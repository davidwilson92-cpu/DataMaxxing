"""Optional TOTP with synthetic accounts, no provider or email calls."""
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from fastapi.testclient import TestClient
from test_account_integrity import account
from nova.app import app
from nova import mfa, security
from nova.db import SessionLocal, User, MfaSettings, MfaChallenge, utcnow
from nova.data_lifecycle import erase_local_account, export_account


def enrolled():
    client, uid, old_token, email = account()
    assert client.post('/mfa/setup', data={'password':'wrong'}).status_code == 200
    with SessionLocal() as db:
        assert db.get(MfaSettings, uid) is None
    response = client.post('/mfa/setup', data={'password':'old-password-123'})
    assert response.status_code == 200
    with SessionLocal() as db:
        settings = db.get(MfaSettings, uid)
        assert not settings.enabled
        secret = security.decrypt(settings.encrypted_secret)
        assert secret in response.text and secret != settings.encrypted_secret
    code = mfa.totp(secret, int(time.time())//30)
    response = client.post('/mfa/enable', data={'code':code})
    assert response.status_code == 200 and 'shown only once' in response.text
    codes = re.findall(r'<code>([0-9a-f-]{23})</code>', response.text)
    assert len(codes) == 10
    client.cookies.clear()
    client.cookies.update(response.cookies)
    assert security.user_from_session(old_token) is None
    assert client.get('/account').status_code == 200
    return client, uid, email, secret, codes


def pending_login(email):
    client = TestClient(app)
    response = client.post('/login', data={'email':email,'password':'old-password-123'}, follow_redirects=False)
    assert response.status_code == 303 and response.headers['location'] == '/mfa/challenge'
    assert not client.cookies.get('nova_session')
    assert client.get('/studio', follow_redirects=False).status_code in (303, 401)
    return client


def test_rfc_totp_known_vector():
    # RFC 6238 SHA-1 vector truncated to six digits; independent expected value.
    assert mfa.totp('GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ', 59//30) == '287082'


def test_optional_setup_recovery_codes_and_login_replay():
    owner, uid, email, secret, codes = enrolled()
    with SessionLocal() as db:
        row = db.get(MfaSettings, uid)
        assert row.enabled and codes[0] not in row.recovery_hashes_json
        exported = json.dumps(export_account(db, uid))
        assert secret not in exported and 'encrypted_secret' not in exported and 'recovery_hashes' not in exported
    page = owner.get('/mfa/setup')
    assert secret not in page.text and codes[0] not in page.text
    login = pending_login(email)
    assert 'invalid or already used' in login.post('/mfa/challenge', data={'code':'invalid'}).text
    # Enrollment consumed the current code. A fresh next-step code is accepted within drift tolerance.
    fresh_code = mfa.totp(secret, int(time.time())//30 + 1)
    response = login.post('/mfa/challenge', data={'code':fresh_code}, follow_redirects=False)
    assert response.status_code == 303 and response.headers['location'] == '/studio'
    assert login.get('/studio').status_code == 200
    assert login.post('/mfa/challenge', data={'code':codes[0]}).status_code == 400
    second = pending_login(email)
    assert 'invalid or already used' in second.post('/mfa/challenge', data={'code':fresh_code}).text
    assert second.post('/mfa/challenge', data={'code':codes[0]}, follow_redirects=False).status_code == 303
    third = pending_login(email)
    assert 'invalid or already used' in third.post('/mfa/challenge', data={'code':codes[0]}).text


def test_challenge_is_expiring_bound_to_auth_version_and_cookie(monkeypatch):
    _, uid, email, _, codes = enrolled()
    login = pending_login(email)
    forged = TestClient(app)
    forged.cookies.set(mfa.COOKIE, 'forged')
    assert forged.post('/mfa/challenge', data={'code':codes[0]}).status_code == 400
    token = security.decrypt(login.cookies.get(mfa.COOKIE))
    with monkeypatch.context() as clock:
        future=utcnow()+timedelta(minutes=6)
        clock.setattr(mfa,'utcnow',lambda:future)
        assert login.post('/mfa/challenge', data={'code':codes[0]}).status_code == 400
    login = pending_login(email)
    with SessionLocal() as db:
        db.get(User, uid).auth_version += 1; db.commit()
    assert login.post('/mfa/challenge', data={'code':codes[0]}).status_code == 400


def test_concurrent_recovery_code_can_authenticate_only_one_challenge():
    _, uid, email, _, codes = enrolled()
    first, second = pending_login(email), pending_login(email)
    def submit(client):
        return client.post('/mfa/challenge', data={'code':codes[0]}, follow_redirects=False).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, [first,second]))
    assert results.count(303) == 1
    with SessionLocal() as db:
        assert len(json.loads(db.get(MfaSettings, uid).recovery_hashes_json)) == 9


def test_disable_requires_factor_and_erasure_removes_mfa_secrets():
    owner, uid, email, secret, codes = enrolled()
    assert 'Check your password' in owner.post('/mfa/disable', data={'password':'wrong','code':codes[0]}).text
    with SessionLocal() as db:
        assert db.get(MfaSettings, uid).enabled
    response = owner.post('/mfa/disable', data={'password':'old-password-123','code':codes[0]}, follow_redirects=False)
    assert response.status_code == 303
    with SessionLocal() as db:
        row = db.get(MfaSettings, uid)
        assert not row.enabled and row.encrypted_secret == '' and row.recovery_hashes_json == '[]'
        erase_local_account(db, uid, 'synthetic-mfa-erasure', writes_paused=True)
        assert db.get(MfaSettings, uid) is None


def test_factor_rate_limit(monkeypatch):
    _, _, email, _, codes = enrolled()
    login = pending_login(email)
    monkeypatch.setattr(mfa, 'allowed_request', lambda *a:False)
    assert login.post('/mfa/challenge', data={'code':codes[0]}).status_code == 429
    assert not login.cookies.get('nova_session')


def test_setup_pending_expiry_and_account_boundary():
    owner, uid, _, _ = account()
    other, _, _, _ = account()
    owner.post('/mfa/setup', data={'password':'old-password-123'})
    with SessionLocal() as db:
        row = db.get(MfaSettings, uid)
        secret = security.decrypt(row.encrypted_secret)
        row.setup_expires_at = utcnow()-timedelta(seconds=1); db.commit()
    code = mfa.totp(secret, int(time.time())//30)
    assert owner.post('/mfa/enable', data={'code':code}).status_code == 400
    assert other.post('/mfa/enable', data={'code':code}).status_code == 400
    with SessionLocal() as db:
        assert not db.get(MfaSettings, uid).enabled


def test_password_reset_keeps_second_factor_required():
    _, uid, email, _, codes = enrolled()
    from nova.db import RecoveryToken
    with SessionLocal() as db:
        user = db.get(User, uid)
        db.add(RecoveryToken(token_hash=security.hash_api_key('synthetic-mfa-reset'), user_id=uid,
            auth_version=user.auth_version, expires_at=utcnow()+timedelta(minutes=5)))
        db.commit()
    client = TestClient(app)
    response = client.post('/reset-password', data={'token':'synthetic-mfa-reset','password':'replacement-synthetic-password','confirmation':'replacement-synthetic-password'}, follow_redirects=False)
    assert response.status_code == 303
    response = client.post('/login', data={'email':email,'password':'replacement-synthetic-password'}, follow_redirects=False)
    assert response.headers['location'] == '/mfa/challenge'
    assert not client.cookies.get('nova_session')
    assert client.post('/mfa/challenge', data={'code':codes[0]}, follow_redirects=False).status_code == 303


def test_concurrent_same_challenge_is_consumed_once():
    _, _, email, _, codes = enrolled()
    original = pending_login(email)
    challenge_cookie = original.cookies.get(mfa.COOKIE)
    clients = [TestClient(app), TestClient(app)]
    for client in clients:
        client.cookies.set(mfa.COOKIE, challenge_cookie)
    def submit(client):
        return client.post('/mfa/challenge', data={'code':codes[0]}, follow_redirects=False).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, clients))
    assert results.count(303) == 1


def test_enabled_mfa_and_pending_challenge_erased_without_affecting_other_account():
    _, uid, email, secret, _ = enrolled()
    pending_login(email)
    _, other, _, _ = account()
    with SessionLocal() as db:
        db.add(MfaSettings(user_id=other, enabled=True, encrypted_secret=security.encrypt('synthetic-other-secret')))
        db.commit()
        erase_local_account(db, uid, 'synthetic-enabled-mfa-erasure', writes_paused=True)
        assert db.get(MfaSettings, uid) is None
        from sqlalchemy import select
        assert db.scalar(select(MfaChallenge).where(MfaChallenge.user_id == uid)) is None
        assert db.get(MfaSettings, other).enabled


def test_secret_pages_are_not_cached_and_cross_site_setup_is_rejected():
    client, uid, _, _ = account()
    response = client.post('/mfa/setup', data={'password':'old-password-123'}, headers={'origin':'https://attacker.invalid'})
    assert response.status_code == 403
    with SessionLocal() as db:
        assert db.get(MfaSettings, uid) is None
    response = client.post('/mfa/setup', data={'password':'old-password-123'})
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['referrer-policy'] == 'no-referrer'


def test_apple_sign_in_requires_enabled_second_factor(monkeypatch):
    from test_apple_account_regressions import callback
    _, _, email, _, _ = enrolled()
    response = callback(monkeypatch, email)
    assert response.headers['location'] == '/mfa/challenge'
    assert not response.cookies.get('nova_session')


def test_password_login_cannot_bypass_concurrent_enrollment(monkeypatch):
    from nova import app as app_module
    _, uid, _, email = account()
    original = app_module.make_user_session
    def enroll_before_session(user_id, *, expected_auth_version=None):
        with SessionLocal() as db:
            db.get(User, user_id).auth_version += 1
            db.commit()
        return original(user_id, expected_auth_version=expected_auth_version)
    monkeypatch.setattr(app_module, 'make_user_session', enroll_before_session)
    response = TestClient(app).post('/login', data={'email':email,'password':'old-password-123'}, follow_redirects=False)
    assert 'sign-in+changed' in response.headers['location']
    assert not response.cookies.get('nova_session')


def test_additive_mfa_migration_is_repeatable_and_preserves_users():
    from sqlalchemy import create_engine, text
    from nova.migrations import run_mfa_migration
    from nova.db import Base
    engine = create_engine('sqlite://')
    User.__table__.create(engine)
    with engine.begin() as connection:
        connection.execute(User.__table__.insert().values(email='migration@example.test',password_hash='unchanged'))
        connection.execute(text('CREATE TABLE zova_schema_migrations (version VARCHAR(100) PRIMARY KEY, applied_at TIMESTAMP NOT NULL)'))
        before = connection.execute(text('SELECT * FROM nova_users')).all()
    for _ in range(2):
        run_mfa_migration(engine, (MfaSettings.__table__, MfaChallenge.__table__))
    with engine.connect() as connection:
        assert connection.execute(text('SELECT * FROM nova_users')).all() == before
        assert connection.execute(text('SELECT COUNT(*) FROM zova_mfa_settings')).scalar() == 0
        assert connection.execute(text('SELECT COUNT(*) FROM zova_schema_migrations')).scalar() == 1
    engine.dispose()
