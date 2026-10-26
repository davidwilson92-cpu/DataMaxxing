"""Credential work-factor upgrades and password-reset/sign-in interleavings."""
import hashlib

from sqlalchemy import update
from nova import security
from nova.db import SessionLocal, User
from test_account_integrity import account


def legacy_hash(password):
    salt = b'legacy-test-salt'
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f'scrypt${salt.hex()}${digest.hex()}'


def test_legacy_login_upgrades_hash_without_revoking_valid_sessions():
    client, uid, old_token, email = account()
    old_hash = legacy_hash('old-password-123')
    with SessionLocal() as db:
        db.get(User, uid).password_hash = old_hash
        db.commit()
    assert security.verify_password('old-password-123', old_hash)
    response = client.post('/login', data={'email': email, 'password': 'old-password-123'}, follow_redirects=False)
    assert response.headers['location'] == '/studio'
    with SessionLocal() as db:
        row = db.get(User, uid)
        assert row.password_hash.startswith('scrypt-v2$')
        assert security.verify_password('old-password-123', row.password_hash)
        assert not security.verify_password('wrong', row.password_hash)
        assert row.auth_version == 0
    assert security.user_from_session(old_token)
    assert security.user_from_session(response.cookies['nova_session'])


def reset_credentials(uid):
    with SessionLocal() as db:
        db.execute(update(User).where(User.id == uid).values(
            password_hash=security.hash_password('replacement-password-123'), auth_version=User.auth_version + 1))
        db.commit()


def test_reset_after_password_check_prevents_stale_login(monkeypatch):
    import nova.app as module
    client, uid, _, email = account()
    original = module.verify_password
    def racing_check(password, hashed):
        accepted = original(password, hashed)
        reset_credentials(uid)
        return accepted
    monkeypatch.setattr(module, 'verify_password', racing_check)
    result = client.post('/login', data={'email': email, 'password': 'old-password-123'}, follow_redirects=False)
    assert result.status_code == 303 and result.headers['location'].startswith('/login?')
    assert 'nova_session' not in result.cookies


def test_reset_before_cookie_issue_cannot_adopt_new_auth_version(monkeypatch):
    import nova.app as module
    client, uid, _, email = account()
    original = module.make_user_session
    def racing_issue(user_id, expected_auth_version=None):
        reset_credentials(uid)
        return original(user_id, expected_auth_version=expected_auth_version)
    monkeypatch.setattr(module, 'make_user_session', racing_issue)
    result = client.post('/login', data={'email': email, 'password': 'old-password-123'}, follow_redirects=False)
    assert result.status_code == 401
    assert 'nova_session' not in result.cookies


def test_password_change_cannot_overwrite_a_concurrent_reset(monkeypatch):
    import nova.app as module
    client, uid, *_ = account()
    original = module.verify_password
    def racing_check(password, hashed):
        accepted = original(password, hashed)
        reset_credentials(uid)
        return accepted
    monkeypatch.setattr(module, 'verify_password', racing_check)
    result = client.post('/account/password', data={
        'current_password': 'old-password-123', 'new_password': 'competing-password-123',
        'new_password_confirmation': 'competing-password-123'}, follow_redirects=False)
    assert result.status_code == 409
    assert 'nova_session' not in result.cookies
    with SessionLocal() as db:
        assert security.verify_password('replacement-password-123', db.get(User, uid).password_hash)


def test_new_hash_uses_bounded_memory_profile_and_rejects_unknown_formats(monkeypatch):
    original = security.hashlib.scrypt
    observed = []
    def record(*args, **kwargs):
        observed.append((kwargs['n'], kwargs['r'], kwargs['p']))
        return original(*args, **kwargs)
    monkeypatch.setattr(security.hashlib, 'scrypt', record)
    encoded = security.hash_password('unicode-password-\U0001f680')
    assert security.verify_password('unicode-password-\U0001f680', encoded)
    assert observed == [(2**14, 8, 5), (2**14, 8, 5)]
    assert not security.verify_password('x', encoded.replace('scrypt-v2', 'scrypt-v999'))
