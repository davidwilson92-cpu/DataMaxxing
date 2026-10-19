import json
import logging
import re
import secrets
from http.cookies import SimpleCookie
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from nova.app import app
from nova.db import Brand, DeletionRequest, MobileGrant, MobileHandoff, MobileSession, SessionLocal, User, utcnow
from nova.mobile_auth import challenge_for
from nova.security import hash_api_key, user_from_session
from test_account_integrity import account

CALLBACK = 'https://zova-social.com/mobile/callback'


def test_account_deletion_request_is_authenticated_idempotent_and_truthful():
    web, uid, _, _ = account()
    assert TestClient(app).post('/account/deletion', data={'confirmation': 'DELETE'}).status_code == 401
    assert web.get('/account/deletion').status_code == 200
    assert web.post('/account/deletion', data={'confirmation': 'other'}).status_code == 400
    response = web.post('/account/deletion', data={'confirmation': 'DELETE'}, follow_redirects=False)
    assert response.status_code == 303
    assert web.post('/account/deletion', data={'confirmation': 'DELETE'}, follow_redirects=False).headers['location'] == response.headers['location']
    page = web.get(response.headers['location'])
    assert 'Deletion request received' in page.text
    assert 'have not yet been deleted' in page.text
    assert 'Platform connection removed' not in page.text
    with SessionLocal() as db:
        row = db.get(DeletionRequest, response.headers['location'].rsplit('/', 1)[1])
        assert row.status == 'received'
        assert row.subject_hash == hash_api_key(str(uid))
        assert db.get(User, uid).active
    other, _, _, _ = account()
    assert other.post('/account/deletion', data={'confirmation': 'DELETE'}, follow_redirects=False).headers['location'] != response.headers['location']


@pytest.fixture(autouse=True)
def native_config(monkeypatch):
    monkeypatch.setenv('ZOVA_MOBILE_ENABLED', 'true')
    monkeypatch.setenv('ZOVA_IOS_REDIRECT_URI', CALLBACK)
    monkeypatch.setenv('ZOVA_IOS_APP_ID', '7B4W8RN6GX.com.zovasocial.app')
    monkeypatch.setenv('RATE_LIMIT_SCALE', '100')


def sign_in():
    web, uid, _, _ = account()
    verifier, state = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    response = web.get('/mobile/authorize', params={'client_id': 'zova-ios', 'redirect_uri': CALLBACK, 'code_challenge': challenge_for(verifier), 'state': state}, follow_redirects=False)
    assert response.status_code == 303, response.text
    page = web.get(response.headers['location'])
    proof = re.search(r'name="proof" value="([a-f0-9]+)"', page.text)[1]
    confirmed = web.post(response.headers['location'], data={'proof': proof}, follow_redirects=False)
    values = parse_qs(urlsplit(confirmed.headers['location']).query)
    assert values['state'] == [state]
    exchange = {'client_id': 'zova-ios', 'redirect_uri': CALLBACK, 'code': values['code'][0], 'code_verifier': verifier}
    client = TestClient(app)
    response = client.post('/api/v1/auth/token', json=exchange)
    assert response.status_code == 200, response.text
    pair = response.json()
    client.headers['Authorization'] = 'Bearer ' + pair['access_token']
    return client, web, uid, pair, exchange


def handoff(client, destination='/studio', purpose='studio'):
    response = client.post('/api/v1/native-handoff', json={'destination': destination, 'purpose': purpose})
    assert response.status_code == 200, response.text
    return response.json()['ticket']


def shell(client, destination='/studio'):
    browser = TestClient(app)
    response = browser.post('/mobile/web-session', data={'ticket': handoff(client, destination)}, follow_redirects=False)
    assert response.status_code == 303, response.text
    return browser


def test_existing_browser_auth_stays_separate_and_native_is_gated(monkeypatch):
    native, web, uid, pair, _ = sign_in()
    assert web.get('/api/v1/native-profile').status_code == 401
    assert native.get('/api/drafts').status_code == 401
    assert native.get('/api/v1/native-profile').json()['id'] == uid
    monkeypatch.setenv('ZOVA_MOBILE_ENABLED', 'false')
    assert native.get('/api/v1/native-profile').status_code == 404
    assert web.get('/api/drafts').status_code == 200
    assert web.get('/api/v1/native-config').json()['enabled'] is False


def test_cookie_is_owned_revocable_and_does_not_expose_native_tokens():
    native, _, uid, pair, _ = sign_in()
    browser = shell(native)
    cookie = browser.cookies.get('nova_session')
    assert cookie.startswith('ios.')
    assert pair['access_token'] not in cookie and pair['refresh_token'] not in cookie
    assert user_from_session(cookie).id == uid
    response = browser.get('/studio')
    assert response.status_code == 200
    assert 'ios-shell.css' in response.text
    assert pair['access_token'] not in response.text
    assert native.post('/api/v1/auth/logout').status_code == 204
    assert browser.get('/api/drafts').status_code == 401


def test_web_signout_revokes_native_session_and_its_other_cookies():
    native, _, _, pair, _ = sign_in()
    browser, second = shell(native), shell(native)
    assert browser.post('/logout', follow_redirects=False).status_code == 303
    assert native.get('/api/v1/native-profile').status_code == 401
    assert second.get('/api/drafts').status_code == 401


def test_password_change_and_disabled_mobile_revoke_bound_cookie(monkeypatch):
    native, _, uid, _, _ = sign_in()
    browser = shell(native)
    with SessionLocal() as db:
        db.get(User, uid).auth_version += 1
        db.commit()
    assert browser.get('/api/drafts').status_code == 401
    native, _, _, _, _ = sign_in()
    browser = shell(native)
    monkeypatch.setenv('ZOVA_MOBILE_ENABLED', 'false')
    assert browser.get('/api/drafts').status_code == 401


def test_handoff_single_use_expiry_and_purpose():
    native, _, _, pair, _ = sign_in()
    ticket = handoff(native)
    browser = TestClient(app)
    response = browser.post('/mobile/web-session', data={'ticket': ticket}, follow_redirects=False)
    assert response.status_code == 303
    assert browser.post('/mobile/web-session', data={'ticket': ticket}).status_code == 401
    with SessionLocal() as db:
        row = db.get(MobileHandoff, hash_api_key(ticket))
        assert row.used and row.token_hash != ticket
    ticket = handoff(native)
    with SessionLocal() as db:
        db.get(MobileHandoff, hash_api_key(ticket)).expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert browser.post('/mobile/web-session', data={'ticket': ticket}).status_code == 401
    ticket = handoff(native, '/account', 'browser')
    assert browser.post('/mobile/web-session', data={'ticket': ticket}).status_code == 401


@pytest.mark.parametrize('target', ['https://evil.test/', '//evil.test/', '/\\evil.test', '/mobile/authorize/anything', '/oauth/tiktok/start', '/studio?workspace=1&workspace=2', '/studio?workspace=-1', '/studio?draft=9223372036854775808', '/account?draft=1', '/studio?next=https://evil.test', '/studio#unknown'])
def test_handoff_cannot_redirect_or_expand_scope(target):
    native, *_ = sign_in()
    assert native.post('/api/v1/native-handoff', json={'destination': target}).status_code == 400


def test_browser_transfer_requires_explicit_cookie_bound_confirmation():
    native, _, uid, _, _ = sign_in()
    other, other_id, _, _ = account()
    ticket = handoff(native, '/connect/tiktok?workspace=0', 'browser')
    path = '/mobile/browser/' + ticket
    page = other.get(path)
    assert page.status_code == 200 and 'Continue to your account' in page.text
    assert user_from_session(other.cookies.get('nova_session')).id == other_id
    proof = re.search(r'name="proof" value="([a-f0-9]+)"', page.text)[1]
    stranger = TestClient(app)
    assert stranger.post(path, data={'proof': proof}).status_code == 403
    assert other.post(path, data={'proof': proof}, headers={'origin': 'https://evil.test'}).status_code == 403
    accepted = other.post(path, data={'proof': proof}, follow_redirects=False)
    assert accepted.status_code == 303 and accepted.headers['location'] == '/connect/tiktok?workspace=0'
    issued = SimpleCookie(accepted.headers.get_list('set-cookie')[0])['nova_session'].value
    assert user_from_session(issued).id == uid
    assert other.post(path, data={'proof': proof}).status_code in {401, 403}


def test_revoked_session_cannot_finish_a_previously_minted_ticket():
    native, _, _, _, _ = sign_in()
    ticket = handoff(native)
    native.post('/api/v1/auth/logout')
    assert TestClient(app).post('/mobile/web-session', data={'ticket': ticket}).status_code == 401


def test_native_cookie_does_not_authorize_foreign_workspace():
    native, _, _, _, _ = sign_in()
    other, uid, _, _ = account()
    with SessionLocal() as db:
        brand = Brand(user_id=uid, name='Other brand')
        db.add(brand); db.commit(); bid = brand.id
    browser = shell(native, f'/studio?workspace={bid}')
    assert browser.get(f'/studio?workspace={bid}').status_code == 404
    assert browser.get(f'/api/native-connections?workspace={bid}').status_code == 404


def test_native_billing_is_disabled_and_web_billing_unchanged():
    native, web, *_ = sign_in()
    browser = shell(native)
    assert browser.post('/billing/checkout', data={}).status_code == 403
    assert browser.get('/billing/portal').status_code == 403
    assert web.get('/subscribe').status_code == 200


def test_pkce_replay_wrong_callback_and_rotation_replay():
    native, _, _, pair, exchange = sign_in()
    assert TestClient(app).post('/api/v1/auth/token', json=exchange).status_code == 401
    assert TestClient(app).post('/api/v1/auth/token', json={**exchange, 'redirect_uri': 'https://evil.test/mobile/callback'}).status_code == 400
    assert native.post('/api/v1/auth/refresh', json={'refresh_token': pair['refresh_token']}).status_code == 200
    assert native.get('/api/v1/native-profile').status_code == 401
    assert native.post('/api/v1/auth/refresh', json={'refresh_token': pair['refresh_token']}).status_code == 401


def test_parallel_ticket_consumption_only_creates_one_cookie():
    native, *_ = sign_in()
    ticket = handoff(native)
    def consume(_):
        with TestClient(app) as browser:
            return browser.post('/mobile/web-session', data={'ticket': ticket}, follow_redirects=False).status_code
    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = list(pool.map(consume, range(4)))
    assert outcomes.count(303) == 1 and outcomes.count(401) == 3


def test_signup_or_apple_return_resumes_explicit_native_consent():
    web, *_ = account()
    verifier, state = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    response = web.get('/mobile/authorize', params={'client_id': 'zova-ios', 'redirect_uri': CALLBACK, 'code_challenge': challenge_for(verifier), 'state': state}, follow_redirects=False)
    grant_path = response.headers['location']
    grant_id = grant_path.rsplit('/', 1)[1]
    # Secure pending cookie is set on production HTTPS; simulate its presence here.
    web.cookies.set('zova_mobile_grant', grant_id)
    returned = web.get('/onboarding/socials', follow_redirects=False)
    assert returned.status_code == 303 and returned.headers['location'] == grant_path
    assert 'Continue to the app' in web.get(grant_path).text


def test_association_scope_config_and_no_wildcards(monkeypatch):
    client = TestClient(app)
    response = client.get('/.well-known/apple-app-site-association')
    assert response.status_code == 200
    data = response.json()
    assert data['applinks']['details'][0]['components'][0]['/'] == '/mobile/callback'
    assert '*' not in json.dumps(data)
    monkeypatch.setenv('ZOVA_IOS_APP_ID', '*')
    assert client.get('/.well-known/apple-app-site-association').status_code == 404


def test_access_logs_strip_query_and_handoff_secret():
    from nova.access_logging import RedactAccess
    secret = secrets.token_urlsafe(48)
    record = logging.LogRecord('uvicorn.access', logging.INFO, '', 0, '%s - "%s %s HTTP/%s" %d', ('client', 'GET', '/mobile/browser/' + secret + '?code=secret', '1.1', 200), None)
    RedactAccess().filter(record)
    assert secret not in record.getMessage() and 'code=secret' not in record.getMessage()
    assert '[redacted]' in record.getMessage()


def test_mutating_native_route_rejects_cross_site_origin():
    native, *_ = sign_in()
    assert native.post('/api/v1/native-handoff', json={'destination': '/studio'}, headers={'origin': 'https://evil.test'}).status_code == 403
