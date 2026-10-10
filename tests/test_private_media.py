import io
from urllib.parse import urlsplit, parse_qs, urlencode, urlunsplit

from fastapi.testclient import TestClient
from PIL import Image

from nova.app import app
from nova.db import MediaAsset, SessionLocal
from nova.storage import get_public_url
from test_account_integrity import account


def test_preview_requires_owner_and_signed_download_expires(monkeypatch):
    owner, _, _, _=account()
    other, _, _, _=account()
    data=io.BytesIO();Image.new('RGB',(2,2)).save(data,format='PNG')
    asset=owner.post('/api/media',files={'files':('private.png',data.getvalue(),'image/png')}).json()['assets'][0]
    anonymous=TestClient(app)
    assert other.get(asset['url'],follow_redirects=False).status_code==404
    assert anonymous.get(asset['url'],follow_redirects=False).status_code in {401,404}
    preview=owner.get(asset['url'],follow_redirects=False)
    assert preview.status_code==307
    signed=preview.headers['location']
    parts=urlsplit(signed)
    assert anonymous.get(parts.path).status_code==404
    assert anonymous.get(signed).status_code==200
    assert anonymous.get(signed).headers['cache-control']=='no-store'
    params=parse_qs(parts.query)
    params['expires']=[str(int(params['expires'][0])+60)]
    tampered=urlunsplit((parts.scheme,parts.netloc,parts.path,urlencode(params,doseq=True),''))
    assert anonymous.get(tampered).status_code==404
    deadline=int(parse_qs(parts.query)['expires'][0])
    monkeypatch.setattr('nova.storage.time.time',lambda:deadline+1)
    assert anonymous.get(signed).status_code==404


def test_s3_uses_presigned_url_instead_of_old_permanent_url(monkeypatch):
    import nova.storage as storage
    calls=[]
    class Client:
        def generate_presigned_url(self,*args,**kwargs):
            calls.append(kwargs)
            return 'https://synthetic-bucket.test/expiring'
    monkeypatch.setenv('S3_BUCKET','synthetic-bucket')
    monkeypatch.setattr(storage,'_s3_client',lambda:Client())
    assert get_public_url('nova/private.png','https://old-public.test/private.png',expires=99999)=='https://synthetic-bucket.test/expiring'
    assert calls[0]['ExpiresIn']==3600


def test_local_url_cannot_sign_files_outside_upload_root(tmp_path):
    import pytest
    path=tmp_path/'private.txt';path.write_text('synthetic secret')
    with pytest.raises(RuntimeError):
        get_public_url(str(path),'https://untrusted.test/file')


def test_access_logs_drop_query_secrets_and_unknown_shapes():
    import logging
    from nova.safe_logging import SafeAccessLog
    record=logging.LogRecord('uvicorn.access',logging.INFO,'',0,'%s - "%s %s HTTP/%s" %d',
                             ('127.0.0.1','GET','/media/raw/file.png?signature=secret&code=oauth-secret','1.1',200),None)
    assert SafeAccessLog().filter(record)
    assert '/media/raw/file.png' in record.getMessage()
    assert 'secret' not in record.getMessage()
    unexpected=logging.LogRecord('uvicorn.access',logging.INFO,'',0,'URL signature=secret',(),None)
    assert not SafeAccessLog().filter(unexpected)
