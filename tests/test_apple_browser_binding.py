import secrets
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from nova import app as module
from nova.db import SessionLocal, AuthState, User
from nova.security import hash_api_key


def start(monkeypatch, client=None):
    monkeypatch.setattr(module, 'apple_configured', lambda: True)
    monkeypatch.setenv('APPLE_CLIENT_ID', 'synthetic-client')
    client = client or TestClient(module.app, base_url='https://testserver')
    response = client.get('/auth/apple/start', follow_redirects=False)
    params = parse_qs(urlsplit(response.headers['location']).query)
    return client, response, params['state'][0], params['nonce'][0]


def provider(monkeypatch, nonce):
    email = secrets.token_hex(8) + '@example.test'
    exchanges = []
    monkeypatch.setattr(module, 'apple_client_secret', lambda: 'synthetic-secret')
    def exchange(*args, **kwargs):
        exchanges.append(True)
        return SimpleNamespace(status_code=200)
    monkeypatch.setattr(module.httpx, 'post', exchange)
    monkeypatch.setattr(module.jwt, 'PyJWKClient', lambda *a: SimpleNamespace(
        get_signing_key_from_jwt=lambda *a: SimpleNamespace(key='synthetic-key')))
    monkeypatch.setattr(module.jwt, 'decode', lambda *a, **k: {
        'nonce': nonce, 'sub': secrets.token_hex(16), 'email': email, 'email_verified': True})
    return email, exchanges


def finish(client, state):
    return client.post('/auth/apple/callback', data={
        'code': 'synthetic', 'id_token': 'synthetic', 'state': state}, follow_redirects=False)


@pytest.mark.parametrize('cookie', [None, 'different-browser-state', 'tampered'])
def test_callback_without_original_browser_cannot_claim_state_or_sign_in(monkeypatch, cookie):
    original, _, state, nonce = start(monkeypatch)
    email, exchanges = provider(monkeypatch, nonce)
    foreign = TestClient(module.app, base_url='https://testserver')
    from test_account_integrity import account
    from nova.security import user_from_session
    _, victim_id, victim_session, _ = account()
    foreign.cookies.set('nova_session', victim_session)
    if cookie:
        foreign.cookies.set('__Host-zova_apple_state', cookie)
    rejected = finish(foreign, state)
    assert rejected.status_code == 400
    assert exchanges == [] and not rejected.cookies.get('nova_session')
    assert user_from_session(foreign.cookies.get('nova_session')).id == victim_id
    with SessionLocal() as db:
        assert not db.scalar(select(AuthState).where(AuthState.state_hash == hash_api_key(state))).used
        assert db.scalar(select(User).where(User.email == email)) is None
    accepted = finish(original, state)
    assert accepted.status_code == 303 and accepted.cookies.get('nova_session')
    assert exchanges == [True]


def test_start_sets_host_only_secure_cross_site_post_cookie_and_success_clears_it(monkeypatch):
    client, response, state, nonce = start(monkeypatch)
    cookie = response.headers['set-cookie'].lower()
    assert '__host-zova_apple_state=' in cookie
    assert 'secure' in cookie and 'httponly' in cookie
    assert 'samesite=none' in cookie and 'path=/' in cookie and 'max-age=600' in cookie
    assert 'domain=' not in cookie
    provider(monkeypatch, nonce)
    result = finish(client, state)
    assert result.cookies.get('nova_session')
    assert '__Host-zova_apple_state' not in client.cookies
    assert finish(client, state).status_code == 400


def test_new_attempt_replaces_old_browser_binding_without_consuming_old_state(monkeypatch):
    client, _, old, _ = start(monkeypatch)
    client, _, latest, nonce = start(monkeypatch, client)
    _, exchanges = provider(monkeypatch, nonce)
    assert finish(client, old).status_code == 400
    assert exchanges == []
    assert finish(client, latest).status_code == 303


def test_expired_state_is_rejected_even_with_original_browser_cookie(monkeypatch):
    from datetime import timedelta
    from nova.db import utcnow
    client, _, state, nonce = start(monkeypatch)
    _, exchanges = provider(monkeypatch, nonce)
    with SessionLocal() as db:
        db.scalar(select(AuthState).where(AuthState.state_hash == hash_api_key(state))).created_at = utcnow()-timedelta(minutes=11)
        db.commit()
    assert finish(client, state).status_code == 400
    assert exchanges == []


def test_bound_apple_signin_still_requires_mfa_and_clears_binding(monkeypatch):
    from nova.db import MfaSettings
    from nova.security import encrypt
    client, _, state, nonce = start(monkeypatch)
    email, _ = provider(monkeypatch, nonce)
    with SessionLocal() as db:
        user = User(email=email, password_hash='synthetic-unused')
        db.add(user); db.flush()
        db.add(MfaSettings(user_id=user.id, enabled=True, encrypted_secret=encrypt('synthetic-secret')))
        db.commit()
    response = finish(client, state)
    assert response.headers['location'] == '/mfa/challenge'
    assert not response.cookies.get('nova_session')
    assert '__Host-zova_apple_state' not in client.cookies
