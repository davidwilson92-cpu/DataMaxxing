import base64
import hashlib
import secrets
import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import select
from nova import app as module
from nova.db import SessionLocal, User
from test_apple_browser_binding import start


@pytest.fixture(scope='module')
def signing_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def identity_claims(nonce, **changes):
    now = int(time.time())
    return {'iss': 'https://appleid.apple.com', 'aud': 'synthetic-client',
            'iat': now, 'exp': now+300, 'sub': secrets.token_hex(16), 'nonce': nonce,
            'email': secrets.token_hex(8)+'@example.test', 'email_verified': True,
            'c_hash': base64.urlsafe_b64encode(hashlib.sha256(b'synthetic').digest()[:16]).rstrip(b'=').decode(),
            **changes}


def setup_exchange(monkeypatch, signing_key, front_changes=None, back_changes=None, missing=None, bad_signature=False):
    client, _, state, nonce = start(monkeypatch)
    claims = identity_claims(nonce)
    front = {**claims, **(front_changes or {})}
    if missing: front.pop(missing)
    back = {**claims, **(back_changes or {})}
    back.pop('c_hash', None)
    token = jwt.encode(front, rsa.generate_private_key(public_exponent=65537,key_size=2048) if bad_signature else signing_key,
                       algorithm='RS256', headers={'kid':'synthetic'})
    back_token = jwt.encode(back, signing_key, algorithm='RS256', headers={'kid':'synthetic'})
    exchanges = []
    monkeypatch.setattr(module, 'apple_client_secret', lambda: 'synthetic-secret')
    monkeypatch.setattr(module.jwt, 'PyJWKClient', lambda *a, **k: SimpleNamespace(
        get_signing_key_from_jwt=lambda *a: SimpleNamespace(key=signing_key.public_key())))
    def exchange(*a, **k):
        exchanges.append(True)
        return SimpleNamespace(status_code=200, json=lambda: {'id_token':back_token})
    monkeypatch.setattr(module.httpx, 'post', exchange)
    def finish():
        return client.post('/auth/apple/callback', data={
            'code':'synthetic','id_token':token,'state':state}, follow_redirects=False)
    return finish, claims, exchanges


@pytest.mark.parametrize('missing', ['exp','iat','sub','nonce','iss','aud','c_hash'])
def test_missing_required_front_claim_cannot_create_account(monkeypatch, signing_key, missing):
    finish, claims, exchanges = setup_exchange(monkeypatch, signing_key, missing=missing)
    response = finish()
    assert response.status_code == 400 and not response.cookies.get('nova_session')
    assert exchanges == []
    with SessionLocal() as db:
        assert db.scalar(select(User).where(User.email==claims['email'])) is None


@pytest.mark.parametrize('changes', [
    {'c_hash':'different-code'}, {'iss':'https://other.example'}, {'aud':'other-client'},
    {'exp':1}, {'iat':4102444800}, {'nonce':'other-nonce'}, {'sub':''},
    {'azp':'other-client'}, {'aud':['synthetic-client','other-client']},
    {'email_verified':[]}, {'email':123}, {'exp':True}, {'sub':123},
])
def test_invalid_front_identity_is_rejected_before_exchange(monkeypatch, signing_key, changes):
    finish, _, exchanges = setup_exchange(monkeypatch, signing_key, front_changes=changes)
    response = finish()
    assert response.status_code == 400 and not response.cookies.get('nova_session')
    assert exchanges == []


@pytest.mark.parametrize('changes', [{'sub':'another-person'}, {'nonce':'another-attempt'}, {'exp':1}])
def test_exchanged_token_must_validate_and_match_front_identity(monkeypatch, signing_key, changes):
    finish, claims, exchanges = setup_exchange(monkeypatch, signing_key, back_changes=changes)
    response = finish()
    assert response.status_code == 400 and not response.cookies.get('nova_session')
    assert exchanges == [True]
    with SessionLocal() as db:
        assert db.scalar(select(User).where(User.email==claims['email'])) is None


def test_wrong_signature_is_rejected_without_exchange(monkeypatch, signing_key):
    finish, _, exchanges = setup_exchange(monkeypatch, signing_key, bad_signature=True)
    response = finish()
    assert response.status_code == 400 and not response.cookies.get('nova_session')
    assert exchanges == []


@pytest.mark.parametrize('failure', ['timeout','json','missing_token','provider_error','keys'])
def test_provider_failure_is_sanitized_and_consumed_state_is_not_retried(monkeypatch, signing_key, failure, caplog):
    import httpx
    finish, claims, _ = setup_exchange(monkeypatch, signing_key)
    calls=[]
    def fail(*a, **k):
        calls.append(True)
        if failure=='timeout':raise httpx.TimeoutException('Private provider diagnostic')
        if failure=='provider_error':return SimpleNamespace(status_code=400)
        def body():
            if failure=='json':raise ValueError('Private provider diagnostic')
            return {}
        return SimpleNamespace(status_code=200,json=body)
    monkeypatch.setattr(module.httpx,'post',fail)
    if failure=='keys':
        def unavailable(*a):raise jwt.PyJWKClientConnectionError('Private provider diagnostic')
        monkeypatch.setattr(module.jwt,'PyJWKClient',lambda *a,**k:SimpleNamespace(get_signing_key_from_jwt=unavailable))
    response=finish()
    assert response.status_code == (503 if failure in {'timeout','keys'} else 502)
    assert 'Private provider diagnostic' not in response.text+caplog.text
    assert not response.cookies.get('nova_session')
    assert finish().status_code==400
    assert calls==([] if failure=='keys' else [True])
    with SessionLocal() as db:
        assert db.scalar(select(User).where(User.email==claims['email'])) is None


def test_valid_signed_tokens_create_account_and_cannot_replay(monkeypatch, signing_key):
    finish, _, exchanges = setup_exchange(monkeypatch, signing_key)
    response = finish()
    assert response.status_code == 303 and response.cookies.get('nova_session')
    assert finish().status_code == 400
    assert exchanges == [True]
