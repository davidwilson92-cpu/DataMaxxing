import hashlib
import hmac
import secrets
import time

from fastapi.testclient import TestClient
from sqlalchemy import select
from nova.app import app
from nova.db import SessionLocal, User
from nova.security import hash_password, make_user_session, user_from_session


def account():
    email = secrets.token_hex(8) + "@example.test"
    with SessionLocal() as db:
        user = User(email=email, display_name="Original", password_hash=hash_password("old-password-123"))
        db.add(user); db.commit(); db.refresh(user); uid = user.id
    client = TestClient(app)
    token = make_user_session(uid)
    client.cookies.set("nova_session", token)
    return client, uid, token, email


def test_password_persists_and_revokes_old_session():
    client, uid, token, email = account()
    result = client.post('/account/password', data={"current_password":"old-password-123", "new_password":"replacement-password-123", "new_password_confirmation":"replacement-password-123"}, follow_redirects=False)
    assert result.headers['location'] == '/account?saved=password'
    assert user_from_session(token) is None
    assert user_from_session(result.cookies.get('nova_session')).id == uid
    assert 'Incorrect' in client.post('/login', data={"email":email,"password":"old-password-123"}, follow_redirects=False).headers['location']
    assert client.post('/login', data={"email":email,"password":"replacement-password-123"}, follow_redirects=False).headers['location'] == '/studio'


def test_logout_revokes_only_presented_session_and_accepts_legacy():
    client, uid, token, _ = account()
    other = make_user_session(uid)
    client.post('/logout')
    assert user_from_session(token) is None
    assert user_from_session(other).id == uid
    payload = f'{uid}.{int(time.time())+3600}'
    legacy = payload + '.' + hmac.new(b'test-session-secret', payload.encode(), hashlib.sha256).hexdigest()
    assert user_from_session(legacy).id == uid
    client.cookies.set('nova_session', legacy)
    client.post('/logout')
    assert user_from_session(legacy) is None


def test_profile_persists_and_guidance_can_be_cleared():
    client, uid, _, _ = account()
    client.post('/account/profile',data={'display_name':'Updated','guidance':'Avoid jargon'})
    client.post('/account/profile',data={'display_name':'Updated','guidance':''})
    with SessionLocal() as db:
        user = db.get(User,uid)
        assert user.display_name == 'Updated'
        assert user.preferences.things_to_avoid == ''


def test_billing_success_persists_owned_references(monkeypatch):
    import nova.app as module
    client, uid, _, _ = account()
    monkeypatch.setattr(module.billing,'fetch_checkout_session',lambda _: {'client_reference_id':str(uid),'customer':'synthetic-customer','subscription':'synthetic-subscription','payment_status':'paid'})
    assert client.get('/billing/success?session_id=synthetic',follow_redirects=False).status_code == 303
    with SessionLocal() as db:
        user=db.get(User,uid)
        assert user.stripe_customer_id == 'synthetic-customer'
        assert user.subscription_status == 'active'
