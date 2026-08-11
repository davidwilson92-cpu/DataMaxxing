import os
import secrets
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///./zova-test.db")
os.environ.setdefault("SESSION_SECRET", "test-session-secret")
os.environ.setdefault("CREDENTIAL_ENCRYPTION_KEY", "eV7ZGbkgONCU5t6fVtxgBMvCKx6-4UlAHWVHN2LoflE=")
os.environ.setdefault("REQUIRE_SUBSCRIPTION", "false")

from fastapi.testclient import TestClient
from nova.app import app


client = TestClient(app)


def test_health_and_branding():
    response = client.get("/health")
    assert response.json() == {"status": "ok", "version": "5.1.0", "brand": "Zova"}
    landing = client.get("/").text
    assert "One idea." in landing and "Every social." in landing
    assert "YOUR AI SOCIAL MANAGER" in landing
    assert "Nova" not in landing


def test_public_legal_pages_and_footer_links():
    privacy = client.get("/privacy-policy")
    terms = client.get("/terms-of-service")
    assert privacy.status_code == 200 and "TikTok and other platform data" in privacy.text
    assert terms.status_code == 200 and "Connected platforms" in terms.text
    assert 'href="/privacy-policy"' in privacy.text
    assert 'href="/terms-of-service"' in terms.text
    assert client.get("/privacy").status_code == 200
    assert client.get("/terms").status_code == 200


def test_password_confirmation_is_required_server_side():
    response = client.post("/signup", data={"email": "mismatch@example.com", "password": "long-password-1", "password_confirmation": "long-password-2"}, follow_redirects=False)
    assert response.status_code == 303
    assert "Passwords+do+not+match" in response.headers["location"]


def test_signup_routes_through_onboarding():
    email = f"test-{secrets.token_hex(5)}@example.com"
    response = client.post("/signup", data={"email": email, "password": "long-password-1", "password_confirmation": "long-password-1"}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/onboarding/socials"
    assert response.cookies.get("nova_session")
    socials = client.get("/onboarding/socials", cookies=response.cookies)
    assert socials.status_code == 200 and "Skip for now" in socials.text
    writing = client.get("/onboarding/writing-style", cookies=response.cookies)
    assert writing.status_code == 200 and "YOUR ZOVA VOICE" in writing.text
    assert "Paste 3" not in writing.text


def test_signup_form_has_confirmation_and_client_validation():
    page = client.get("/signup").text
    assert 'name="password_confirmation"' in page
    assert "setCustomValidity" in page


def test_studio_has_premium_application_shell():
    email = f"studio-{secrets.token_hex(5)}@example.com"
    signup = client.post("/signup", data={"email": email, "password": "long-password-1", "password_confirmation": "long-password-1"}, follow_redirects=False)
    page = client.get("/studio", cookies=signup.cookies)
    assert page.status_code == 200
    assert "ACCOUNT ANALYTICS" in page.text
    assert "Shape for every platform" in page.text
    assert 'src="/static/studio.js?v=5.7"' in page.text
    assert 'href="/static/nova.css?v=5.8"' in page.text
    assert 'accept="image/*,video/mp4,video/quicktime,video/webm"' in page.text
    assert "Videos publish to Instagram and TikTok only" in page.text
    assert 'id="refineInstruction"' in page.text
    assert 'class="rewrite-shortcuts"' in page.text
    assert "Ã" not in page.text and "â" not in page.text
    assert "site-header" not in page.text
    assert "Give Zova the thought behind the post" not in page.text
    assert 'href="/account#voice"' in page.text
    assert "Calendar" not in page.text
    assert "zova-symbol" in page.text
    assert "ACCOUNT ANALYTICS" in page.text
    assert "ZOVA INTELLIGENCE" not in page.text


def test_account_management_and_social_voice_waiting_state():
    email = f"account-{secrets.token_hex(5)}@example.com"
    signup = client.post("/signup", data={"email": email, "password": "long-password-1", "password_confirmation": "long-password-1"}, follow_redirects=False)
    page = client.get("/account", cookies=signup.cookies).text
    assert 'action="/account/profile"' in page
    assert 'action="/account/password"' in page
    assert "Connected socials" in page and "Change password" in page
    response = client.post("/api/voice/scan-socials", cookies=signup.cookies)
    assert response.json()["status"] == "waiting"


def test_voice_learning_updates_inferred_profile():
    email = f"voice-{secrets.token_hex(5)}@example.com"
    signup = client.post("/signup", data={"email": email, "password": "long-password-1", "password_confirmation": "long-password-1"}, follow_redirects=False)
    import nova.app as app_module
    original = app_module.ai.infer_voice_profile
    app_module.ai.infer_voice_profile = lambda sample: {"summary": "Direct and optimistic.", "writing_tone": "Direct", "audience": "Creators", "topics": "Social media", "things_to_avoid": "Jargon", "preferred_post_length": 180}
    try:
        response = client.post("/api/voice/learn", json={"content": "This is a representative piece of creator writing. " * 4}, cookies=signup.cookies)
    finally:
        app_module.ai.infer_voice_profile = original
    assert response.status_code == 200
    assert response.json()["summary"] == "Direct and optimistic."
