import secrets
from types import SimpleNamespace
from fastapi.testclient import TestClient
from sqlalchemy import select
from nova import app as app_module
from nova.app import app
from nova.db import SessionLocal, User, AuthState, AuthIdentity
from nova.security import hash_api_key
from test_account_integrity import account


def callback(monkeypatch, email, verified=True):
    state=secrets.token_hex(16)
    with SessionLocal() as db:
        db.add(AuthState(provider='apple',state_hash=hash_api_key(state),nonce_hash=hash_api_key('synthetic-nonce'),intent='login'));db.commit()
    monkeypatch.setenv('APPLE_CLIENT_ID','synthetic-client')
    monkeypatch.setattr(app_module,'apple_client_secret',lambda:'synthetic-secret')
    monkeypatch.setattr(app_module.httpx,'post',lambda *a,**k:SimpleNamespace(status_code=200,json=lambda:{'id_token':'synthetic'}))
    monkeypatch.setattr(app_module.jwt,'PyJWKClient',lambda *a,**k:SimpleNamespace(get_signing_key_from_jwt=lambda *a:SimpleNamespace(key='synthetic-key')))
    from test_apple_token_validation import identity_claims
    claims=identity_claims('synthetic-nonce',sub=state,email=email,email_verified=verified)
    monkeypatch.setattr(app_module.jwt,'decode',lambda *a,**k:claims)
    client=TestClient(app,base_url='https://testserver')
    client.cookies.set('__Host-zova_apple_state',state)
    return client.post('/auth/apple/callback',data={'code':'synthetic','id_token':'synthetic','state':state},follow_redirects=False)


def test_new_apple_account_initialises_own_workspace(monkeypatch):
    email=secrets.token_hex(8)+'@example.test'
    response=callback(monkeypatch,email)
    assert response.status_code==303 and response.headers['location']=='/onboarding/socials'
    assert response.cookies.get('nova_session')
    with SessionLocal() as db:
        user=db.scalar(select(User).where(User.email==email))
        assert user and user.email_verified_at


def test_unverified_apple_email_cannot_link_existing_user(monkeypatch):
    _,uid,_,email=account()
    response=callback(monkeypatch,email,False)
    assert 'did+not+verify' in response.headers['location']
    assert not response.cookies.get('nova_session')
    with SessionLocal() as db:
        assert db.scalar(select(AuthIdentity).where(AuthIdentity.user_id==uid)) is None


def test_inactive_apple_account_cannot_sign_in(monkeypatch):
    _,uid,_,email=account()
    with SessionLocal() as db:
        db.get(User,uid).active=False;db.commit()
    response=callback(monkeypatch,email)
    assert 'not+available' in response.headers['location'] and not response.cookies.get('nova_session')


def test_concurrent_mfa_enable_cannot_be_bypassed_by_apple(monkeypatch):
    _,uid,_,email=account()
    from nova import security
    from nova.db import MfaSettings
    original=app_module.make_user_session
    def intervening_enrollment(user_id,*,expected_auth_version=None):
        with SessionLocal() as db:
            db.get(User,user_id).auth_version+=1
            db.add(MfaSettings(user_id=user_id,enabled=True,encrypted_secret=security.encrypt('synthetic')))
            db.commit()
        return original(user_id,expected_auth_version=expected_auth_version)
    monkeypatch.setattr(app_module,'make_user_session',intervening_enrollment)
    response=callback(monkeypatch,email)
    assert 'sign-in+changed' in response.headers['location']
    assert not response.cookies.get('nova_session')
