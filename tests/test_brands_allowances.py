from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from test_account_integrity import account
from nova import allowances
from nova.db import SessionLocal, Brand, BillingAccount, Draft, SocialConnection, UsageEntry, CreatorPreferences, BrandVoice


def test_brands_keep_legacy_drafts_and_voice_separate():
    client,uid,*_=account()
    original=client.post('/api/drafts',json={}).json()['id']
    assert client.post('/account/preferences',data={'writing_tone':'Original voice'}).status_code==200
    assert client.post('/brands',data={'name':'Second brand'},follow_redirects=False).status_code==303
    bid=int(client.cookies.get('zova_brand'))
    second=client.post('/api/drafts',json={}).json()['id']
    assert client.get(f'/api/drafts/{original}').status_code==404
    assert client.get(f'/api/drafts/{second}',headers={'X-Zova-Brand':'0'}).status_code==404
    assert client.get(f'/api/drafts/{original}',headers={'X-Zova-Brand':'0'}).status_code==200
    assert client.post('/account/preferences',data={'writing_tone':'Second voice'}).status_code==200
    with SessionLocal() as db:
        assert db.get(Draft,original).brand_id==0
        assert db.get(Draft,second).brand_id==bid
        assert db.scalar(select(CreatorPreferences).where(CreatorPreferences.user_id==uid)).writing_tone=='Original voice'
        assert db.scalar(select(BrandVoice).where(BrandVoice.user_id==uid)).writing_tone=='Second voice'
    stranger,*_=account()
    assert stranger.get('/api/drafts',headers={'X-Zova-Brand':str(bid)}).status_code==404
    assert stranger.post('/brands/switch',data={'brand_id':bid}).status_code==404


def configure(monkeypatch,uid,tier='basic'):
    monkeypatch.setenv('PLAN_LIMITS_ENABLED','true')
    monkeypatch.setenv('PLAN_LIMITS_MODE','test')
    monkeypatch.setenv('STRIPE_MODE','test')
    monkeypatch.setenv('STRIPE_'+tier.upper()+'_MONTHLY_PRICE_ID','price_'+tier)
    with SessionLocal() as db:
        db.add(BillingAccount(key=f'{uid}:test',user_id=uid,mode='test',status='trialing',price_id='price_'+tier));db.commit()


def test_brand_cap_and_test_live_separation(monkeypatch):
    client,uid,*_=account();configure(monkeypatch,uid)
    assert client.post('/brands',data={'name':'Blocked'}).status_code==402
    monkeypatch.setenv('PLAN_LIMITS_MODE','live')
    with SessionLocal() as db:assert allowances.tier(db,uid) is None
    monkeypatch.setenv('PLAN_LIMITS_ENABLED','false')
    assert client.post('/brands',data={'name':'Testing'}).status_code==200
    assert client.post('/brands',data={'name':'Third'}).status_code==409


def test_concurrent_allowance_reservation_is_atomic(monkeypatch):
    _,uid,*_=account();configure(monkeypatch,uid)
    with SessionLocal() as db:
        allowances.reserve(db,uid,'ai',f'seed:{uid}',149);db.commit()
    def reserve(i):
        with SessionLocal() as db:
            try:allowances.reserve(db,uid,'ai',f'concurrent:{uid}:{i}');db.commit();return True
            except HTTPException:db.rollback();return False
    with ThreadPoolExecutor(max_workers=2) as pool:assert sum(pool.map(reserve,range(2)))==1
    with SessionLocal() as db:assert allowances.count(db,uid,'ai')==150


def test_failed_ai_does_not_consume_and_success_does(monkeypatch):
    client,uid,*_=account()
    from nova import ai
    def fail(**kwargs):raise RuntimeError('Synthetic failure')
    monkeypatch.setattr(ai,'generate_variants',fail)
    assert client.post('/api/ai/generate',json={'brief':'An idea','platforms':['x']}).status_code==502
    with SessionLocal() as db:assert allowances.count(db,uid,'ai')==0
    monkeypatch.setattr(ai,'generate_variants',lambda **kwargs:{'x':{'posts':['Saved result']}})
    assert client.post('/api/ai/generate',json={'brief':'An idea','platforms':['x']}).status_code==200
    with SessionLocal() as db:assert allowances.count(db,uid,'ai')==1


def test_publication_retry_and_release_are_idempotent():
    _,uid,*_=account()
    with SessionLocal() as db:
        allowances.reserve(db,uid,'publications',f'thread:{uid}',3);db.commit()
        allowances.reserve(db,uid,'publications',f'thread:{uid}',3);db.commit()
        assert allowances.count(db,uid,'publications')==3
        allowances.finish(db,f'thread:{uid}',False);db.commit()
        assert allowances.count(db,uid,'publications')==0


def test_connection_limit_counts_all_brands(monkeypatch):
    _,uid,*_=account();configure(monkeypatch,uid)
    with SessionLocal() as db:
        for i in range(4):db.add(SocialConnection(user_id=uid,brand_id=i%2,platform='x',account_id=str(i),encrypted_access_token='synthetic'))
        db.commit();db.info.update(brand_id=0,brand_user_id=uid)
        with pytest.raises(HTTPException):allowances.connection_slot(db,uid)


def test_cross_brand_review_media_schedule_and_connections_are_rejected(monkeypatch):
    from test_reviewed_publication import prepared, review
    from nova.db import MediaAsset, ScheduledPost, utcnow
    from datetime import timedelta
    client,uid,_,body=prepared()
    body['scheduled_local']=(utcnow()+timedelta(days=1)).isoformat()
    approved=review(client,body)
    assert client.post('/api/schedule',json=approved).status_code==200
    with SessionLocal() as db:
        job=db.scalar(select(ScheduledPost).where(ScheduledPost.user_id==uid)).id
        conn=db.scalar(select(SocialConnection).where(SocialConnection.user_id==uid)).id
        asset=MediaAsset(user_id=uid,filename='private.png',mime_type='image/png',storage_key='synthetic');db.add(asset);db.commit();mid=asset.id
    client.post('/brands',data={'name':'Separate'})
    assert client.get('/api/schedules').json()==[]
    assert client.post(f'/api/schedules/{job}/cancel').status_code==404
    assert client.post(f'/api/schedules/{job}/reschedule',json={'scheduled_local':body['scheduled_local']}).status_code==404
    assert client.post('/api/schedule',json=approved).status_code==400
    assert client.get(f'/api/publications/{body["draft_id"]}').status_code==404
    assert client.post(f'/account/connections/{conn}/unlink').status_code==404
    new=client.post('/api/drafts',json={}).json()['id']
    assert client.patch(f'/api/drafts/{new}',json={'workspace':{'media_asset_ids':[mid]}}).status_code==404
    with SessionLocal() as db:assert db.get(SocialConnection,conn).active


def test_publication_quota_rolls_back_review_and_cancel_releases(monkeypatch):
    from test_reviewed_publication import prepared, review
    from nova.db import ScheduledPost, PublishReview, utcnow
    from datetime import timedelta
    client,uid,_,body=prepared();configure(monkeypatch,uid)
    with SessionLocal() as db:allowances.reserve(db,uid,'publications',f'prior:{uid}',100);db.commit()
    body['scheduled_local']=(utcnow()+timedelta(days=1)).isoformat();approved=review(client,body)
    assert client.post('/api/schedule',json=approved).status_code==402
    with SessionLocal() as db:
        assert db.get(PublishReview,approved['review_token']).status=='review'
        assert db.get(Draft,body['draft_id']).status=='draft'
        allowances.finish(db,f'prior:{uid}',False);db.commit()
    assert client.post('/api/schedule',json=approved).status_code==200
    with SessionLocal() as db:
        assert allowances.count(db,uid,'publications')==1
        job=db.scalar(select(ScheduledPost).where(ScheduledPost.user_id==uid)).id
    assert client.post(f'/api/schedules/{job}/cancel').status_code==200
    with SessionLocal() as db:assert allowances.count(db,uid,'publications')==0


def test_second_brand_oauth_state_survives_workspace_switch(monkeypatch):
    from nova import app as module
    from nova.db import OAuthState
    from nova.security import hash_api_key
    client,uid,*_=account();client.post('/brands',data={'name':'Second'})
    bid=int(client.cookies.get('zova_brand'))
    with SessionLocal() as db:
        db.add(OAuthState(user_id=uid,brand_id=bid,platform='instagram',state_hash=hash_api_key('brand-state')));db.commit()
    client.post('/brands/switch',data={'brand_id':0})
    monkeypatch.setattr(module,'instagram_exchange',lambda code:{'access_token':'synthetic','profile':{'id':'ig-second','username':'second'}})
    monkeypatch.setattr(module,'learn_voice_from_socials',lambda *a:None)
    result=client.get('/oauth/instagram/callback?code=synthetic&state=brand-state',follow_redirects=False)
    assert result.status_code==303,result.text
    assert f'workspace={bid}' in result.headers['location']
    with SessionLocal() as db:
        row=db.scalar(select(SocialConnection).where(SocialConnection.user_id==uid));assert row.brand_id==bid


def test_monthly_counter_resets_without_erasing_history(monkeypatch):
    from datetime import datetime,timezone
    _,uid,*_=account()
    with SessionLocal() as db:
        allowances.reserve(db,uid,'ai',f'old-month:{uid}');db.commit()
        monkeypatch.setattr(allowances,'utcnow',lambda:datetime(2031,2,1,tzinfo=timezone.utc))
        assert allowances.count(db,uid,'ai')==0
        assert db.get(UsageEntry,f'old-month:{uid}') is not None


def test_renaming_brand_preserves_data_and_profile():
    from nova.db import User
    client,uid,*_=account()
    did=client.post('/api/drafts',json={}).json()['id']
    assert client.post('/brands/0/name',data={'name':'Acme'}).status_code==200
    with SessionLocal() as db:
        assert db.get(User,uid).display_name=='Original'
        assert db.get(User,uid).default_brand_name=='Acme'
        assert db.get(Draft,did).brand_id==0
    assert 'Acme' in client.get('/studio').text


def test_retired_price_keeps_existing_tier(monkeypatch):
    from nova import billing
    _,uid,*_=account();configure(monkeypatch,uid)
    monkeypatch.setenv('STRIPE_BASIC_MONTHLY_PRICE_ID','price_new_basic')
    monkeypatch.setenv('STRIPE_BASIC_MONTHLY_LEGACY_PRICE_IDS','price_basic')
    with SessionLocal() as db:assert allowances.tier(db,uid)=='basic'
    assert billing.plan_for_price('price_basic')=='basic_monthly'
