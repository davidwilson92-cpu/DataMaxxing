import io
from datetime import timedelta
from PIL import Image
from test_account_integrity import account
from nova.db import SessionLocal, RecoveryToken, User, utcnow
from nova.security import hash_api_key, user_from_session
from nova.request_security import allowed_request


def test_origin_and_security_headers():
    client, uid, _, _ = account()
    assert client.post('/account/profile',headers={'Origin':'https://other.example'},data={'display_name':'Wrong'}).status_code == 403
    page=client.get('/account')
    assert page.headers['x-frame-options']=='DENY'
    assert page.headers['cache-control']=='no-store'
    assert 'frame-ancestors' in page.headers['content-security-policy']


def test_database_limiter_is_shared_and_bounded():
    import secrets
    key=secrets.token_hex(16)
    assert allowed_request(key,2,60)
    assert allowed_request(key,2,60)
    assert not allowed_request(key,2,60)


def test_media_is_decoded_and_storage_extension_is_safe():
    client, uid, _, _ = account()
    for name,content,mime in [('active.svg',b'<svg/>','image/svg+xml'),('fake.png',b'<html/>','image/png')]:
        assert client.post('/api/media',files={'files':(name,content,mime)}).status_code==400
    png=io.BytesIO(); Image.new('RGB',(2,2)).save(png,format='PNG')
    result=client.post('/api/media',files={'files':('misleading.html',png.getvalue(),'image/png')})
    assert result.status_code==200
    url=result.json()['assets'][0]['url']
    assert url.endswith('.png')
    response=client.get(url)
    assert response.headers['content-type'].startswith('image/png')
    assert 'sandbox' in response.headers['content-security-policy']


def test_video_requires_decodable_frames():
    import av
    client,*_=account()
    assert client.post('/api/media',files={'files':('fake.mp4',b'0000ftypinvalid','video/mp4')}).status_code==400
    output=io.BytesIO()
    with av.open(output,mode='w',format='mp4') as container:
        stream=container.add_stream('mpeg4',rate=24);stream.width=16;stream.height=16;stream.pix_fmt='yuv420p'
        frame=av.VideoFrame.from_image(Image.new('RGB',(16,16)))
        for packet in stream.encode(frame):container.mux(packet)
        for packet in stream.encode():container.mux(packet)
    assert client.post('/api/media',files={'files':('synthetic.mp4',output.getvalue(),'video/mp4')}).status_code==200


def test_recovery_is_single_use_revokes_sessions_and_does_not_enumerate(monkeypatch):
    import nova.recovery as module
    client, uid, old_token, email = account()
    sent=[]
    monkeypatch.setattr(module,'recovery_ready',lambda:True)
    monkeypatch.setattr(module,'send_recovery_email',lambda address,token:sent.append((address,token)))
    known=client.post('/forgot-password',data={'email':email},follow_redirects=False)
    unknown=client.post('/forgot-password',data={'email':'missing@example.test'},follow_redirects=False)
    assert known.headers['location']==unknown.headers['location']
    assert len(sent)==1
    token=sent[0][1]
    with SessionLocal() as db:
        assert db.get(RecoveryToken,token) is None
        assert db.get(RecoveryToken,hash_api_key(token))
    body={'token':token,'password':'replacement-password-123','confirmation':'replacement-password-123'}
    assert client.post('/reset-password',data=body,follow_redirects=False).status_code==303
    assert user_from_session(old_token) is None
    assert client.post('/reset-password',data=body).status_code==400


def test_recovery_expiry_and_unknown_deletion_status():
    client, uid, token, _ = account()
    with SessionLocal() as db:
        db.add(RecoveryToken(token_hash=hash_api_key('expired'),user_id=uid,auth_version=0,expires_at=utcnow()-timedelta(minutes=1)))
        db.commit()
    assert client.post('/reset-password',data={'token':'expired','password':'replacement-password-123','confirmation':'replacement-password-123'}).status_code==400
    assert user_from_session(token)
    assert client.get('/data-deletion/status/invented').status_code==404
def test_chunked_body_limit_before_handler():
    import asyncio
    from nova.body_limit import BodyLimitMiddleware
    sent=[]
    async def receive():return {'type':'http.request','body':b'x'*(1024*1024+1),'more_body':False}
    async def send(message):sent.append(message)
    async def forbidden(*args):raise AssertionError('Oversized request reached handler')
    asyncio.run(BodyLimitMiddleware(forbidden)({'type':'http','method':'POST','path':'/api/drafts'},receive,send))
    assert sent[0]['status']==413
