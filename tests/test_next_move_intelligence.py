"""Evidence, isolation and failure tests for the Next Move recommendation loop."""
import json
from datetime import timedelta
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from nova import strategy, performance, social
from nova.db import (SessionLocal, StrategyAction, PerformanceSnapshot, SocialConnection,
                     ScheduledPost, Brand, get_preferences, utcnow)
from nova.security import encrypt
from test_strategy_series import setup_strategy, PROFILE
from test_strategy_revision import ideas
from test_account_integrity import account


def connect(uid, platform='instagram', brand_id=0):
    with SessionLocal() as db:
        db.info.update(brand_user_id=uid,brand_id=brand_id)
        conn=SocialConnection(user_id=uid,brand_id=brand_id,platform=platform,
            account_id='synthetic',username='synthetic',encrypted_access_token=encrypt('synthetic'),active=True)
        db.add(conn);db.commit();return conn.id


def feed():
    return {'posts':[{'platform':'instagram','text':f'Pottery example {i}',
        'created_at':(utcnow()-timedelta(days=i+1)).isoformat(),'format':'IMAGE',
        'likes':i,'comments':1,'shares':None,'views':None} for i in range(8)],'unavailable':[]}


def test_every_path_receives_strategy_voice_performance_and_schedule(monkeypatch):
    c,uid,old=setup_strategy(monkeypatch);connect(uid)
    calls=[]
    monkeypatch.setattr(social,'recent_posts_for_user',lambda *a,**kw:(calls.append(kw) or feed()))
    with SessionLocal() as db:
        prefs=get_preferences(db,uid);prefs.writing_tone='Dry humour';prefs.things_to_avoid='No hype'
        prefs.example_posts='An explicit writing example.'
        prefs.learned_json=json.dumps({'approved_examples':['An approved caption.']})
        db.add(ScheduledPost(user_id=uid,platform='instagram',content_json=json.dumps({'posts':['Already planned class announcement']}),scheduled_at=utcnow()+timedelta(days=1)))
        db.commit()
    captured=[]
    monkeypatch.setattr(strategy,'model_json',lambda u,i,d:(captured.append(d) or ideas('Fresh')))
    result=c.post('/api/strategy/recommend',json={'brief':'A playful new angle','platforms':['instagram'],'post_only':True})
    assert result.status_code==200,result.text
    data=captured[0]
    assert data['strategy']['goal']==PROFILE['goal'] and data['strategy']['topic']=='A playful new angle'
    assert data['strategy']['audience']==PROFILE['audience']
    assert data['voice']['writing_tone']=='Dry humour' and data['voice']['things_to_avoid']=='No hype'
    assert 'An approved caption.' in data['voice']['example_posts']
    assert len(data['performance']['evidence']['posts'])==8, 'Use the cohort, not only winning posts'
    assert data['performance']['evidence']['posts'][0]['shares'] is None
    assert data['upcoming_posts'][0]['content']==['Already planned class announcement']
    assert result.json()['items'][0]['basis']=='Performance · Strategy · Voice'
    assert c.get('/api/strategy').json()['confirmed']['goal']==PROFILE['goal']
    assert calls==[{'limit':30,'quick':True}]


def test_performance_refresh_cache_failure_and_expiry(monkeypatch):
    c,uid,*_=account();connect(uid);calls=[]
    monkeypatch.setattr(social,'recent_posts_for_user',lambda *a,**kw:(calls.append(1) or feed()))
    with SessionLocal() as db:
        db.info.update(brand_user_id=uid,brand_id=0)
        assert performance.recommendation_context(db,uid)['available']
        assert performance.recommendation_context(db,uid)['available'];assert len(calls)==1
        row=db.scalar(select(PerformanceSnapshot).where(PerformanceSnapshot.user_id==uid))
        payload=json.loads(row.payload_json);payload['last_attempt_at']=(utcnow()-timedelta(minutes=16)).isoformat()
        row.payload_json=json.dumps(payload);db.commit()
        monkeypatch.setattr(social,'recent_posts_for_user',lambda *a,**kw:(_ for _ in ()).throw(RuntimeError('SECRET_PROVIDER_DETAIL')))
        result=performance.recommendation_context(db,uid)
        assert result['available'] and 'SECRET' not in json.dumps(result)
        row.fetched_at=utcnow()-timedelta(hours=25);payload=json.loads(row.payload_json)
        payload['last_attempt_at']=(utcnow()-timedelta(minutes=16)).isoformat();row.payload_json=json.dumps(payload);db.commit()
        result=performance.recommendation_context(db,uid)
        assert not result['available'] and 'evidence' not in result
        db.info['brand_id']=999
        assert not performance.recommendation_context(db,uid)['available']


def test_disconnected_performance_is_not_reused(monkeypatch):
    c,uid,*_=account();cid=connect(uid)
    monkeypatch.setattr(social,'recent_posts_for_user',lambda *a,**kw:feed())
    with SessionLocal() as db:
        assert performance.recommendation_context(db,uid)['available']
        db.get(SocialConnection,cid).active=False;db.commit()
        assert not performance.recommendation_context(db,uid)['available']


def test_refinement_is_atomic_owned_and_preserves_history(monkeypatch):
    c,uid,old=setup_strategy(monkeypatch);aid=old[0]['id']
    before=c.get('/api/strategy/actions').json()['items']
    monkeypatch.setattr(strategy,'model_json',lambda *a:(_ for _ in ()).throw(HTTPException(502,'Retry later')))
    result=c.post('/api/strategy/recommend',json={'refine_action_id':aid,'refinement':'Less filming'})
    assert result.status_code==502
    assert c.get('/api/strategy/actions').json()['items']==before
    with SessionLocal() as db: assert db.get(StrategyAction,aid).feedback==''
    seen=[]
    monkeypatch.setattr(strategy,'model_json',lambda u,i,d:(seen.append(d) or ideas('Simpler')))
    direction=('Less filming. '+('Use my own words. '*12)).strip()
    result=c.post('/api/strategy/recommend',json={'refine_action_id':aid,'refinement':direction,'post_only':True,'fresh':True})
    assert result.status_code==200,result.text
    assert seen[0]['refinement']['direction']==direction
    assert seen[0]['strategy']['goal']==PROFILE['goal']
    assert aid in [a['id'] for a in result.json()['history']]
    with SessionLocal() as db:
        row=db.get(StrategyAction,aid)
        assert row.status=='open' and len(row.feedback)<=80
        assert json.loads(row.payload_json)['creative_feedback']==direction
    other,*_=account()
    assert other.post('/api/strategy/recommend',json={'refine_action_id':aid,'refinement':'Another angle'}).status_code==404
    assert c.post('/api/strategy/recommend',json={'refine_action_id':aid}).status_code==400
    assert c.post('/api/strategy/recommend',json={'refine_action_id':aid,'refinement':'x'*501}).status_code==422


def test_source_failure_still_uses_all_three_foundations(monkeypatch):
    c,uid,*_=setup_strategy(monkeypatch);captured=[]
    monkeypatch.setattr(strategy.trends,'discover',lambda *a:(_ for _ in ()).throw(RuntimeError('Search unavailable')))
    monkeypatch.setattr(strategy,'model_json',lambda u,i,d:(captured.append(d) or ideas('Evergreen')))
    result=c.post('/api/strategy/recommend',json={'post_only':True})
    assert result.status_code==200
    assert all(key in captured[0] for key in ('strategy','voice','performance'))
    assert not captured[0]['performance']['available']
    assert captured[0]['recent_topics']==[]
    assert all(a['source'] is None for a in result.json()['items'])


def test_quick_feed_read_does_not_renew_tokens_and_uses_short_timeout(monkeypatch):
    c,uid,*_=account();connect(uid)
    class Response:
        status_code=200
        def json(self):return {'data':[]}
    seen=[]
    monkeypatch.setattr(social,'access_token',lambda *a:pytest.fail('Quick read must not refresh a token'))
    monkeypatch.setattr(social.httpx,'get',lambda *a,**kw:(seen.append(kw['timeout']) or Response()))
    with SessionLocal() as db:
        result=social.recent_posts_for_user(db,uid,quick=True)
    assert result['unavailable']==[] and len(seen)==1 and 0<seen[0]<=2


def test_refining_can_keep_the_original_concept(monkeypatch):
    c,uid,old=setup_strategy(monkeypatch)
    output=ideas('Alternative')
    output['actions'][0]['title']=old[0]['title']
    output['actions'][0]['brief']='Keep the clay tip, with a playful hook and only one photo.'
    monkeypatch.setattr(strategy,'model_json',lambda *a:output)
    result=c.post('/api/strategy/recommend',json={'refine_action_id':old[0]['id'],
        'refinement':'Keep this idea, make it playful.','fresh':True,'post_only':True})
    assert result.status_code==200,result.text
    assert result.json()['items'][0]['title']==old[0]['title']
    assert result.json()['items'][0]['id']!=old[0]['id']


def test_changed_social_identity_invalidates_cached_performance(monkeypatch):
    c,uid,*_=account();cid=connect(uid)
    monkeypatch.setattr(social,'recent_posts_for_user',lambda *a,**kw:feed())
    with SessionLocal() as db:
        assert performance.recommendation_context(db,uid)['available']
        db.get(SocialConnection,cid).account_id='replacement-account';db.commit()
        monkeypatch.setattr(social,'recent_posts_for_user',lambda *a,**kw:(_ for _ in ()).throw(RuntimeError('unavailable')))
        result=performance.recommendation_context(db,uid)
        assert not result['available'] and 'evidence' not in result


def test_missing_counters_are_not_performance_evidence(monkeypatch):
    c,uid,*_=account();connect(uid)
    empty=feed()
    for post in empty['posts']:
        for key in ('likes','comments','shares','views'):post[key]=None
    monkeypatch.setattr(social,'recent_posts_for_user',lambda *a,**kw:empty)
    with SessionLocal() as db:
        result=performance.recommendation_context(db,uid)
        assert not result['available'] and result['evidence']['posts']==[]


def test_connection_changed_during_refresh_discards_the_sample(monkeypatch):
    c,uid,*_=account();cid=connect(uid)
    def changing(*args,**kwargs):
        with SessionLocal() as other:
            other.get(SocialConnection,cid).active=False;other.commit()
        return feed()
    monkeypatch.setattr(social,'recent_posts_for_user',changing)
    with SessionLocal() as db:
        assert not performance.recommendation_context(db,uid)['available']
        assert db.scalar(select(PerformanceSnapshot).where(PerformanceSnapshot.user_id==uid)) is None
