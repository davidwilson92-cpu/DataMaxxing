import json
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select
from test_account_integrity import account
from nova import strategy, ai, series
from nova.db import SessionLocal, Strategy, StrategyAction, Draft, Brand, SeriesOccurrence, ContentSeries, ScheduledPost, Publication

PROFILE={'goal':'Increase pottery class enquiries','audience':'Local beginners','themes':'Practical beginner tips','platforms':['instagram'],'voice':'Warm','resources':'One hour a week'}


def setup_strategy(monkeypatch):
    c,uid,*_=account()
    row=c.get('/api/strategy').json()
    assert c.post('/api/strategy/confirm',json={'strategy':PROFILE,'revision':row['revision']}).status_code==200
    def reply(*args,**kwargs):
        return {'actions':[{'title':'Beginner tip '+str(i),'reason':'Build trust before class enquiries','brief':'Explain one useful pottery tip '+str(i),'effort':'5 minutes','needs':'A photo of your tools','platform':'instagram','format':'post'} for i in range(3)]}
    monkeypatch.setattr(strategy,'model_json',reply)
    r=c.post('/api/strategy/recommend',json={});assert r.status_code==200,r.text
    return c,uid,r.json()['items']


def test_strategy_confirm_revision_and_brand_isolation(monkeypatch):
    c,uid,items=setup_strategy(monkeypatch)
    other,*_=account()
    assert other.post(f'/api/strategy/actions/{items[0]["id"]}/draft',json={}).status_code==404
    assert other.get('/api/strategy').json()['confirmed']=={}
    with SessionLocal() as db:
        brand=Brand(user_id=uid,name='Other brand');db.add(brand);db.commit();bid=brand.id
    assert c.get('/api/strategy',headers={'X-Zova-Brand':str(bid)}).json()['confirmed']=={}
    assert c.post(f'/api/strategy/actions/{items[0]["id"]}/draft',json={},headers={'X-Zova-Brand':str(bid)}).status_code==404
    assert c.post('/api/strategy/confirm',json={'strategy':PROFILE,'revision':0}).status_code==409


def test_proposal_is_not_confirmation(monkeypatch):
    c,*_=account();c.get('/api/strategy')
    monkeypatch.setattr(strategy,'model_json',lambda *a,**k:{'strategy':PROFILE,'assumptions':['One hour is enough for one post.']})
    r=c.post('/api/strategy/propose',json={'brief':'Help me plan','revision':0});assert r.status_code==200,r.text
    saved=c.get('/api/strategy').json()
    assert not saved['confirmed'] and saved['proposal']['assumptions']
    assert c.post('/api/strategy/recommend',json={}).status_code==400


def test_next_move_is_idempotent_and_generated(monkeypatch):
    c,uid,items=setup_strategy(monkeypatch)
    monkeypatch.setattr(ai,'generate_variants',lambda **k:{'instagram':{'posts':['Try centring a little clay before building height.']}})
    path=f'/api/strategy/actions/{items[0]["id"]}/draft'
    one=c.post(path,json={});assert one.status_code==200,one.text
    assert c.post(path,json={}).json()==one.json()
    saved=c.get('/api/drafts/'+str(one.json()['draft_id'])).json()
    assert saved['variants']['instagram']['posts'] and saved['status']=='draft'
    assert saved['workspace']['instagram_format']=='post'
    assert saved['workspace']['platform_selection_explicit'] is True
    assert saved['workspace']['active_platform']=='instagram'
    assert saved['title']==items[0]['title']


def test_generation_failure_keeps_recommendation(monkeypatch):
    c,uid,items=setup_strategy(monkeypatch)
    def fail(**kw):raise RuntimeError('synthetic')
    monkeypatch.setattr(ai,'generate_variants',fail)
    assert c.post(f'/api/strategy/actions/{items[0]["id"]}/draft',json={}).status_code==502
    assert c.get('/api/strategy/actions').json()['items'][0]['draft_id'] is None


def test_feedback_and_missing_sources(monkeypatch):
    c,uid,items=setup_strategy(monkeypatch)
    assert 'not connected' in c.get('/api/strategy/actions').json()['source_note']
    assert c.post(f'/api/strategy/actions/{items[0]["id"]}/feedback',json={'status':'snoozed','reason':'Bad timing'}).status_code==200
    assert len(c.get('/api/strategy/actions').json()['items'])==2
    assert c.post(f'/api/strategy/actions/{items[1]["id"]}/feedback',json={'status':'dismissed'}).status_code==200
    assert len(c.get('/api/strategy/actions').json()['items'])==1


def source(c):
    d=c.post('/api/drafts',json={}).json()
    r=c.patch('/api/drafts/'+str(d['id']),json={'brief':'Weekly pottery tip','platforms':['instagram'],'variants':{'instagram':{'posts':['A useful tip']}},'workspace':{'instagram_format':'story','selected_platforms':['instagram']},'revision':d['revision']})
    assert r.status_code==200,r.text
    return d['id']


def spec(d):return {'draft_id':d,'request_key':'test-series-unique','start':'2030-03-24T10:00','timezone':'Europe/London','frequency':'weekly','count':3,'mode':'repeat'}


def test_series_dates_preserve_local_time_across_dst():
    dates=series.times(series.SeriesSpec(**spec(1)))
    assert dates[0]['local'].endswith('+00:00') and dates[1]['local'].endswith('+01:00')
    assert all('T10:00' in x['local'] for x in dates)


@pytest.mark.parametrize('value',['2030-03-31T01:30','2030-10-27T01:30'])
def test_ambiguous_or_missing_local_time_rejected(value):
    from fastapi import HTTPException
    body=spec(1);body.update(start=value,count=1)
    with pytest.raises(HTTPException):series.times(series.SeriesSpec(**body))


def test_series_creation_is_idempotent_and_unapproved():
    c,uid,*_=account();body=spec(source(c))
    r=c.post('/api/series',json=body);assert r.status_code==200,r.text
    assert c.post('/api/series',json=body).json()==r.json()
    rows=c.get('/api/series').json();assert len(rows)==1 and len(rows[0]['occurrences'])==3
    o=rows[0]['occurrences'][0]
    r=c.post(f'/api/series/occurrences/{o["id"]}/draft',json={});assert r.status_code==200,r.text
    d=c.get('/api/drafts/'+str(r.json()['draft_id'])).json()
    assert d['status']=='draft' and d['workspace']['instagram_format']=='story'
    assert c.post(f'/api/series/occurrences/{o["id"]}/draft',json={}).json()==r.json()
    with SessionLocal() as db:assert not db.scalar(select(ScheduledPost).where(ScheduledPost.user_id==uid))


def test_series_owner_and_pause_resume_cancel():
    c,uid,*_=account();other,*_=account()
    sid=c.post('/api/series',json=spec(source(c))).json()['id']
    assert other.post(f'/api/series/{sid}/state',json={'action':'pause','revision':0}).status_code==404
    assert c.post(f'/api/series/{sid}/state',json={'action':'pause','revision':0}).status_code==200
    occurrence=c.get('/api/series').json()[0]['occurrences'][0]['id']
    assert c.post(f'/api/series/occurrences/{occurrence}/draft',json={}).status_code==409
    assert c.post(f'/api/series/{sid}/state',json={'action':'resume','revision':1}).status_code==200
    assert c.post(f'/api/series/{sid}/state',json={'action':'cancel','revision':2}).status_code==200
    assert c.post(f'/api/series/{sid}/state',json={'action':'resume','revision':3}).status_code==409


def test_series_move_one_or_future():
    c,*_=account();c.post('/api/series',json=spec(source(c)))
    rows=c.get('/api/series').json()[0];o=rows['occurrences']
    r=c.post(f'/api/series/occurrences/{o[1]["id"]}/time',json={'local_time':'2030-04-01T11:00','scope':'future','revision':0})
    assert r.status_code==200,r.text
    now=c.get('/api/series').json()[0]['occurrences']
    assert now[0]['due_at']==o[0]['due_at'] and now[1]['due_at']!=o[1]['due_at'] and now[2]['due_at']!=o[2]['due_at']


def test_strategy_is_in_privacy_export(monkeypatch):
    c,uid,_=setup_strategy(monkeypatch)
    from nova.data_lifecycle import export_account
    with SessionLocal() as db:
        data=export_account(db,uid)
        assert data['zova_strategies'] and len(data['zova_strategy_actions'])==3


def repeat_ready():
    from test_reviewed_publication import prepared
    c,uid,token,body=prepared()
    d=c.get('/api/drafts/'+str(body['draft_id'])).json()
    c.patch('/api/drafts/'+str(d['id']),json={'brief':'Weekly update','platforms':['x'],'variants':body['variants'],'revision':d['revision']})
    sid=c.post('/api/series',json=spec(d['id'])).json()['id']
    return c,uid,sid


def test_repeat_approval_is_exact_and_duplicate_safe():
    c,uid,sid=repeat_ready()
    reviewed=c.post(f'/api/series/{sid}/review',json={'revision':0});assert reviewed.status_code==200,reviewed.text
    r=reviewed.json();assert len(r['occurrences'])==3
    assert all(i['snapshot']['targets']['x']['account_id']=='original-x' for i in r['occurrences'])
    confirmed=c.post(f'/api/series/{sid}/confirm',json={'token':r['token']});assert confirmed.status_code==200,confirmed.text
    assert all(i['status']=='scheduled' for i in confirmed.json()['results'])
    assert c.post(f'/api/series/{sid}/confirm',json={'token':r['token']}).status_code==200
    with SessionLocal() as db:assert len(db.scalars(select(ScheduledPost).where(ScheduledPost.user_id==uid)).all())==3


def test_pause_invalidates_repeat_approval_and_cancels_jobs():
    c,uid,sid=repeat_ready()
    reviewed=c.post(f'/api/series/{sid}/review',json={'revision':0}).json()
    assert c.post(f'/api/series/{sid}/confirm',json={'token':reviewed['token']}).status_code==200
    assert c.post(f'/api/series/{sid}/state',json={'action':'pause','revision':0}).status_code==200
    with SessionLocal() as db:
        assert all(r.status=='cancelled' for r in db.scalars(select(ScheduledPost).where(ScheduledPost.user_id==uid)))
    assert c.post(f'/api/series/{sid}/confirm',json={'token':reviewed['token']}).status_code==409
    assert c.post(f'/api/series/{sid}/state',json={'action':'resume','revision':1}).status_code==200
    assert c.post(f'/api/series/{sid}/confirm',json={'token':reviewed['token']}).status_code==409


def test_repeat_changed_content_has_per_occurrence_failure():
    c,uid,sid=repeat_ready()
    r=c.post(f'/api/series/{sid}/review',json={'revision':0}).json()
    did=r['occurrences'][0]['snapshot']['draft_id'];d=c.get('/api/drafts/'+str(did)).json()
    c.patch('/api/drafts/'+str(did),json={'revision':d['revision'],'platforms':['x'],'variants':{'x':{'posts':['Changed after approval']}}})
    out=c.post(f'/api/series/{sid}/confirm',json={'token':r['token']}).json()['results']
    assert out[0]['status']=='not_scheduled' and out[1]['status']=='scheduled'


def test_concurrent_recommendation_clicks_create_one_draft(monkeypatch):
    c,uid,items=setup_strategy(monkeypatch)
    monkeypatch.setattr(ai,'generate_variants',lambda **k:{'instagram':{'posts':['A useful pottery tip.']}})
    path=f'/api/strategy/actions/{items[0]["id"]}/draft'
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(lambda _:c.post(path,json={}),range(2)))
    assert all(r.status_code==200 for r in responses),[r.text for r in responses]
    assert responses[0].json()==responses[1].json()


def test_cancel_one_occurrence_preserves_other_dates():
    c,uid,sid=repeat_ready();before=c.get('/api/series').json()[0]['occurrences']
    assert c.post(f'/api/series/occurrences/{before[0]["id"]}/cancel',json={'revision':0}).status_code==200
    after=c.get('/api/series').json()[0]['occurrences']
    assert after[0]['status']=='cancelled' and after[1]['status']=='planned'


def test_elapsed_snooze_can_be_drafted(monkeypatch):
    from datetime import timedelta
    from nova.db import utcnow
    c,uid,items=setup_strategy(monkeypatch)
    with SessionLocal() as db:
        row=db.get(StrategyAction,items[0]['id']);row.status='snoozed';row.snoozed_until=utcnow()-timedelta(seconds=1);db.commit()
    monkeypatch.setattr(ai,'generate_variants',lambda **kw:{'instagram':{'posts':['Useful proposal']}})
    assert c.post(f'/api/strategy/actions/{items[0]["id"]}/draft',json={}).status_code==200


def test_fresh_occurrence_failure_and_generation_remain_unapproved(monkeypatch):
    c,uid,*_=account();body=spec(source(c));body['mode']='fresh'
    c.post('/api/series',json=body)
    occurrence=c.get('/api/series').json()[0]['occurrences'][0]['id']
    def fail(**kw):raise RuntimeError('synthetic outage')
    monkeypatch.setattr(ai,'generate_variants',fail)
    assert c.post(f'/api/series/occurrences/{occurrence}/draft',json={}).status_code==502
    assert c.get('/api/series').json()[0]['occurrences'][0]['draft_id'] is None
    monkeypatch.setattr(ai,'generate_variants',lambda **kw:{'instagram':{'posts':['Fresh proposed text']}})
    result=c.post(f'/api/series/occurrences/{occurrence}/draft',json={});assert result.status_code==200,result.text
    draft=c.get('/api/drafts/'+str(result.json()['draft_id'])).json()
    assert draft['variants']['instagram']['posts']==['Fresh proposed text'] and draft['status']=='draft'
    with SessionLocal() as db:assert not db.scalar(select(ScheduledPost).where(ScheduledPost.user_id==uid))


def test_unconfirmed_sending_blocks_series_cancellation():
    c,uid,sid=repeat_ready();review=c.post(f'/api/series/{sid}/review',json={'revision':0}).json()
    c.post(f'/api/series/{sid}/confirm',json={'token':review['token']})
    with SessionLocal() as db:
        row=db.scalar(select(ScheduledPost).where(ScheduledPost.user_id==uid));row.status='unknown';db.commit()
    assert c.post(f'/api/series/{sid}/state',json={'action':'cancel','revision':0}).status_code==409
    assert c.get('/api/series').json()[0]['status']=='active'


def test_series_cancel_preserves_published_history():
    c,uid,sid=repeat_ready();review=c.post(f'/api/series/{sid}/review',json={'revision':0}).json()
    did=review['occurrences'][0]['snapshot']['draft_id']
    with SessionLocal() as db:db.get(Draft,did).status='published';db.commit()
    assert c.post(f'/api/series/{sid}/state',json={'action':'cancel','revision':0}).status_code==200
    assert c.get('/api/series').json()[0]['occurrences'][0]['status']=='published'
