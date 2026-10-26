from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
from nova.app import app
from nova import media_export, storage
from nova.db import Brand, MediaAsset, SessionLocal
from test_account_integrity import account


def asset(uid, brand=0, key=None):
    if key is None:
        path=storage.UPLOAD_DIR / ('export-' + str(uid) + '-' + str(brand) + '.mp4')
        path.write_bytes(b'video-test')
        key=str(path)
    with SessionLocal() as db:
        row=MediaAsset(user_id=uid,brand_id=brand,filename='../My video.mp4',
            mime_type='video/mp4',size_bytes=10,storage_key=key)
        db.add(row);db.commit();return row.id


def test_download_is_private_and_does_not_disclose_existence():
    client,uid,_,_=account();other,_,_,_=account();mid=asset(uid)
    guest=TestClient(app)
    assert guest.get('/media/download/'+str(mid)).status_code==401
    assert guest.get('/media/download/999999999').status_code==401
    assert other.get('/media/download/'+str(mid)).status_code==404
    response=client.get('/media/download/'+str(mid))
    assert response.status_code==200 and response.content==b'video-test'
    assert response.headers['cache-control']=='no-store'
    assert 'attachment' in response.headers['content-disposition']
    assert '..' not in response.headers['content-disposition']


def test_download_requires_current_brand_and_existing_safe_media(tmp_path):
    client,uid,_,_=account()
    with SessionLocal() as db:
        brand=Brand(user_id=uid,name='Second brand');db.add(brand);db.commit();bid=brand.id
    mid=asset(uid,bid)
    assert client.get('/media/download/'+str(mid)).status_code==404
    assert client.get(f'/media/download/{mid}?workspace={bid}').status_code==200
    with SessionLocal() as db:
        row=db.get(MediaAsset,mid);Path(row.storage_key).unlink()
    assert client.get(f'/media/download/{mid}?workspace={bid}').status_code==404
    private=tmp_path/'private.mp4';private.write_bytes(b'video-test')
    bad=asset(uid,key=str(private))
    assert client.get('/media/download/'+str(bad)).status_code==404


def test_remote_download_stream_closes_and_provider_failure_is_redacted(monkeypatch):
    client,uid,_,_=account();mid=asset(uid,key='nova/synthetic.mp4')
    monkeypatch.setenv('S3_BUCKET','synthetic-bucket')
    closed=[]
    stream=SimpleNamespace(iter_chunks=lambda chunk_size:iter([b'video-',b'test']),close=lambda:closed.append(True))
    remote=SimpleNamespace(head_object=lambda **kw:{'ContentLength':10},get_object=lambda **kw:{'Body':stream})
    monkeypatch.setattr(storage,'_s3_client',lambda:remote)
    monkeypatch.setattr(media_export,'_s3_client',lambda:remote)
    response=client.get('/media/download/'+str(mid))
    assert response.status_code==200 and response.content==b'video-test' and closed==[True]
    def fail(**kw):raise RuntimeError('private-storage-credentials')
    remote.get_object=fail
    response=client.get('/media/download/'+str(mid))
    assert response.status_code==503 and 'private-storage' not in response.text


def test_signed_out_help_is_public_and_access_forms_have_separate_controls():
    client=TestClient(app)
    response=client.get('/help')
    assert response.status_code==200 and 'From idea to post' in response.text
    assert 'account-access.css' in client.get('/login').text
    assert 'account-access.css' in client.get('/forgot-password').text
