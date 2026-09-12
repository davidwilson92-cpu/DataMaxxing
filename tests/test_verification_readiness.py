import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SESSION_SECRET", "test-session-secret")
os.environ.setdefault("CREDENTIAL_ENCRYPTION_KEY", "eV7ZGbkgONCU5t6fVtxgBMvCKx6-4UlAHWVHN2LoflE=")

from fastapi.testclient import TestClient
from nova.app import app


def test_private_pages_redirect_to_login():
    client = TestClient(app)
    for path in ("/studio", "/account", "/analytics", "/drafts"):
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/login"


def test_api_and_oauth_errors_are_not_hidden():
    client = TestClient(app)
    assert client.get("/api/drafts", follow_redirects=False).status_code == 401
    for path in ("/oauth/meta/callback", "/oauth/tiktok/callback"):
        assert client.get(path, follow_redirects=False).status_code == 400


def test_operator_identity_visible_on_public_pages(monkeypatch):
    monkeypatch.setenv("LEGAL_ENTITY_NAME", "ZOVA SOCIAL LIMITED")
    client = TestClient(app)
    for path in ("/", "/signup", "/login", "/privacy-policy", "/terms-of-service", "/refund-policy", "/data-deletion"):
        response = client.get(path)
        assert response.status_code == 200
        assert "Operated by ZOVA SOCIAL LIMITED" in response.text
