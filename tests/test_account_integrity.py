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


def test_concurrent_password_changes_cannot_share_a_security_version(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from nova import app as module
    from nova.security import verify_password
    _,uid,token,_=account()
    clients=[TestClient(app),TestClient(app)]
    for client in clients:client.cookies.set('nova_session',token)
    barrier=Barrier(2)
    def check_together(raw,hashed):
        result=verify_password(raw,hashed)
        barrier.wait(timeout=10)
        return result
    monkeypatch.setattr(module,'verify_password',check_together)
    passwords=['Concurrent-password-one!','Concurrent-password-two!']
    def change(index):
        return clients[index].post('/account/password',data={'current_password':'old-password-123',
            'new_password':passwords[index],'new_password_confirmation':passwords[index]},follow_redirects=False)
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(change,[0,1]))
    assert sorted(response.status_code for response in results)==[303,409]
    winner=next(index for index,response in enumerate(results) if response.status_code==303)
    assert user_from_session(token) is None
    assert user_from_session(results[winner].cookies.get('nova_session')).id==uid
    assert not results[1-winner].cookies.get('nova_session')
    with SessionLocal() as db:
        user=db.get(User,uid)
        assert user.auth_version==1
        assert verify_password(passwords[winner],user.password_hash)
        assert not verify_password(passwords[1-winner],user.password_hash)


def test_password_change_cannot_bypass_concurrent_mfa_enrollment(monkeypatch):
    from nova import app as module
    from nova.db import MfaSettings
    from nova.security import encrypt, verify_password
    client,uid,token,_=account()
    def enroll_before_update(password):
        with SessionLocal() as db:
            db.get(User,uid).auth_version+=1
            db.add(MfaSettings(user_id=uid,enabled=True,encrypted_secret=encrypt('synthetic')))
            db.commit()
        return hash_password(password)
    monkeypatch.setattr(module,'hash_password',enroll_before_update)
    response=client.post('/account/password',data={'current_password':'old-password-123',
        'new_password':'Replacement-password-2026!','new_password_confirmation':'Replacement-password-2026!'},follow_redirects=False)
    assert response.status_code==409
    assert not response.cookies.get('nova_session')
    assert user_from_session(token) is None
    with SessionLocal() as db:
        assert db.get(User,uid).auth_version==1
        assert verify_password('old-password-123',db.get(User,uid).password_hash)
        assert db.get(MfaSettings,uid).enabled


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


def test_billing_return_cannot_grant_access_from_payment_status(monkeypatch):
    import nova.app as module
    client, uid, _, _ = account()
    monkeypatch.setattr(module.billing,'fetch_checkout_session',lambda _: {'client_reference_id':str(uid),'customer':'cus_unlinked','subscription':'sub_unlinked','payment_status':'paid','livemode':False})
    assert client.get('/billing/success?session_id=cs_synthetic',follow_redirects=False).status_code == 403
    with SessionLocal() as db:
        user=db.get(User,uid)
        assert user.stripe_customer_id is None
        assert user.subscription_status == 'none'
