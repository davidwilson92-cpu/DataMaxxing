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
    assert "Your idea." in landing and "Native everywhere." in landing
    assert "YOUR AI SOCIAL MANAGER" in landing
    assert "Nova" not in landing


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
    assert writing.status_code == 200 and "TEACH ZOVA HOW YOU WRITE" in writing.text


def test_signup_form_has_confirmation_and_client_validation():
    page = client.get("/signup").text
    assert 'name="password_confirmation"' in page
    assert "setCustomValidity" in page


def test_studio_has_premium_application_shell():
    email = f"studio-{secrets.token_hex(5)}@example.com"
    signup = client.post("/signup", data={"email": email, "password": "long-password-1", "password_confirmation": "long-password-1"}, follow_redirects=False)
    page = client.get("/studio", cookies=signup.cookies)
    assert page.status_code == 200
    assert "ZOVA INTELLIGENCE" in page.text
    assert "Shape for every platform" in page.text
    assert 'src="/static/studio.js"' in page.text
    assert "site-header" not in page.text
