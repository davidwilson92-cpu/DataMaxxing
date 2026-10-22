"""Synthetic OAuth grants only; no real accounts or posts."""
import re
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient
from nova.app import app
from nova.db import SessionLocal, SocialConnection
from nova.security import hash_api_key
from test_ios_beta_handoff import sign_in, handoff, native_config


@pytest.mark.parametrize('platform', ['instagram', 'facebook', 'x', 'tiktok'])
@pytest.mark.parametrize('outcome', ['connected', 'cancelled', 'connection_failed', 'no_pages'])
def test_native_return_is_bound_to_active_device_attempt_and_provider(platform, outcome):
    from nova.mobile_shell import social_return, social_return_cookie
    from starlette.requests import Request
    native, _, uid, pair, _ = sign_in()
    browser = TestClient(app)
    ticket = handoff(native, '/connect/' + platform + '?workspace=0', 'browser')
    path = '/mobile/browser/' + ticket + '?return_to_app=1'
    page = browser.get(path)
    proof = re.search(r'name="proof" value="([a-f0-9]+)"', page.text)[1]
    response = browser.post(path, data={'proof': proof}, follow_redirects=False)
    cookie = response.cookies['nova_session']
    flow = response.cookies['zova_social_return']
    def request(session=cookie, context=flow):
        return Request({'type': 'http', 'headers': [(b'cookie', f'nova_session={session}; zova_social_return={context}'.encode())]})
    result = social_return(request(), platform, outcome)
    assert result.status_code == 303
    assert parse_qs(urlsplit(result.headers['location']).query) == {'social': [outcome], 'platform': [platform], 'state': [hash_api_key(ticket)]}
    assert urlsplit(result.headers['location']).path == '/mobile/callback'
    assert social_return(request(context=flow + 'x'), platform, outcome) is None
    assert social_return(request(session='wrong'), platform, outcome) is None
    assert social_return(request(), 'other', outcome) is None
    other_ticket = handoff(native, '/account', 'browser')
    assert social_return(request(context=social_return_cookie(other_ticket)), platform, outcome) is None
    with SessionLocal() as db:
        assert not db.query(SocialConnection).filter_by(user_id=uid).count()
    native.post('/api/v1/auth/logout')
    assert social_return(request(), platform, outcome) is None


def test_combined_instagram_prompt_keeps_identity_and_both_routes(monkeypatch):
    for key in ['INSTAGRAM_APP_ID', 'INSTAGRAM_APP_SECRET', 'META_APP_ID', 'META_APP_SECRET']:
        monkeypatch.setenv(key, 'synthetic')
    native, *_ = sign_in()
    browser = TestClient(app)
    path = '/mobile/browser/' + handoff(native, '/connect/instagram?workspace=0', 'browser')
    page = browser.get(path)
    assert 'public Instagram Creator or Business' in page.text
    assert 'Continue to Instagram' in page.text and 'Continue with Facebook' in page.text
    assert 'This isn’t my Zova account' in page.text
    proof = re.search(r'name="proof" value="([a-f0-9]+)"', page.text)[1]
    accepted = browser.post(path, data={'proof': proof, 'method': 'facebook'}, follow_redirects=False)
    assert accepted.headers['location'] == '/oauth/instagram/facebook/start?workspace=0'
    assert 'zova_social_return' not in accepted.cookies  # Older binaries retain their flow.
    repeat = browser.post(path, data={'proof': proof, 'method': 'facebook'}, follow_redirects=False)
    assert repeat.headers['location'] == '/connect/instagram?workspace=0'  # Never restart OAuth on replay.


@pytest.mark.parametrize('route,platform', [('instagram', 'instagram'), ('instagram/facebook', 'instagram'), ('meta', 'facebook'), ('x', 'x'), ('tiktok', 'tiktok')])
def test_provider_callback_requires_final_confirmation_before_returning_to_app(monkeypatch, route, platform):
    import importlib
    module = importlib.import_module('nova.app')
    for key in ['INSTAGRAM_APP_ID', 'INSTAGRAM_APP_SECRET', 'META_APP_ID', 'META_APP_SECRET', 'X_OAUTH2_CLIENT_ID', 'TIKTOK_CLIENT_KEY', 'TIKTOK_CLIENT_SECRET']:
        monkeypatch.setenv(key, 'synthetic')
    monkeypatch.setattr(module, 'instagram_exchange', lambda code: {'profile': {'id': 'synthetic-ig', 'username': 'creator'}, 'access_token': 'synthetic-only'})
    monkeypatch.setattr(module, 'meta_exchange', lambda code, **kwargs: [{'id': 'synthetic-page', 'name': 'Demo Page', 'access_token': 'synthetic-only', 'instagram_business_account': {'id': 'synthetic-ig', 'username': 'creator'}}])
    monkeypatch.setattr(module, 'x_exchange', lambda *args: ({'access_token': 'synthetic-only'}, {'id': 'synthetic-x', 'username': 'creator'}))
    monkeypatch.setattr(module, 'tiktok_exchange', lambda *args: ({'access_token': 'synthetic-only'}, {'open_id': 'synthetic-tiktok', 'display_name': 'Creator'}))
    native, _, uid, *_ = sign_in()
    browser = TestClient(app)
    ticket = handoff(native, '/connect/' + platform + '?workspace=0', 'browser')
    path = '/mobile/browser/' + ticket + '?return_to_app=1'
    proof = re.search(r'name="proof" value="([a-f0-9]+)"', browser.get(path).text)[1]
    accepted = browser.post(path, data={'proof': proof, 'method': 'facebook' if route == 'instagram/facebook' else 'direct'}, follow_redirects=False)
    start = browser.get(accepted.headers['location'], follow_redirects=False)
    state = parse_qs(urlsplit(start.headers['location']).query)['state'][0]
    callback = '/oauth/' + ('meta' if route == 'instagram/facebook' else route) + '/callback'
    pending = browser.get(callback, params={'state': state, 'code': 'synthetic'}, follow_redirects=False)
    assert pending.headers['location'].startswith('/connections/review/')
    with SessionLocal() as db:
        assert not db.query(SocialConnection).filter_by(user_id=uid).count()
    confirmed = browser.post(pending.headers['location'], data={'choice': 0, 'action': 'connect'}, follow_redirects=False)
    assert parse_qs(urlsplit(confirmed.headers['location']).query) == {'social': ['connected'], 'platform': [platform], 'state': [hash_api_key(ticket)]}
    with SessionLocal() as db:
        assert db.query(SocialConnection).filter_by(user_id=uid, platform=platform, active=True).count() == 1
    assert browser.post(pending.headers['location'], data={'choice': 0, 'action': 'connect'}).status_code == 410


def test_consumed_return_receipt_survives_cleanup_during_provider_login():
    from datetime import timedelta
    from nova.db import MobileHandoff, utcnow
    from nova.mobile_auth import remove_expired_sessions
    native, *_ = sign_in()
    browser = TestClient(app)
    ticket = handoff(native, '/connect/instagram', 'browser')
    path = '/mobile/browser/' + ticket + '?return_to_app=1'
    proof = re.search(r'name="proof" value="([a-f0-9]+)"', browser.get(path).text)[1]
    browser.post(path, data={'proof': proof}, follow_redirects=False)
    with SessionLocal() as db:
        db.get(MobileHandoff, hash_api_key(ticket)).expires_at = utcnow() - timedelta(minutes=5)
        db.commit()
    remove_expired_sessions()
    with SessionLocal() as db:
        receipt = db.get(MobileHandoff, hash_api_key(ticket))
        assert receipt and receipt.used
        receipt.expires_at = utcnow() - timedelta(minutes=21)
        db.commit()
    remove_expired_sessions()
    with SessionLocal() as db:
        assert db.get(MobileHandoff, hash_api_key(ticket)) is None
