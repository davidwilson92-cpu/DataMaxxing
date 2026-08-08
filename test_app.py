import os
from unittest.mock import MagicMock, patch

os.environ.setdefault("POSTING_API_KEY", "test-secret")
os.environ.setdefault("X_API_KEY", "key")
os.environ.setdefault("X_API_SECRET", "secret")
os.environ.setdefault("X_ACCESS_TOKEN", "token")
os.environ.setdefault("X_ACCESS_TOKEN_SECRET", "token-secret")
os.environ.setdefault("X_USERNAME", "DataMaxxing")

from fastapi.testclient import TestClient
from app import app

client = TestClient(app)
HEADERS = {"Authorization": "Bearer test-secret"}


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_auth_required():
    assert client.post("/x/preview", json={"text": "hello"}).status_code == 401


def test_preview():
    response = client.post("/x/preview", headers=HEADERS, json={"text": " hello "})
    assert response.status_code == 200
    assert response.json()["text"] == "hello"
    assert response.json()["character_count"] == 5


def test_approval_required():
    response = client.post("/x/post", headers=HEADERS, json={"text": "hello", "approved": False})
    assert response.status_code == 400


@patch("app.tweepy.Client")
def test_publish(mock_client_class):
    mock_client = MagicMock()
    mock_client.create_tweet.return_value.data = {"id": "123"}
    mock_client_class.return_value = mock_client

    response = client.post(
        "/x/post",
        headers=HEADERS,
        json={"text": "hello", "approved": True},
    )
    assert response.status_code == 200
    assert response.json()["url"] == "https://x.com/DataMaxxing/status/123"
    mock_client.create_tweet.assert_called_once_with(text="hello")
