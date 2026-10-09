import secrets
import pytest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from fastapi.testclient import TestClient
from sqlalchemy import event, select, func
from sqlalchemy.exc import IntegrityError

from nova import app as module
from nova import db as models
from nova.security import hash_password, user_from_session, verify_password, decrypt
from nova.tenant_migration import workspace_key


def payload(email, **changes):
    return {'name':'Atomic Signup','email':email,'country':'GB','password':'Synthetic-password-2026!',
            'password_confirmation':'Synthetic-password-2026!','accept_terms':'yes',
            'marketing_consent':'yes',**changes}


def test_signup_preference_failure_rolls_back_identity_and_allows_retry(monkeypatch,caplog):
    monkeypatch.setenv('RATE_LIMIT_SCALE','100')
    email=secrets.token_hex(8)+'@example.test'
    attempted=[]
    def fail_preferences(mapper,connection,target):
        attempted.append(target.user_id)
        raise IntegrityError('synthetic statement',{},RuntimeError('Private database diagnostic'))
    event.listen(models.CreatorPreferences,'before_insert',fail_preferences)
    client=TestClient(module.app,raise_server_exceptions=False)
    try:
        response=client.post('/signup',data=payload(email),follow_redirects=False)
    finally:event.remove(models.CreatorPreferences,'before_insert',fail_preferences)
    with models.SessionLocal() as db:
        assert db.scalar(select(models.User).where(models.User.email==email)) is None
        assert attempted
        assert db.get(models.TenantWorkspace,workspace_key(attempted[0])) is None
        assert db.get(models.WorkspaceMembership,(workspace_key(attempted[0]),attempted[0])) is None
    assert response.status_code==303 and 'try+again' in response.headers['location']
    assert not response.cookies.get('nova_session')
    saved=decrypt(response.cookies.get('zova_signup_input'))
    assert email in saved and 'Synthetic-password' not in saved
    assert 'Private database diagnostic' not in caplog.text
    retry=client.post('/signup',data=payload(email),follow_redirects=False)
    assert retry.status_code==303 and retry.headers['location']=='/onboarding/socials'
    uid=user_from_session(retry.cookies.get('nova_session')).id
    with models.SessionLocal() as db:
        user=db.get(models.User,uid)
        assert user.display_name=='Atomic Signup' and user.country_code=='GB'
        assert user.terms_accepted_at and user.marketing_consent and user.marketing_consent_at
        assert user.subscription_status=='none' and user.stripe_customer_id is None
        assert db.scalar(select(func.count()).select_from(models.CreatorPreferences).where(models.CreatorPreferences.user_id==uid))==1
        assert db.get(models.WorkspaceMembership,(workspace_key(uid),uid)).role=='owner'
        assert db.scalar(select(func.count()).select_from(models.SocialConnection).where(models.SocialConnection.user_id==uid))==0


def test_concurrent_signup_has_one_complete_account_and_a_friendly_conflict(monkeypatch):
    monkeypatch.setenv('RATE_LIMIT_SCALE','100')
    email=secrets.token_hex(8)+'@example.test'
    barrier=Barrier(2)
    def together(password):
        barrier.wait(timeout=15)
        return hash_password(password)
    monkeypatch.setattr(module,'hash_password',together)
    passwords=['First-concurrent-passphrase!','Second-concurrent-passphrase!']
    def submit(index):
        return TestClient(module.app,raise_server_exceptions=False).post('/signup',
            data=payload(email if index==0 else email.upper(),password=passwords[index],
                         password_confirmation=passwords[index],name=f'Person {index}'),follow_redirects=False)
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(submit,[0,1]))
    assert [r.status_code for r in responses]==[303,303]
    winner=next(i for i,r in enumerate(responses) if r.headers['location']=='/onboarding/socials')
    assert 'already+exists' in responses[1-winner].headers['location']
    assert not responses[1-winner].cookies.get('nova_session')
    uid=user_from_session(responses[winner].cookies.get('nova_session')).id
    with models.SessionLocal() as db:
        user=db.scalars(select(models.User).where(models.User.email==email)).one()
        assert user.id==uid and user.display_name==f'Person {winner}'
        assert verify_password(passwords[winner],user.password_hash)
        assert db.scalar(select(func.count()).select_from(models.CreatorPreferences).where(models.CreatorPreferences.user_id==uid))==1
        assert db.get(models.WorkspaceMembership,(workspace_key(uid),uid)).active


def test_new_account_session_does_not_upgrade_an_intervening_security_change(monkeypatch):
    from nova.security import encrypt
    monkeypatch.setenv('RATE_LIMIT_SCALE','100')
    email=secrets.token_hex(8)+'@example.test'
    original=module.make_user_session
    def enrollment(uid,*,expected_auth_version=None,**kwargs):
        with models.SessionLocal() as db:
            db.get(models.User,uid).auth_version+=1
            db.add(models.MfaSettings(user_id=uid,enabled=True,encrypted_secret=encrypt('synthetic')))
            db.commit()
        return original(uid,expected_auth_version=expected_auth_version,**kwargs)
    monkeypatch.setattr(module,'make_user_session',enrollment)
    response=TestClient(module.app,raise_server_exceptions=False).post('/signup',data=payload(email),follow_redirects=False)
    assert response.status_code==303 and response.headers['location'].startswith('/login?')
    assert not response.cookies.get('nova_session')
    with models.SessionLocal() as db:
        user=db.scalars(select(models.User).where(models.User.email==email)).one()
        assert user.auth_version==1 and db.get(models.MfaSettings,user.id).enabled
        assert user.preferences is not None


def test_duplicate_signup_does_not_repair_revoked_membership_or_change_connections():
    from nova.security import make_user_session
    email=secrets.token_hex(8)+'@example.test'
    with models.SessionLocal() as db:
        user=models.User(email=email,password_hash=hash_password('Existing-account-passphrase!'))
        db.add(user);db.flush();uid=user.id
        db.add(models.SocialConnection(user_id=uid,platform='instagram',account_id='synthetic-account',encrypted_access_token='synthetic-preserved'))
        db.get(models.WorkspaceMembership,(workspace_key(uid),uid)).active=False
        db.commit();db.refresh(user);old_hash=user.password_hash;old_version=user.auth_version
    token=make_user_session(uid)
    response=TestClient(module.app).post('/signup',data=payload(email),follow_redirects=False)
    assert 'already+exists' in response.headers['location'] and not response.cookies.get('nova_session')
    assert user_from_session(token).id==uid
    with models.SessionLocal() as db:
        user=db.get(models.User,uid)
        assert user.password_hash==old_hash and user.auth_version==old_version
        assert not db.get(models.WorkspaceMembership,(workspace_key(uid),uid)).active
        assert db.scalars(select(models.SocialConnection).where(models.SocialConnection.user_id==uid)).one().encrypted_access_token=='synthetic-preserved'


def test_apple_identity_failure_rolls_back_new_account_workspace_and_preferences(monkeypatch):
    from test_apple_account_regressions import callback
    email=secrets.token_hex(8)+'@example.test'
    attempted=[]
    def fail_identity(mapper,connection,target):
        attempted.append(target.user_id)
        raise IntegrityError('synthetic identity insert',{},RuntimeError('Private identity diagnostic'))
    event.listen(models.AuthIdentity,'before_insert',fail_identity)
    response=None
    try:
        try:response=callback(monkeypatch,email)
        except IntegrityError:pass  # Allows the old partial-commit defect to be inspected.
    finally:event.remove(models.AuthIdentity,'before_insert',fail_identity)
    with models.SessionLocal() as db:
        assert db.scalar(select(models.User).where(models.User.email==email)) is None
        assert attempted and db.get(models.TenantWorkspace,workspace_key(attempted[0])) is None
        assert db.scalar(select(models.CreatorPreferences).where(models.CreatorPreferences.user_id==attempted[0])) is None
    assert response.status_code==303 and 'try+again' in response.headers['location']
    assert not response.cookies.get('nova_session')
    retried=callback(monkeypatch,email)
    assert retried.headers['location']=='/onboarding/socials'
    uid=user_from_session(retried.cookies.get('nova_session')).id
    with models.SessionLocal() as db:
        assert db.get(models.User,uid).preferences is not None
        assert db.scalars(select(models.AuthIdentity).where(models.AuthIdentity.user_id==uid)).one().provider=='apple'


def test_apple_state_is_claimed_once_before_provider_exchange(monkeypatch):
    from types import SimpleNamespace
    from nova.security import hash_api_key
    state=secrets.token_hex(20)
    digest=hash_api_key(state)
    email=secrets.token_hex(8)+'@example.test'
    with models.SessionLocal() as db:
        db.add(models.AuthState(provider='apple',state_hash=digest,nonce_hash=hash_api_key('synthetic-nonce'),intent='signup'))
        db.commit()
    barrier=Barrier(2)
    def both_read_unused(session,target):
        if isinstance(target,models.AuthState) and target.state_hash==digest:barrier.wait(timeout=15)
    event.listen(models.SessionLocal.class_,'loaded_as_persistent',both_read_unused)
    exchanges=[]
    def exchange(*args,**kwargs):
        exchanges.append(True)
        return SimpleNamespace(status_code=200)
    monkeypatch.setenv('APPLE_CLIENT_ID','synthetic-client')
    monkeypatch.setattr(module,'apple_client_secret',lambda:'synthetic-secret')
    monkeypatch.setattr(module.httpx,'post',exchange)
    monkeypatch.setattr(module.jwt,'PyJWKClient',lambda *a:SimpleNamespace(get_signing_key_from_jwt=lambda *a:SimpleNamespace(key='synthetic-key')))
    monkeypatch.setattr(module.jwt,'decode',lambda *a,**k:{'nonce':'synthetic-nonce','sub':state,'email':email,'email_verified':True})
    def submit(_):
        client=TestClient(module.app,base_url='https://testserver',raise_server_exceptions=False)
        client.cookies.set('__Host-zova_apple_state',state)
        return client.post('/auth/apple/callback',
            data={'code':'synthetic','id_token':'synthetic','state':state},follow_redirects=False)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(submit,[0,1]))
    finally:event.remove(models.SessionLocal.class_,'loaded_as_persistent',both_read_unused)
    assert exchanges==[True]
    assert sorted(r.status_code for r in responses)==[303,400]


@pytest.mark.parametrize('platform',['x','instagram','instagram_facebook','meta','tiktok'])
def test_social_connection_state_has_one_claim_across_concurrent_callbacks(platform):
    from fastapi import HTTPException
    from nova.security import hash_api_key
    raw=secrets.token_hex(24);digest=hash_api_key(raw)
    with models.SessionLocal() as db:
        user=models.User(email=secrets.token_hex(8)+'@example.test',password_hash='synthetic-unused')
        db.add(user);db.flush()
        row=models.OAuthState(user_id=user.id,platform=platform,state_hash=digest)
        db.add(row);db.commit();state_id=row.id
    barrier=Barrier(2)
    def both_read_unused(session,target):
        if isinstance(target,models.OAuthState) and target.state_hash==digest:barrier.wait(timeout=15)
    event.listen(models.SessionLocal.class_,'loaded_as_persistent',both_read_unused)
    def claim(_):
        with models.SessionLocal() as db:
            try:
                claimed=module._state_row(db,raw,platform)
                return ('claimed',claimed.id,claimed.used)
            except HTTPException as exc:return ('rejected',exc.status_code)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(claim,[0,1]))
    finally:event.remove(models.SessionLocal.class_,'loaded_as_persistent',both_read_unused)
    assert sorted(result[0] for result in results)==['claimed','rejected']
    assert ('claimed',state_id,True) in results and ('rejected',400) in results
