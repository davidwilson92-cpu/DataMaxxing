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
        assert row.subject_hash == hash_api_key(f'account:{uid}')
        assert db.get(User, uid).active
    other, _, _, _ = account()
    assert other.post('/account/deletion', data={'confirmation': 'DELETE'}, follow_redirects=False).headers['location'] != response.headers['location']
    from nova.data_lifecycle import erase_local_account
    with SessionLocal() as db:
        erase_local_account(db, uid, 'synthetic-ios-deletion-case', writes_paused=True)
    finished = TestClient(app).get(response.headers['location'])
    assert 'Active account data erased' in finished.text
    assert 'awaiting processing' not in finished.text


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


def test_new_signin_cleans_expired_native_authority_without_touching_live_work():
    first, _, uid, pair, _ = sign_in()
    ticket = handoff(first)
    with SessionLocal() as db:
        db.get(MobileSession, pair['session_id']).expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    current, browser, current_uid, current_pair, _ = sign_in()
    assert current_uid != uid
    with SessionLocal() as db:
        assert db.get(MobileSession, pair['session_id']) is None
        assert db.get(MobileHandoff, hash_api_key(ticket)) is None
        assert db.get(User, uid).active
        assert db.get(MobileSession, current_pair['session_id']) is not None
    assert current.get('/api/v1/native-profile').status_code == 200
    assert browser.get('/api/drafts').status_code == 200


def test_signin_cancel_is_bound_expires_grant_and_does_not_loop_to_consent():
    web, uid, _, _ = account()
    verifier, state = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    response = web.get('/mobile/authorize', params={'client_id': 'zova-ios', 'redirect_uri': CALLBACK, 'code_challenge': challenge_for(verifier), 'state': state}, follow_redirects=False)
    target = response.headers['location']
    page = web.get(target)
    assert 'Cancel sign-in' in page.text
    proof = re.search(r'name="proof" value="([a-f0-9]+)"', page.text)[1]
    assert web.post(target, data={'proof': 'wrong', 'decision': 'cancel'}).status_code == 403
    cancelled = web.post(target, data={'proof': proof, 'decision': 'cancel'}, follow_redirects=False)
    assert cancelled.status_code == 303
    assert parse_qs(urlsplit(cancelled.headers['location']).query) == {'error': ['access_denied'], 'state': [state]}
    assert 'zova_mobile_grant=' in cancelled.headers['set-cookie'] and 'Max-Age=0' in cancelled.headers['set-cookie']
    assert web.get('/studio', follow_redirects=False).status_code == 200
    assert web.post(target, data={'proof': proof}, follow_redirects=False).status_code == 409
    with SessionLocal() as db:
        assert db.scalar(select(MobileSession).where(MobileSession.user_id == uid)) is None


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
    assert page.status_code == 200 and 'Connect TikTok' in page.text
    assert user_from_session(other.cookies.get('nova_session')).id == other_id
    proof = re.search(r'name="proof" value="([a-f0-9]+)"', page.text)[1]
    stranger = TestClient(app)
    assert stranger.post(path, data={'proof': proof}).status_code == 403
    assert other.post(path, data={'proof': proof}, headers={'origin': 'https://evil.test'}).status_code == 403
    accepted = other.post(path, data={'proof': proof}, follow_redirects=False)
    assert accepted.status_code == 303 and accepted.headers['location'] == '/connect/tiktok?workspace=0'
    issued = SimpleCookie(accepted.headers.get_list('set-cookie')[0])['nova_session'].value
    assert user_from_session(issued).id == uid
    resumed = other.post(path, data={'proof': proof}, follow_redirects=False)
    assert resumed.status_code == 303
    assert resumed.headers['location'] == '/connect/tiktok?workspace=0'
    assert 'set-cookie' not in resumed.headers


def test_browser_back_after_confirming_resumes_only_the_same_active_device_session():
    native, _, uid, pair, _ = sign_in()
    browser = TestClient(app)
    ticket = handoff(native, '/connect/instagram?workspace=0', 'browser')
    path = '/mobile/browser/' + ticket
    prompt = browser.get(path)
    proof = re.search(r'name="proof" value="([a-f0-9]+)"', prompt.text)[1]
    accepted = browser.post(path, data={'proof': proof}, follow_redirects=False)
    assert accepted.status_code == 303
    # A back/refresh resubmits the old form after the handoff rotated its cookie.
    resumed = browser.post(path, data={'proof': proof}, follow_redirects=False)
    assert resumed.status_code == 303
    assert resumed.headers['location'] == '/connect/instagram?workspace=0'
    assert 'set-cookie' not in resumed.headers
    # An expired, already-used ticket can only navigate an already-authorised
    # cookie; it never grants a fresh session or restores revoked authority.
    with SessionLocal() as db:
        db.get(MobileHandoff, hash_api_key(ticket)).expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert browser.get(path, follow_redirects=False).status_code == 303
    stranger = TestClient(app)
    assert stranger.get(path).status_code == 401
    assert stranger.post(path, data={'proof': proof}).status_code in {401, 403}
    # Same user, different native session must not consume this recovery path.
    from nova.mobile_shell import session_cookie
    with SessionLocal() as db:
        source = db.get(MobileSession, pair['session_id'])
        separate = MobileSession(id=secrets.token_hex(24), user_id=uid, auth_version=source.auth_version,
                                 access_hash=secrets.token_hex(32), access_expires_at=source.access_expires_at,
                                 expires_at=source.expires_at)
        db.add(separate); db.commit()
        different_cookie = session_cookie(separate)
    stranger.cookies.set('nova_session', different_cookie)
    assert stranger.get(path).status_code == 401
    native.post('/api/v1/auth/logout')
    assert browser.get(path).status_code == 401


def test_changed_browser_cookie_gets_safe_recovery_without_consuming_unused_ticket():
    native, *_ = sign_in()
    browser, _, _, _ = account()
    ticket = handoff(native, '/connect/instagram', 'browser')
    path = '/mobile/browser/' + ticket
    proof = re.search(r'name="proof" value="([a-f0-9]+)"', browser.get(path).text)[1]
    browser.cookies.clear()
    rejected = browser.post(path, data={'proof': proof})
    assert rejected.status_code == 403
    assert rejected.headers['content-type'].startswith('text/html')
    assert 'Review your Zova account again' in rejected.text
    assert 'set-cookie' not in rejected.headers
    with SessionLocal() as db:
        assert not db.get(MobileHandoff, hash_api_key(ticket)).used


def test_wrong_account_can_cancel_without_switching_browser_identity_or_connecting():
    native, _, uid, _, _ = sign_in()
    other, other_id, cookie, email = account()
    native_email = native.get('/api/v1/native-profile').json()['email']
    path = '/mobile/browser/' + handoff(native, '/connect/instagram?workspace=0', 'browser')
    page = other.get(path)
    assert native_email in page.text and email not in page.text
    assert 'This isn’t my Zova account' in page.text
    proof = re.search(r'name="proof" value="([a-f0-9]+)"', page.text)[1]
    assert TestClient(app).post(path, data={'proof': proof, 'decision': 'cancel'}).status_code == 403
    cancelled = other.post(path, data={'proof': proof, 'decision': 'cancel'})
    assert cancelled.status_code == 200
    assert 'Switch your Zova account' in cancelled.text
    assert 'Sign out' in cancelled.text
    assert 'set-cookie' not in cancelled.headers
    assert user_from_session(other.cookies.get('nova_session')).id == other_id
    assert native.get('/api/v1/native-profile').json()['id'] == uid
    assert other.post(path, data={'proof': proof}).status_code == 401


def test_browser_cancel_cannot_consume_studio_ticket():
    from nova.mobile_shell import browser_proof
    native, *_ = sign_in()
    ticket = handoff(native)
    browser = TestClient(app)
    assert browser.post('/mobile/browser/' + ticket, data={
        'proof': browser_proof(ticket, ''), 'decision': 'cancel'
    }).status_code == 401
    assert browser.post('/mobile/web-session', data={'ticket': ticket}, follow_redirects=False).status_code == 303


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
    blocked = browser.get('/billing/portal')
    assert blocked.status_code == 403
    assert blocked.headers['x-content-type-options'] == 'nosniff'
    assert blocked.headers['x-frame-options'] == 'DENY'
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


def test_native_signup_returns_to_consent_without_redirecting_normal_web_work():
    web, *_ = account()
    verifier, state = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    response = web.get('/mobile/authorize', params={'client_id': 'zova-ios', 'redirect_uri': CALLBACK, 'code_challenge': challenge_for(verifier), 'state': state}, follow_redirects=False)
    grant_path = response.headers['location']
    grant_id = grant_path.rsplit('/', 1)[1]
    # Secure pending cookie is set on production HTTPS; simulate its presence here.
    web.cookies.set('zova_mobile_grant', grant_id)
    # Abandoning the system sign-in window must not take over ordinary web work.
    assert web.get('/studio', follow_redirects=False).status_code == 200
    from test_onboarding import signup_payload
    email = 'native-signup-' + secrets.token_hex(8) + '@example.com'
    returned = web.post('/signup', data=signup_payload(email), follow_redirects=False)
    assert returned.status_code == 303 and returned.headers['location'] == grant_path
    assert 'Continue to the app' in web.get(grant_path).text
    assert email in web.get(grant_path).text


def test_apple_native_resume_uses_single_use_state_without_cross_site_cookies(monkeypatch):
    import importlib
    from types import SimpleNamespace
    application = importlib.import_module('nova.app')
    web, uid, *_ = account()
    verifier = secrets.token_urlsafe(48)
    native_state = secrets.token_urlsafe(32)
    begun = web.get('/mobile/authorize', params={'client_id':'zova-ios', 'redirect_uri':CALLBACK, 'code_challenge':challenge_for(verifier), 'state':native_state}, follow_redirects=False)
    grant_path = begun.headers['location']
    web.cookies.set('zova_mobile_grant', grant_path.rsplit('/', 1)[1])
    for name in ('APPLE_CLIENT_ID','APPLE_TEAM_ID','APPLE_KEY_ID','APPLE_PRIVATE_KEY'):
        monkeypatch.setenv(name, 'synthetic-provider-setting')
    started = web.get('/auth/apple/start', follow_redirects=False)
    values = parse_qs(urlsplit(started.headers['location']).query)
    state = values['state'][0]
    assert state.endswith('.' + grant_path.rsplit('/', 1)[1])
    with SessionLocal() as db:
        email = db.get(User, uid).email
    monkeypatch.setattr(application, 'apple_client_secret', lambda: 'synthetic-client-proof')
    monkeypatch.setattr(application.httpx, 'post', lambda *a, **k: SimpleNamespace(status_code=200))
    monkeypatch.setattr(application.jwt, 'PyJWKClient', lambda *a: SimpleNamespace(get_signing_key_from_jwt=lambda *a: SimpleNamespace(key='synthetic-provider-key')))
    monkeypatch.setattr(application.jwt, 'decode', lambda *a, **k: {'sub':'synthetic-native-'+secrets.token_hex(8), 'email':email, 'email_verified':True, 'nonce':values['nonce'][0]})
    # Apple form_post does not send a SameSite=Lax pending-flow cookie.
    callback = TestClient(app)
    body = {'state':state, 'code':'synthetic-code', 'id_token':'synthetic-token'}
    assert callback.post('/auth/apple/callback', data={**body, 'state':state+'tampered'}, follow_redirects=False).status_code == 400
    response = callback.post('/auth/apple/callback', data=body, headers={'sec-fetch-site':'cross-site'}, follow_redirects=False)
    assert response.status_code == 303 and response.headers['location'] == grant_path
    page = callback.get(grant_path)
    assert email in page.text
    proof = re.search(r'name="proof" value="([a-f0-9]+)"', page.text)[1]
    approved = callback.post(grant_path, data={'proof':proof}, follow_redirects=False)
    native_code = parse_qs(urlsplit(approved.headers['location']).query)
    assert native_code['state'] == [native_state]
    native = TestClient(app)
    pair = native.post('/api/v1/auth/token', json={'client_id':'zova-ios', 'redirect_uri':CALLBACK, 'code':native_code['code'][0], 'code_verifier':verifier})
    assert pair.status_code == 200
    native.headers['Authorization'] = 'Bearer ' + pair.json()['access_token']
    assert native.get('/api/v1/native-profile').json()['id'] == uid
    assert shell(native).get('/studio').status_code == 200
    assert callback.post('/auth/apple/callback', data=body, follow_redirects=False).status_code == 400


def test_password_login_preserves_native_consent_destination():
    _, uid, _, email = account()
    web = TestClient(app)
    response = web.get('/mobile/authorize', params={'client_id':'zova-ios', 'redirect_uri':CALLBACK, 'code_challenge':challenge_for(secrets.token_urlsafe(48)), 'state':secrets.token_urlsafe(32)}, follow_redirects=False)
    target = response.headers['location']
    assert web.get(target, follow_redirects=False).headers['location'].startswith('/login?next=')
    signed_in = web.post('/login', data={'email':email, 'password':'old-password-123', 'next':target}, follow_redirects=False)
    assert signed_in.headers['location'] == target
    assert email in web.get(target).text
    assert web.get('/studio', follow_redirects=False).status_code == 200


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


def test_webkit_opaque_origin_handoff_requires_native_header_and_one_use_ticket():
    native, _, uid, *_ = sign_in()
    ticket = handoff(native)
    browser = TestClient(app)
    headers = {'origin': 'null', 'sec-fetch-site': 'cross-site'}
    denied = browser.post('/mobile/web-session', data={'ticket': ticket}, headers=headers)
    assert denied.status_code == 403
    assert denied.json()['detail'] == 'Open Zova directly and try again.'
    headers['x-zova-native-handoff'] = '1'
    accepted = browser.post('/mobile/web-session', data={'ticket': ticket}, headers=headers, follow_redirects=False)
    assert accepted.status_code == 303
    assert accepted.headers['location'] == '/studio'
    assert user_from_session(browser.cookies.get('nova_session')).id == uid
    assert browser.get('/studio').status_code == 200
    assert browser.post('/mobile/web-session', data={'ticket': ticket}, headers=headers).status_code == 401


@pytest.mark.parametrize('origin', ['https://evil.test', 'https://zova-social.com.evil.test'])
def test_native_handoff_header_does_not_allow_untrusted_origins(origin):
    native, *_ = sign_in()
    ticket = handoff(native)
    browser = TestClient(app)
    headers = {'origin': origin, 'sec-fetch-site': 'cross-site', 'x-zova-native-handoff': '1'}
    assert browser.post('/mobile/web-session', data={'ticket': ticket}, headers=headers).status_code == 403
    # Rejection must not consume the ticket or establish an account session.
    assert not browser.cookies.get('nova_session')
    assert browser.post('/mobile/web-session', data={'ticket': ticket}, headers={'origin':'null','x-zova-native-handoff':'1'}, follow_redirects=False).status_code == 303


def test_native_handoff_header_cannot_bypass_other_route_origin_protection():
    native, *_ = sign_in()
    headers = {'origin':'null','sec-fetch-site':'cross-site','x-zova-native-handoff':'1'}
    assert native.post('/api/v1/native-handoff', json={'destination':'/studio'}, headers=headers).status_code == 403
    assert TestClient(app).post('/mobile/web-session', data={'ticket':'x'*64}, headers=headers).status_code == 401


def test_native_cookie_bootstrap_requires_bearer_and_owns_ticket():
    first, _, uid, _, _ = sign_in()
    other, *_ = sign_in()
    ticket = handoff(first)
    body = {'ticket':ticket}
    assert TestClient(app).post('/api/v1/native-web-session',json=body).status_code == 401
    assert other.post('/api/v1/native-web-session',json=body).status_code == 401
    result = first.post('/api/v1/native-web-session',json=body,follow_redirects=False)
    assert result.status_code == 200
    assert result.json() == {'destination':'/studio'}
    assert len(result.headers.get_list('set-cookie')) == 1
    assert 'location' not in result.headers
    cookie = result.cookies.get('nova_session')
    assert user_from_session(cookie).id == uid
    assert 'HttpOnly' in result.headers['set-cookie'] and 'SameSite=lax' in result.headers['set-cookie']
    assert first.post('/api/v1/native-web-session',json=body).status_code == 401
    browser = TestClient(app)
    browser.cookies.set('nova_session',cookie)
    assert browser.get('/studio').status_code == 200
    first.post('/api/v1/auth/logout')
    assert browser.get('/api/drafts').status_code == 401


def test_native_cookie_bootstrap_rejects_browser_authority_origin_and_wrong_purpose(monkeypatch):
    native, web, *_ = sign_in()
    ticket = handoff(native)
    assert web.post('/api/v1/native-web-session',json={'ticket':ticket}).status_code == 401
    assert native.post('/api/v1/native-web-session',json={'ticket':ticket},headers={'origin':'null','x-zova-native-handoff':'1'}).status_code == 403
    wrong = handoff(native,'/account','browser')
    assert native.post('/api/v1/native-web-session',json={'ticket':wrong}).status_code == 401
    monkeypatch.setenv('PUBLIC_BASE_URL','https://zova-social.com')
    accepted = native.post('/api/v1/native-web-session',json={'ticket':ticket})
    assert accepted.status_code == 200 and '; Secure' in accepted.headers['set-cookie']


def test_native_cookie_bootstrap_is_gated_and_expired_ticket_cannot_set_cookie(monkeypatch):
    native, *_ = sign_in()
    ticket = handoff(native)
    with SessionLocal() as db:
        db.get(MobileHandoff,hash_api_key(ticket)).expires_at = utcnow()-timedelta(seconds=1)
        db.commit()
    failed = native.post('/api/v1/native-web-session',json={'ticket':ticket})
    assert failed.status_code == 401 and 'set-cookie' not in failed.headers
    monkeypatch.setenv('ZOVA_MOBILE_ENABLED','false')
    assert native.post('/api/v1/native-web-session',json={'ticket':ticket}).status_code == 404
