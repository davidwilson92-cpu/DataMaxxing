import secrets
from datetime import timedelta

from fastapi.testclient import TestClient

from nova.app import app
from nova import recovery


def test_native_apple_creates_once_and_requires_terms(monkeypatch):
    from datetime import datetime, timezone
    from types import SimpleNamespace
    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa

    monkeypatch.setenv('ZOVA_MOBILE_ENABLED', 'true')
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(jwt.PyJWKClient, 'get_signing_key_from_jwt',
                        lambda self, token: SimpleNamespace(key=key.public_key()))
    client = TestClient(app)
    nonce = client.post('/api/v1/auth/apple/challenge').json()['nonce']
    now = datetime.now(timezone.utc)
    subject = secrets.token_hex(16)
    claims = dict(sub=subject, email=subject+'@example.test', email_verified=True, nonce=nonce,
                  iss='https://appleid.apple.com', aud='com.zovasocial.app', iat=now, exp=now+timedelta(minutes=5))
    def sign_in(**overrides):
        token = jwt.encode({**claims, **overrides}, key, algorithm='RS256')
        return client.post('/api/v1/auth/apple', json=dict(nonce=nonce, token=token, accept_terms=True))
    assert sign_in(aud='other.app').status_code == 401
    assert sign_in(nonce='different').status_code == 401
    token = jwt.encode(claims, key, algorithm='RS256')
    assert client.post('/api/v1/auth/apple', json=dict(nonce=nonce, token=token)).status_code == 409
    assert sign_in().status_code == 200
    assert sign_in().status_code == 401
    nonce = client.post('/api/v1/auth/apple/challenge').json()['nonce']
    assert sign_in(nonce=nonce).status_code == 200


def test_native_registration_reset_and_reentry(monkeypatch):
    monkeypatch.setenv('ZOVA_MOBILE_ENABLED', 'true')
    monkeypatch.setattr(recovery, 'recovery_ready', lambda: True)
    mail = []
    monkeypatch.setattr(recovery, 'smtp_message', lambda address, subject, body: mail.append((address, subject, body)))
    client = TestClient(app, follow_redirects=False)
    headers = {'accept': 'application/json'}
    email = secrets.token_hex(8) + '@example.test'
    original = 'original-password-123'
    updated = 'updated-password-456'
    form = dict(email=email, name='Native Test', password=original, password_confirmation=original)
    assert client.post('/signup', data=form, headers=headers).status_code == 400
    assert client.post('/signup', data={**form, 'accept_terms': 'yes'}, headers=headers).status_code == 201
    login = client.post('/api/v1/auth/password', json=dict(email=email, password=original))
    assert login.status_code == 200
    assert mail[0][:2] == (email, 'Verify your Zova email')
    verification = mail[0][2].split('#token=')[1].strip()
    assert client.post('/verify-email', data={'token': verification}, headers=headers).status_code == 401
    bearer = {'Authorization': 'Bearer '+login.json()['access_token']}
    ticket = client.post('/api/v1/native-handoff', headers=bearer, json={'destination':'/studio','purpose':'studio'})
    assert ticket.status_code == 200
    cookie = client.post('/api/v1/native-web-session', headers=bearer, json={'ticket':ticket.json()['ticket']})
    assert cookie.status_code == 200
    verified = client.post('/verify-email', headers=headers, cookies={'nova_session':cookie.cookies['nova_session']},
                           data={'token':verification})
    assert verified.json() == {'verified': True}
    assert client.post('/forgot-password', data={'email':email}, headers=headers).status_code == 202
    assert mail[-1][:2] == (email, 'Reset your Zova password')
    token = mail[-1][2].split('#token=')[1].split()[0]
    reset_form = dict(token=token, password=updated, confirmation=updated)
    assert client.post('/reset-password', data=reset_form, headers=headers).json() == {'reset': True}
    assert client.post('/reset-password', data=reset_form, headers=headers).status_code == 400
    assert client.post('/api/v1/auth/password', json=dict(email=email, password=original)).status_code == 401
    assert client.post('/api/v1/auth/password', json=dict(email=email, password=updated)).status_code == 200
