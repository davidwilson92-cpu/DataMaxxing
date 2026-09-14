"""Run only with an isolated DATABASE_URL; no real OAuth calls or tokens."""
import importlib
import secrets
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from nova.db import SessionLocal, User, SocialConnection, OAuthState, utcnow
from nova.security import hash_password, make_user_session, hash_api_key, decrypt

module = importlib.import_module("nova.app")


@pytest.fixture
def signed_in(monkeypatch):
    for key in ("INSTAGRAM_APP_ID", "INSTAGRAM_APP_SECRET", "META_APP_ID", "META_APP_SECRET", "TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "X_OAUTH2_CLIENT_ID"):
        monkeypatch.setenv(key, "synthetic-test-value")
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://testserver")
    monkeypatch.setenv("INSTAGRAM_REDIRECT_URI", "http://testserver/oauth/instagram/callback")
    monkeypatch.setenv("META_REDIRECT_URI", "http://testserver/oauth/meta/callback")
    monkeypatch.delenv("INSTAGRAM_SCOPES", raising=False)
    monkeypatch.setattr(module, "learn_voice_from_socials", lambda *args: None)
    with SessionLocal() as db:
        user = User(email=f"routes-{secrets.token_hex(6)}@example.test", password_hash=hash_password("synthetic-password"), display_name="Route test")
        db.add(user); db.commit(); db.refresh(user)
        user_id = user.id
    client = TestClient(module.app)
    client.cookies.set("nova_session", make_user_session(user_id))
    yield client, user_id
    client.close()


def state_from(response):
    return parse_qs(urlsplit(response.headers["location"]).query)["state"][0]


def test_instagram_uses_only_instagram(signed_in):
    client, _ = signed_in
    response = client.get("/oauth/instagram/start", follow_redirects=False)
    parsed = urlsplit(response.headers["location"])
    assert parsed.hostname == "www.instagram.com"
    query = parse_qs(parsed.query)
    assert query["scope"] == ["instagram_business_basic,instagram_business_content_publish"]
    assert query["enable_fb_login"] == ["0"]
    assert query["redirect_uri"] == ["http://testserver/oauth/instagram/callback"]


@pytest.mark.parametrize("key", ["INSTAGRAM_APP_ID", "INSTAGRAM_APP_SECRET"])
def test_missing_instagram_key_never_falls_back(signed_in, monkeypatch, key):
    client, user_id = signed_in
    monkeypatch.delenv(key)
    response = client.get("/oauth/instagram/start", follow_redirects=False)
    assert response.headers["location"] == "/connect/instagram?error=unavailable"
    page = client.get(response.headers["location"])
    assert "not available yet" in page.text
    assert 'href="/oauth/meta/start"' not in page.text
    with SessionLocal() as db:
        assert db.scalar(select(OAuthState).where(OAuthState.user_id == user_id)) is None


def test_facebook_does_not_import_or_overwrite_instagram(signed_in, monkeypatch):
    client, user_id = signed_in
    with SessionLocal() as db:
        module.upsert_connection(db, user_id=user_id, platform="instagram", account_id="ig-preserved", username="kept", display_name="Kept", access="synthetic-existing-token", scope="instagram_business_basic", metadata={"auth_provider":"instagram_login"})
    monkeypatch.setattr(module, "meta_exchange", lambda code: [{"id":"page-1", "access_token":"synthetic-page-token", "name":"Demo Page", "instagram_business_account":{"id":"ig-preserved", "username":"wrong"}}])
    response = client.get("/oauth/meta/start", follow_redirects=False)
    assert "instagram" not in parse_qs(urlsplit(response.headers["location"]).query)["scope"][0]
    result = client.get("/oauth/meta/callback", params={"code":"synthetic", "state":state_from(response)}, follow_redirects=False)
    assert result.headers["location"] == "/account?connected=facebook"
    with SessionLocal() as db:
        rows=db.scalars(select(SocialConnection).where(SocialConnection.user_id == user_id)).all()
        assert {row.platform for row in rows} == {"instagram", "facebook"}
        ig=next(row for row in rows if row.platform == "instagram")
        assert ig.username == "kept" and decrypt(ig.encrypted_access_token) == "synthetic-existing-token"


def test_instagram_success_replay_and_owner_binding(signed_in, monkeypatch):
    client, user_id = signed_in
    monkeypatch.setattr(module,"instagram_exchange",lambda code: {"profile":{"id":"ig-new","username":"demo"},"access_token":"synthetic-ig-token","expires_in":3600})
    raw = state_from(client.get("/oauth/instagram/start", follow_redirects=False))
    other = TestClient(module.app)
    other.cookies.set("nova_session", "invalid-user-session")
    assert other.get("/oauth/instagram/callback",params={"code":"synthetic","state":raw}).status_code == 401
    with SessionLocal() as db:
        other_user=User(email=f"other-{secrets.token_hex(6)}@example.test",password_hash="unused",display_name="Other workspace")
        db.add(other_user);db.commit();db.refresh(other_user);other_id=other_user.id
    other.cookies.set("nova_session",make_user_session(other_id))
    assert other.get("/oauth/instagram/callback",params={"code":"synthetic","state":raw}).status_code == 400
    result=client.get("/oauth/instagram/callback",params={"code":"synthetic","state":raw},follow_redirects=False)
    assert result.headers["location"] == "/account?connected=instagram"
    assert client.get("/oauth/instagram/callback",params={"code":"synthetic","state":raw}).status_code == 400


def test_expired_state_rejected(signed_in):
    client, _ = signed_in
    raw=state_from(client.get("/oauth/instagram/start",follow_redirects=False))
    with SessionLocal() as db:
        row=db.scalar(select(OAuthState).where(OAuthState.state_hash == hash_api_key(raw)))
        row.created_at=utcnow()-timedelta(minutes=21);db.commit()
    assert client.get("/oauth/instagram/callback",params={"code":"synthetic","state":raw}).status_code == 400


@pytest.mark.parametrize("platform", ["instagram","meta","tiktok","x"])
def test_cancel_returns_to_onboarding(signed_in, platform):
    client, _=signed_in
    client.get("/onboarding/socials")
    result=client.get(f"/oauth/{platform}/callback?error=access_denied",follow_redirects=False)
    name="facebook" if platform=="meta" else platform
    assert result.headers["location"] == f"/onboarding/socials?cancelled={name}"
    assert "connection cancelled" in client.get(result.headers["location"]).text


def test_failure_does_not_expose_provider_response(signed_in, monkeypatch):
    client,_=signed_in
    def fail(code):raise RuntimeError("SECRET_TOKEN synthetic-provider-response")
    monkeypatch.setattr(module,"instagram_exchange",fail)
    raw=state_from(client.get("/oauth/instagram/start",follow_redirects=False))
    result=client.get("/oauth/instagram/callback",params={"code":"synthetic","state":raw})
    assert "could not finish connecting Instagram" in result.text
    assert "SECRET_TOKEN" not in result.text


def test_clear_shared_routes_and_no_password_collection(signed_in):
    client,_=signed_in
    for path in ("/account","/onboarding/socials"):
        text=client.get(path).text
        for platform in ("instagram","facebook","tiktok","x"):
            assert f'href="/connect/{platform}"' in text
    page=client.get("/connect/instagram").text
    assert "Continue to Instagram" in page and 'type="password"' not in page


def test_signed_out_connect_resumes_safe_preflight(signed_in):
    _,user_id=signed_in
    client=TestClient(module.app)
    response=client.get("/oauth/instagram/start",follow_redirects=False)
    assert response.headers["location"] == "/login?next=%2Fconnect%2Finstagram"
    with SessionLocal() as db: email=db.get(User,user_id).email
    for target,expected in [("/connect/instagram","/connect/instagram"),("https://evil.example/","/studio"),("//evil.example/","/studio"),("/oauth/instagram/start","/studio")]:
        result=client.post("/login",data={"email":email,"password":"synthetic-password","next":target},follow_redirects=False)
        assert result.headers["location"] == expected


def test_account_resets_onboarding_return_and_empty_facebook_is_not_success(signed_in, monkeypatch):
    client,_=signed_in
    client.get("/onboarding/socials")
    client.get("/account")
    assert not client.cookies.get("zova_onboarding")
    monkeypatch.setattr(module,"meta_exchange",lambda code: [])
    raw=state_from(client.get("/oauth/meta/start",follow_redirects=False))
    response=client.get("/oauth/meta/callback",params={"code":"synthetic","state":raw},follow_redirects=False)
    assert response.headers["location"] == "/account?no_pages=facebook"


def test_other_platform_authorisation_destinations(signed_in):
    client,_=signed_in
    for platform,host in [("tiktok","www.tiktok.com"),("x","twitter.com")]:
        response=client.get(f"/oauth/{platform}/start",follow_redirects=False)
        parsed=urlsplit(response.headers["location"])
        assert parsed.hostname in ({"twitter.com","x.com"} if platform=="x" else {host})
        if platform=="tiktok":
            scopes=parse_qs(parsed.query)["scope"][0].split(",")
            assert "video.upload" in scopes and "video.publish" not in scopes


def test_instagram_facebook_is_explicit_and_connects_only_instagram(signed_in, monkeypatch):
    client,user_id=signed_in
    monkeypatch.delenv("INSTAGRAM_APP_SECRET")
    page=client.get("/connect/instagram").text
    assert "Use Instagram" in page and "Use Facebook" in page
    assert 'href="/oauth/instagram/start"' not in page
    assert 'href="/oauth/instagram/facebook/start"' in page
    start=client.get("/oauth/instagram/facebook/start",follow_redirects=False)
    parsed=urlsplit(start.headers["location"])
    assert parsed.hostname == "www.facebook.com"
    scopes=parse_qs(parsed.query)["scope"][0].split(",")
    assert "instagram_basic" in scopes and "instagram_content_publish" in scopes
    assert "instagram_business_basic" not in scopes
    def exchange(code, *, include_instagram=False):
        assert include_instagram
        return [{"id":"page-route", "access_token":"synthetic-page-token", "name":"Page", "instagram_business_account":{"id":"ig-route", "username":"correct_instagram"}}]
    monkeypatch.setattr(module,"meta_exchange",exchange)
    result=client.get("/oauth/meta/callback",params={"code":"synthetic","state":state_from(start)},follow_redirects=False)
    assert result.headers["location"] == "/account?connected=instagram"
    with SessionLocal() as db:
        rows=db.scalars(select(SocialConnection).where(SocialConnection.user_id==user_id)).all()
        assert len(rows)==1 and rows[0].platform=="instagram"
        assert rows[0].username=="correct_instagram"
    assert "Connection options" in client.get("/account").text


def test_instagram_facebook_requires_linked_account_and_preserves_direct(signed_in, monkeypatch):
    client,user_id=signed_in
    monkeypatch.setattr(module,"meta_exchange",lambda code, **kwargs: [{"id":"page-only","access_token":"synthetic"}])
    raw=state_from(client.get("/oauth/instagram/facebook/start",follow_redirects=False))
    result=client.get("/oauth/meta/callback",params={"code":"synthetic","state":raw},follow_redirects=False)
    assert result.headers["location"] == "/account?no_pages=instagram"
    with SessionLocal() as db:
        module.upsert_connection(db,user_id=user_id,platform="instagram",account_id="ig-direct",username="kept",display_name="Kept",access="synthetic-direct-token",scope="instagram_business_basic",metadata={"auth_provider":"instagram_login"})
    monkeypatch.setattr(module,"meta_exchange",lambda code, **kwargs: [{"id":"page","access_token":"synthetic-facebook-token","instagram_business_account":{"id":"ig-direct","username":"other"}}])
    raw=state_from(client.get("/oauth/instagram/facebook/start",follow_redirects=False))
    client.get("/oauth/meta/callback",params={"code":"synthetic","state":raw})
    with SessionLocal() as db:
        row=db.scalar(select(SocialConnection).where(SocialConnection.user_id==user_id))
        assert row.username=="kept" and decrypt(row.encrypted_access_token)=="synthetic-direct-token"


def test_instagram_facebook_cancel_and_signed_out_return(signed_in):
    client,_=signed_in
    client.get("/onboarding/socials")
    raw=state_from(client.get("/oauth/instagram/facebook/start",follow_redirects=False))
    response=client.get("/oauth/meta/callback",params={"error":"access_denied","state":raw},follow_redirects=False)
    assert response.headers["location"]=="/onboarding/socials?cancelled=instagram"
    client.cookies.clear()
    response=client.get("/oauth/instagram/facebook/start",follow_redirects=False)
    assert response.headers["location"]=="/login?next=%2Fconnect%2Finstagram"
