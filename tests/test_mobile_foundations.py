import re
import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from nova.app import app
from nova.db import SessionLocal, MobileSession, MobileRefresh, User, Draft, Brand, utcnow
from nova.mobile_auth import challenge_for
from test_account_integrity import account

CALLBACK='https://app.example.test/mobile/callback'


@pytest.fixture(autouse=True)
def mobile_config(monkeypatch):
    monkeypatch.setenv('ZOVA_MOBILE_ENABLED','true')
    monkeypatch.setenv('ZOVA_IOS_REDIRECT_URI',CALLBACK)
    monkeypatch.setenv('RATE_LIMIT_SCALE','100')
    monkeypatch.setenv('ZOVA_SCHEDULER_MODE','disabled')


def code_for(client):
    verifier=secrets.token_urlsafe(48)
    state=secrets.token_urlsafe(32)
    start=client.get('/mobile/authorize',params={'client_id':'zova-ios','redirect_uri':CALLBACK,'code_challenge':challenge_for(verifier),'state':state},follow_redirects=False)
    assert start.status_code==303,start.text
    path=start.headers['location']
    page=client.get(path)
    proof=re.search(r'name="proof" value="([a-f0-9]+)"',page.text)[1]
    approved=client.post(path,data={'proof':proof},follow_redirects=False)
    assert approved.status_code==303,approved.text
    params=parse_qs(urlsplit(approved.headers['location']).query)
    assert params['state']==[state]
    return {'code':params['code'][0],'code_verifier':verifier,'client_id':'zova-ios','redirect_uri':CALLBACK}


def native_account():
    web,uid,token,email=account()
    native=TestClient(app)
    response=native.post('/api/v1/auth/token',json=code_for(web))
    assert response.status_code==200,response.text
    pair=response.json()
    native.headers['Authorization']='Bearer '+pair['access_token']
    return native,web,uid,pair


def test_mobile_disabled_does_not_change_existing_web(monkeypatch):
    web,*_=account()
    monkeypatch.setenv('ZOVA_MOBILE_ENABLED','false')
    assert web.get('/api/v1/me').status_code==404
    assert web.get('/api/drafts').status_code==200
    assert web.get('/api/v1/config').json()['mobile_enabled'] is False


def test_pkce_code_is_bound_single_use_and_tokens_are_hashed():
    web,uid,*_=account();body=code_for(web);native=TestClient(app)
    assert native.post('/api/v1/auth/token',json={**body,'code_verifier':'x'*43}).status_code==401
    assert native.post('/api/v1/auth/token',json={**body,'redirect_uri':'https://evil.example/callback'}).status_code==400
    result=native.post('/api/v1/auth/token',json=body)
    assert result.status_code==200,result.text
    pair=result.json()
    assert result.headers['cache-control']=='no-store'
    assert native.post('/api/v1/auth/token',json=body).status_code==401
    with SessionLocal() as db:
        session=db.get(MobileSession,pair['session_id'])
        assert session.user_id==uid and session.access_hash!=pair['access_token']
        assert db.get(MobileRefresh,pair['refresh_token']) is None


def test_consent_requires_same_browser_and_explicit_approval():
    web,*_=account();other,*_=account()
    response=web.get('/mobile/authorize',params={'client_id':'zova-ios','redirect_uri':CALLBACK,'code_challenge':challenge_for('v'*43),'state':'s'*43},follow_redirects=False)
    path=response.headers['location'];page=web.get(path)
    proof=re.search(r'name="proof" value="([a-f0-9]+)"',page.text)[1]
    assert other.post(path,data={'proof':proof}).status_code==403
    assert web.post(path,data={'proof':proof},headers={'origin':'https://evil.example'}).status_code==403
    assert web.post(path,data={'proof':proof},follow_redirects=False).status_code==303
    assert web.post(path,data={'proof':proof},follow_redirects=False).status_code==409


def test_refresh_replay_revokes_family_and_password_revokes_native():
    native,web,uid,pair=native_account()
    fresh=native.post('/api/v1/auth/refresh',json={'refresh_token':pair['refresh_token']})
    assert fresh.status_code==200,fresh.text
    assert native.get('/api/v1/me').status_code==401 # superseded access token
    native.headers['Authorization']='Bearer '+fresh.json()['access_token']
    assert native.get('/api/v1/me').json()['id']==uid
    assert native.post('/api/v1/auth/refresh',json={'refresh_token':pair['refresh_token']}).status_code==401
    assert native.get('/api/v1/me').status_code==401
    native,web,uid,pair=native_account()
    with SessionLocal() as db:
        user=db.get(User,uid);user.auth_version+=1;db.commit()
    assert native.get('/api/v1/me').status_code==401
    assert native.post('/api/v1/auth/refresh',json={'refresh_token':pair['refresh_token']}).status_code==401


def test_cookie_does_not_authorise_native_or_bearer_authorise_browser():
    native,web,uid,pair=native_account()
    assert web.get('/api/v1/me').status_code==401
    assert native.get('/api/drafts').status_code==401
    assert native.get('/api/v1/me').status_code==200
    with SessionLocal() as db:
        row=db.get(MobileSession,pair['session_id']);row.access_expires_at=utcnow()-timedelta(seconds=1);db.commit()
    assert native.get('/api/v1/me').status_code==401


def test_idempotent_creation_and_revision_protect_shared_drafts():
    native,web,uid,pair=native_account();key=secrets.token_urlsafe(20)
    result=native.post('/api/v1/drafts',headers={'Idempotency-Key':key})
    assert result.status_code==200,result.text
    draft=result.json()
    assert native.post('/api/v1/drafts',headers={'Idempotency-Key':key}).json()==draft
    assert web.get('/api/drafts/'+str(draft['id'])).status_code==200
    assert native.patch('/api/v1/drafts/'+str(draft['id']),json={'brief':'missing revision'}).status_code==428
    saved=native.patch('/api/v1/drafts/'+str(draft['id']),json={'brief':'phone edit','revision':0})
    assert saved.status_code==200,saved.text
    stale=web.patch('/api/drafts/'+str(draft['id']),json={'brief':'stale laptop','revision':0})
    assert stale.status_code==409
    assert web.get('/api/drafts/'+str(draft['id'])).json()['brief']=='phone edit'


def test_brands_ownership_and_key_scope():
    native,web,uid,_=native_account();other,otherweb,otheruid,_=native_account()
    with SessionLocal() as db:
        b=Brand(user_id=uid,name='Second');foreign=Brand(user_id=otheruid,name='Foreign');db.add_all([b,foreign]);db.commit();bid,fid=b.id,foreign.id
    key=secrets.token_urlsafe(20)
    draft=native.post('/api/v1/drafts',headers={'Idempotency-Key':key,'X-Zova-Brand':str(bid)}).json()
    assert native.get('/api/v1/drafts/'+str(draft['id'])).status_code==404
    assert other.get('/api/v1/drafts/'+str(draft['id']),headers={'X-Zova-Brand':str(bid)}).status_code==404
    assert native.get('/api/v1/drafts',headers={'X-Zova-Brand':str(fid)}).status_code==404
    own=native.get('/api/v1/drafts/'+str(draft['id']),headers={'X-Zova-Brand':str(bid)})
    assert own.status_code==200
    assert native.post('/api/v1/drafts',headers={'Idempotency-Key':key}).json()['id']!=draft['id']


def test_pagination_and_concurrent_request_deduplication():
    native,web,uid,pair=native_account();key=secrets.token_urlsafe(20)
    def create(_):
        with TestClient(app) as client:
            return client.post('/api/v1/drafts',headers={'Authorization':'Bearer '+pair['access_token'],'Idempotency-Key':key})
    with ThreadPoolExecutor(max_workers=2) as executor: results=list(executor.map(create,range(2)))
    assert all(r.status_code==200 for r in results),[r.text for r in results]
    assert results[0].json()['id']==results[1].json()['id']
    for _ in range(3): native.post('/api/v1/drafts',headers={'Idempotency-Key':secrets.token_urlsafe(20)})
    first=native.get('/api/v1/drafts?limit=2').json()
    second=native.get('/api/v1/drafts',params={'limit':2,'before_id':first['next_before_id']}).json()
    assert len(first['items'])==len(second['items'])==2
    assert not {r['id'] for r in first['items']} & {r['id'] for r in second['items']}
    assert second['next_before_id'] is None


def test_logout_and_foreign_session_revoke():
    native,_,uid,pair=native_account();other,_,_,foreign=native_account()
    assert native.delete('/api/v1/auth/sessions/'+foreign['session_id']).status_code==404
    assert native.get('/api/v1/auth/sessions').json()['sessions'][0]['current'] is True
    assert native.post('/api/v1/auth/logout').status_code==204
    assert native.get('/api/v1/me').status_code==401
    assert other.get('/api/v1/me').status_code==200


def test_runtime_scaling_configuration_refuses_unsafe_defaults(monkeypatch):
    from nova.runtime import validate_runtime,database_options
    monkeypatch.setenv('DATABASE_URL','sqlite:///synthetic-config-only.db')
    monkeypatch.setenv('ZOVA_WEB_REPLICAS','2')
    with pytest.raises(ValueError,match='external'): validate_runtime()
    monkeypatch.setenv('ZOVA_SCHEDULER_MODE','external')
    with pytest.raises(ValueError,match='PostgreSQL'): validate_runtime()
    monkeypatch.setenv('DATABASE_URL','postgresql://localhost/synthetic')
    with pytest.raises(ValueError,match='storage'): validate_runtime()
    monkeypatch.setenv('S3_BUCKET','synthetic')
    monkeypatch.setenv('ZOVA_SCHEMA_MODE','verify')
    assert validate_runtime()=='external'
    assert database_options('postgresql://localhost/test')['max_overflow']==5


def test_mobile_media_is_private_and_owned():
    import io
    from PIL import Image
    native,_,_,_=native_account();other,_,_,_=native_account()
    image=io.BytesIO();Image.new('RGB',(2,2)).save(image,format='PNG')
    uploaded=native.post('/api/v1/media',files={'files':('example.png',image.getvalue(),'image/png')})
    assert uploaded.status_code==200,uploaded.text
    url=uploaded.json()['assets'][0]['url']
    assert url.startswith('/api/v1/media/')
    assert native.get(url).content==image.getvalue()
    assert other.get(url).status_code==404
    assert TestClient(app).get(url).status_code==401


def test_mobile_publication_preserves_immutable_review_and_dedup(monkeypatch):
    from test_reviewed_publication import prepared
    import nova.app as module
    web,uid,_,body=prepared()
    pair=TestClient(app).post('/api/v1/auth/token',json=code_for(web)).json()
    native=TestClient(app,headers={'Authorization':'Bearer '+pair['access_token']})
    calls=[]
    monkeypatch.setattr(module,'publish_platform',lambda *a,**k:calls.append(k) or {'post_id':'synthetic'})
    reviewed=native.post('/api/v1/publish-review',json=body)
    assert reviewed.status_code==200,reviewed.text
    approved={**body,'review_token':reviewed.json()['review_token']}
    modified={**approved,'variants':{'x':{'posts':['Unapproved']}}}
    assert native.post('/api/v1/publish',json=modified).status_code==409
    assert not calls
    assert native.post('/api/v1/publish',json=approved).status_code==200
    assert native.post('/api/v1/publish',json=approved).status_code==200
    assert len(calls)==1


@pytest.mark.parametrize('placement', ['post', 'story'])
def test_native_instagram_matches_web_review_and_prevents_format_swap(monkeypatch, placement):
    from test_instagram_formats import story_draft
    import nova.app as module
    web, body = story_draft(monkeypatch, placement)
    pair = TestClient(app).post('/api/v1/auth/token', json=code_for(web)).json()
    native = TestClient(app, headers={'Authorization': 'Bearer '+pair['access_token']})
    calls = []
    monkeypatch.setattr(module, 'publish_platform', lambda *a, **k: calls.append(k) or {'post_id': 'synthetic'})
    review = native.post('/api/v1/publish-review', json=body)
    assert review.status_code == 200, review.text
    assert review.json()['snapshot']['targets']['instagram']['format_label'] == ('Story' if placement == 'story' else 'Post · feed')
    approved = {**body, 'review_token': review.json()['review_token']}
    changed = {**approved, 'publish_options': {'instagram': {'format': 'post' if placement == 'story' else 'story'}}}
    assert native.post('/api/v1/publish', json=changed).status_code == 409
    assert not calls
    assert native.post('/api/v1/publish', json=approved).status_code == 200
    assert native.post('/api/v1/publish', json=approved).status_code == 200
    assert len(calls) == 1 and calls[0]['options']['format'] == placement


def test_background_generation_survives_disconnect_and_refuses_stale_edits(monkeypatch):
    import nova.ai as ai
    from nova.generation_jobs import process_jobs
    monkeypatch.setenv('ZOVA_AI_JOBS_ENABLED','true')
    native,web,uid,pair=native_account()
    calls=[]
    monkeypatch.setattr(ai,'generate_variants',lambda **kw:calls.append(kw) or {'x':{'posts':['Synthetic caption']}})
    draft=native.post('/api/v1/drafts',headers={'Idempotency-Key':secrets.token_urlsafe(20)}).json()
    body={'draft_id':draft['id'],'revision':0,'brief':'Pottery','platforms':['x']}
    key=secrets.token_urlsafe(20)
    queued=native.post('/api/v1/generation-jobs',headers={'Idempotency-Key':key},json=body)
    assert queued.status_code==202,queued.text
    job=queued.json()
    assert native.post('/api/v1/generation-jobs',headers={'Idempotency-Key':key},json=body).json()['id']==job['id']
    assert native.post('/api/v1/generation-jobs',headers={'Idempotency-Key':key},json={**body,'brief':'Other'}).status_code==409
    native.close()
    assert process_jobs()==1
    assert len(calls)==1
    assert web.get('/api/drafts/'+str(draft['id'])).json()['variants']['x']['posts']==['Synthetic caption']
    native=TestClient(app,headers={'Authorization':'Bearer '+pair['access_token']})
    assert native.get('/api/v1/generation-jobs/'+job['id']).json()['status']=='succeeded'
    body['revision']=1
    queued=native.post('/api/v1/generation-jobs',headers={'Idempotency-Key':secrets.token_urlsafe(20)},json=body).json()
    assert web.patch('/api/drafts/'+str(draft['id']),json={'brief':'Laptop edit','revision':1}).status_code==200
    assert process_jobs()==1
    assert native.get('/api/v1/generation-jobs/'+queued['id']).json()['status']=='failed'
    assert len(calls)==1


def test_queue_cancel_ownership_and_account_revocation(monkeypatch):
    from nova.generation_jobs import process_jobs
    monkeypatch.setenv('ZOVA_AI_JOBS_ENABLED','true')
    native,_,uid,_=native_account();other,_,_,_=native_account()
    draft=native.post('/api/v1/drafts',headers={'Idempotency-Key':secrets.token_urlsafe(20)}).json()
    body={'draft_id':draft['id'],'revision':0,'brief':'Pottery','platforms':['x']}
    job=native.post('/api/v1/generation-jobs',headers={'Idempotency-Key':secrets.token_urlsafe(20)},json=body).json()
    url='/api/v1/generation-jobs/'+job['id']
    assert other.get(url).status_code==404
    assert other.post(url+'/cancel').status_code==404
    assert native.post(url+'/cancel').json()['status']=='cancelled'
    assert process_jobs()==0
    job=native.post('/api/v1/generation-jobs',headers={'Idempotency-Key':secrets.token_urlsafe(20)},json=body).json()
    with SessionLocal() as db:
        user=db.get(User,uid);user.auth_version+=1;db.commit()
    assert process_jobs()==1
    from nova.db import GenerationJob
    with SessionLocal() as db: assert db.get(GenerationJob,job['id']).status=='failed'


def test_schema_verify_is_read_only_and_missing_table_fails():
    from sqlalchemy import create_engine,MetaData,Table,Column,Integer,event
    from nova.runtime import prepare_schema
    from unittest.mock import patch
    engine=create_engine('sqlite://')
    meta=MetaData();Table('synthetic',meta,Column('id',Integer,primary_key=True))
    with patch.dict('os.environ',{'ZOVA_SCHEMA_MODE':'verify'}):
        with pytest.raises(RuntimeError,match='incomplete'):prepare_schema(meta,engine)
        meta.create_all(engine)
        statements=[]
        event.listen(engine,'before_cursor_execute',lambda c,cur,statement,*_:statements.append(statement))
        prepare_schema(meta,engine)
        assert not any(s.lstrip().upper().startswith(('CREATE','ALTER','INSERT','UPDATE','DELETE','DROP')) for s in statements)


def test_postgres_worker_lock_prevents_duplicate_worker(monkeypatch):
    from nova.db import engine
    if engine.dialect.name!='postgresql':pytest.skip('Real PostgreSQL advisory lock coverage in release CI')
    from sqlalchemy import text
    from nova.worker import run,LOCK_ID
    monkeypatch.setenv('ZOVA_SCHEDULER_MODE','external')
    monkeypatch.setenv('S3_BUCKET','synthetic-worker-only')
    monkeypatch.setenv('ZOVA_SCHEMA_MODE','verify')
    with engine.connect() as connection:
        connection.execute(text('SELECT pg_advisory_lock(:key)'),{'key':LOCK_ID});connection.commit()
        try:
            with pytest.raises(RuntimeError,match='Another dedicated worker'):run()
        finally:
            connection.execute(text('SELECT pg_advisory_unlock(:key)'),{'key':LOCK_ID});connection.commit()


def test_every_shared_route_is_in_the_contract_and_strategy_works():
    from nova.api_v1 import SHARED_PATHS
    paths=app.openapi()['paths']
    assert all('/api/v1/'+path[len('/api/'):] in paths for path in SHARED_PATHS)
    native,_,_,_=native_account()
    assert native.get('/api/v1/strategy').status_code==200
    assert native.get('/api/v1/strategy/actions').status_code==200
    assert native.get('/api/v1/schedules').status_code==200


def test_deleted_draft_is_not_recreated_by_retry():
    native,_,_,_=native_account();key=secrets.token_urlsafe(20)
    draft=native.post('/api/v1/drafts',headers={'Idempotency-Key':key}).json()
    assert native.delete('/api/v1/drafts/'+str(draft['id'])).status_code==204
    assert native.post('/api/v1/drafts',headers={'Idempotency-Key':key}).status_code==409


def test_refresh_race_does_not_leave_a_valid_replayed_family():
    native,_,uid,pair=native_account()
    def refresh(_):
        return TestClient(app).post('/api/v1/auth/refresh',json={'refresh_token':pair['refresh_token']})
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(refresh,range(2)))
    assert sorted(r.status_code for r in responses)==[200,401]
    success=next(r.json() for r in responses if r.status_code==200)
    client=TestClient(app,headers={'Authorization':'Bearer '+success['access_token']})
    assert client.get('/api/v1/me').status_code==401


def test_interrupted_job_is_not_replayed(monkeypatch):
    from nova.db import GenerationJob
    from nova.generation_jobs import process_jobs
    import nova.ai as ai
    monkeypatch.setenv('ZOVA_AI_JOBS_ENABLED','true')
    native,_,uid,_=native_account()
    draft=native.post('/api/v1/drafts',headers={'Idempotency-Key':secrets.token_urlsafe(20)}).json()
    job=native.post('/api/v1/generation-jobs',headers={'Idempotency-Key':secrets.token_urlsafe(20)},json={'draft_id':draft['id'],'revision':0,'brief':'Idea','platforms':['x']}).json()
    with SessionLocal() as db:
        row=db.get(GenerationJob,job['id']);row.status='running';row.updated_at=utcnow()-timedelta(minutes=20);db.commit()
    monkeypatch.setattr(ai,'generate_variants',lambda **_:pytest.fail('Interrupted work must not be retried'))
    assert process_jobs()==0
    assert native.get('/api/v1/generation-jobs/'+job['id']).json()['status']=='interrupted'


def test_mobile_lifecycle_export_and_erasure_include_new_data():
    from nova.data_lifecycle import export_account,erase_local_account
    native,web,uid,pair=native_account()
    with SessionLocal() as db:
        export=export_account(db,uid)
        assert export['zova_mobile_sessions'][0]['id']==pair['session_id']
        assert 'access_hash' not in str(export)
        erase_local_account(db,uid,'synthetic-mobile-erasure',writes_paused=True)
        assert db.get(MobileSession,pair['session_id']) is None
    assert native.get('/api/v1/me').status_code==401


def test_native_ai_calls_use_shared_server_model(monkeypatch):
    import nova.ai as ai
    # Both clients call the same handler. The device never supplies a model/key.
    native,_,_,_=native_account()
    draft=native.post('/api/v1/drafts',headers={'Idempotency-Key':secrets.token_urlsafe(20)}).json()
    selected=[]
    def model_output(**kwargs):
        selected.append(ai._model());return {'x':{'posts':['Synthetic model test']}}
    monkeypatch.setattr(ai,'generate_variants',model_output)
    monkeypatch.setenv('OPENAI_MODEL','synthetic-server-model')
    response=native.post('/api/v1/ai/generate',json={'draft_id':draft['id'],'revision':0,'brief':'Pottery','platforms':['x'],'model':'untrusted-device-override'})
    assert response.status_code==200,response.text
    assert selected==['synthetic-server-model']


def test_published_contract_matches_runtime():
    import json
    from pathlib import Path
    from scripts.export_mobile_contract import contract
    assert contract()==json.loads((Path(__file__).resolve().parents[1]/'docs/api/mobile-v1.openapi.json').read_text(encoding='utf-8'))
