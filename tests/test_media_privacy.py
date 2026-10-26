"""Exercise real uploads, cross-account access and provider fetch capabilities."""
import io
from urllib.parse import urlsplit, parse_qs

import pytest
from PIL import Image
from fastapi.testclient import TestClient
from nova.app import app
from nova import storage
from nova.db import SessionLocal, MediaAsset, User
from test_account_integrity import account


def upload(client):
    stream = io.BytesIO()
    Image.new('RGB', (2, 2)).save(stream, format='PNG')
    return client.post('/api/media', files={'files': ('photo.png', stream.getvalue(), 'image/png')})


def test_media_requires_owner_or_expiring_provider_capability(monkeypatch):
    owner, uid, *_ = account()
    other, *_ = account()
    asset = upload(owner).json()['assets'][0]
    anonymous = TestClient(app)
    assert owner.get(asset['url']).status_code == 200
    assert other.get(asset['url']).status_code == 404
    assert anonymous.get(asset['url']).status_code == 404
    assert other.get(f"/media/preview/{asset['id']}").status_code == 404
    with SessionLocal() as db:
        row = db.get(MediaAsset, asset['id'])
        signed = storage.get_public_url(row.storage_key, row.public_url)
    assert anonymous.get(signed).content == owner.get(asset['url']).content
    assert anonymous.get(signed).headers['cache-control'] == 'no-store'
    assert anonymous.get(signed + 'x').status_code == 404
    second = upload(owner).json()['assets'][0]
    substituted = second['url'] + '?' + urlsplit(signed).query
    assert anonymous.get(substituted).status_code == 404
    expiry = int(parse_qs(urlsplit(signed).query)['expires'][0])
    with monkeypatch.context() as patch:
        patch.setattr(storage.time, 'time', lambda: expiry + 1)
        assert anonymous.get(signed).status_code == 404
    with SessionLocal() as db:
        db.get(User, uid).active = False
        db.commit()
    assert anonymous.get(signed).status_code == 404


def test_unregistered_uploads_and_external_files_are_not_served(tmp_path):
    client, *_ = account()
    orphan = storage.UPLOAD_DIR / 'unregistered-test.png'
    orphan.write_bytes(b'not registered')
    assert client.get('/media/raw/' + orphan.name).status_code == 404
    outside = tmp_path / 'private.txt'
    outside.write_bytes(b'private')
    with pytest.raises(ValueError):
        storage.get_bytes(str(outside))
    assert not storage.valid_media_signature('photo.png', 9999999999, '\u00e9' * 64)


def test_account_storage_budget_cannot_be_bypassed_by_switching_brands():
    client, uid, *_ = account()
    with SessionLocal() as db:
        db.add(MediaAsset(user_id=uid, brand_id=0, filename='large.mp4', mime_type='video/mp4',
                          storage_key='synthetic-quota-only', size_bytes=500 * 1024 * 1024))
        db.commit()
    assert client.post('/brands', data={'name': 'Another workspace'}, follow_redirects=False).status_code == 303
    assert upload(client).status_code == 413
    other, *_ = account()
    assert upload(other).status_code == 200


def test_insights_uses_shared_ai_rate_limit(monkeypatch):
    import nova.request_security as security
    client, uid, *_ = account()
    calls = []
    def refuse(key, maximum, seconds):
        calls.append((key, maximum, seconds))
        return False
    monkeypatch.setattr(security, 'allowed_request', refuse)
    monkeypatch.setenv('RATE_LIMIT_SCALE', '1')
    assert client.post('/api/insights', json={}).status_code == 429
    assert calls == [(f'user:{uid}:ai', 20, 60)]
