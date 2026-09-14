import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from fastapi.testclient import TestClient
from nova.db import SessionLocal,SocialConnection,Publication,ScheduledPost,utcnow
from nova.security import encrypt
from test_account_integrity import account


def prepared(platforms=('x',)):
    client,uid,token,_=account()
    with SessionLocal() as db:
        for p in platforms:
            db.add(SocialConnection(user_id=uid,platform=p,account_id='original-'+p,username='demo',display_name='Demo',scope='tweet.write,pages_manage_posts',encrypted_access_token=encrypt('synthetic')))
        db.commit()
    row=client.post('/api/drafts',json={}).json()
    variants={p:{'posts':['Approved text '+p]} for p in platforms}
    client.patch(f"/api/drafts/{row['id']}",json={'platforms':list(platforms),'variants':variants})
    body={'draft_id':row['id'],'platforms':list(platforms),'variants':variants,'media_asset_ids':[],'link_url':'','publish_options':{}}
    return client,uid,token,body


def review(client,body):
    response=client.post('/api/publish-review',json=body)
    assert response.status_code==200,response.text
    return {**body,'review_token':response.json()['review_token']}


def test_link_is_finalised_before_review_and_sent_without_mutation(monkeypatch):
    import nova.app as module
    client,_,_,body=prepared();calls=[]
    body['link_url']='https://example.test/source'
    saved=client.get(f"/api/drafts/{body['draft_id']}").json()
    client.patch(f"/api/drafts/{body['draft_id']}",json={'revision':saved['revision'],'platforms':body['platforms'],'variants':body['variants'],'workspace':{'link_url':body['link_url']}})
    response=client.post('/api/publish-review',json=body)
    assert response.status_code==200
    snapshot=response.json()['snapshot']
    assert snapshot['targets']['x']['posts'][0].endswith(body['link_url'])
    monkeypatch.setattr(module,'publish_platform',lambda *a,**k:calls.append(k) or {'post_id':'mock'})
    assert client.post('/api/publish',json={**body,'review_token':response.json()['review_token']}).status_code==200
    assert calls[0]['posts']==snapshot['targets']['x']['posts'] and calls[0]['link_url']==''


def test_deleting_unsubmitted_review_does_not_leave_foreign_keys():
    client,_,_,body=prepared()
    review(client,body)
    assert client.delete('/api/drafts/'+str(body['draft_id'])).status_code==204
    assert client.get('/api/drafts/'+str(body['draft_id'])).status_code==404


def test_two_workers_claim_one_due_job(monkeypatch):
    import nova.scheduler as worker
    client,_,_,body=prepared();calls=[]
    body['scheduled_local']=(utcnow()+timedelta(days=1)).isoformat()
    approved=review(client,body)
    assert client.post('/api/schedule',json=approved).status_code==200
    with SessionLocal() as db:
        from sqlalchemy import select
        row=db.scalar(select(ScheduledPost).where(ScheduledPost.draft_id==body['draft_id']))
        row.scheduled_at=utcnow()-timedelta(seconds=1);db.commit()
    monkeypatch.setattr(worker,'publish_platform',lambda *a,**k:calls.append(k) or {'post_id':'mock'})
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _:worker.process_due(),range(2)))
    assert len(calls)==1


def test_interrupted_worker_becomes_unknown_without_resend(monkeypatch):
    import nova.scheduler as worker
    client,_,_,body=prepared()
    approved=review(client,body)
    monkeypatch.setattr(worker,'publish_platform',lambda *a,**k: (_ for _ in ()).throw(AssertionError('Must not resend')))
    with SessionLocal() as db:
        from sqlalchemy import select
        conn=db.scalar(select(SocialConnection).where(SocialConnection.account_id=='original-x').order_by(SocialConnection.id.desc()))
        row=Publication(user_id=conn.user_id,draft_id=body['draft_id'],platform='x',connection_id=conn.id,review_code=approved['review_token'],status='publishing',updated_at=utcnow()-timedelta(minutes=20))
        db.add(row);db.commit()
    worker.process_due()
    assert client.get('/api/publications/'+str(body['draft_id'])).json()['results']['x']['status']=='unknown'


def test_confirmation_is_immutable_and_retry_is_idempotent(monkeypatch):
    import nova.app as module
    client,uid,_,body=prepared();calls=[]
    monkeypatch.setattr(module,'publish_platform',lambda *a,**k:calls.append(k) or {'post_id':'synthetic','url':'https://example.test/post'})
    approved=review(client,body)
    changed={**approved,'variants':{'x':{'posts':['Different text']}}}
    assert client.post('/api/publish',json=changed).status_code==409
    assert not calls
    assert client.post('/api/publish',json=approved).json()['results']['x']['status']=='published'
    assert client.post('/api/publish',json=approved).status_code==200
    assert len(calls)==1 and calls[0]['posts']==body['variants']['x']['posts']


def test_partial_unknown_never_resends_successful_targets(monkeypatch):
    import nova.app as module
    client,_,_,body=prepared(('x','facebook'));calls=[]
    def publish(*a,**k):
        calls.append(k['platform'])
        if k['platform']=='facebook':raise TimeoutError('synthetic')
        return {'post_id':'synthetic'}
    monkeypatch.setattr(module,'publish_platform',publish)
    result=client.post('/api/publish',json=review(client,body)).json()
    assert result['results']['facebook']['status']=='unknown'
    assert result['draft_status']=='needs_review'
    assert client.post('/api/publish-review',json=body).status_code==409
    assert calls==['x','facebook']


def test_review_binds_original_account_and_rejects_other_owner(monkeypatch):
    import nova.app as module
    client,uid,_,body=prepared();approved=review(client,body);other,_,_,_=account();calls=[]
    with SessionLocal() as db:
        original=db.query(SocialConnection).filter_by(user_id=uid).first().id
        db.add(SocialConnection(user_id=uid,platform='x',account_id='newer',scope='tweet.write',encrypted_access_token=encrypt('synthetic')));db.commit()
    monkeypatch.setattr(module,'publish_platform',lambda *a,**k:calls.append(k['connection_id']) or {'post_id':'synthetic'})
    assert other.post('/api/publish',json=approved).status_code==400
    assert client.post('/api/publish',json=approved).status_code==200
    assert calls==[original]


def test_concurrent_confirmation_calls_provider_once(monkeypatch):
    import nova.app as module
    client,_,token,body=prepared();approved=review(client,body);calls=[];barrier=threading.Barrier(2)
    monkeypatch.setattr(module,'publish_platform',lambda *a,**k:calls.append(True) or {'post_id':'synthetic'})
    def submit():
        concurrent=TestClient(module.app);concurrent.cookies.set('nova_session',token);barrier.wait()
        return concurrent.post('/api/publish',json=approved).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:submit(),range(2)))
    assert all(r in {200,409} for r in results)
    assert len(calls)==1


def test_schedules_cancel_reschedule_and_only_worker_claims_once(monkeypatch):
    import nova.scheduler as scheduler
    client,_,_,body=prepared()
    scheduled=(utcnow()+timedelta(days=1)).isoformat()
    approved=review(client,{**body,'scheduled_local':scheduled})
    assert client.post('/api/schedule',json=approved).status_code==200
    job=client.get('/api/schedules').json()[0]
    assert client.post(f"/api/schedules/{job['id']}/reschedule",json={'scheduled_local':(utcnow()+timedelta(days=2)).isoformat()}).status_code==200
    assert client.post(f"/api/schedules/{job['id']}/cancel").status_code==200
    with SessionLocal() as db:
        row=db.get(ScheduledPost,job['id']);row.scheduled_at=utcnow()-timedelta(minutes=1);db.commit()
    monkeypatch.setattr(scheduler,'publish_platform',lambda *a,**k:(_ for _ in ()).throw(AssertionError('Cancelled schedule must not publish')))
    scheduler.process_due()
    assert client.get('/api/schedules').json()[0]['status']=='cancelled'


def test_definite_preflight_failure_can_retry_failed_destination_only(monkeypatch):
    import nova.app as module
    client,uid,_,body=prepared(('x','facebook'));approved=review(client,body);calls=[]
    with SessionLocal() as db:
        conn=db.query(SocialConnection).filter_by(user_id=uid,platform='facebook').one();conn.active=False;db.commit()
    monkeypatch.setattr(module,'publish_platform',lambda *a,**k:calls.append(k['platform']) or {'post_id':'synthetic'})
    result=client.post('/api/publish',json=approved).json()
    assert result['results']['facebook']['status']=='failed'
    assert result['draft_status']=='partial'
    assert client.post('/api/publish-review',json=body).status_code==409
    with SessionLocal() as db:
        conn=db.query(SocialConnection).filter_by(user_id=uid,platform='facebook').one();conn.active=True;db.commit()
    retry={**body,'platforms':['facebook'],'variants':{'facebook':body['variants']['facebook']}}
    assert client.post('/api/publish',json=review(client,retry)).status_code==200
    assert calls==['x','facebook']
