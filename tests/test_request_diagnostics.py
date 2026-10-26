import json
import logging
import re
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from nova.observability import RequestDiagnostics, request_id


def test_failure_has_safe_reference_without_content_or_exception_payload(caplog):
    app=FastAPI()
    app.add_middleware(RequestDiagnostics)
    @app.get('/receipt/{secret}')
    def broken(secret:str):
        assert re.fullmatch('[a-f0-9]{32}',request_id.get())
        raise RuntimeError('provider_token=synthetic-sensitive-token')
    with caplog.at_level(logging.INFO,logger='nova.requests'):
        response=TestClient(app).get('/receipt/private-customer-path?code=secret-code',headers={'X-Request-ID':'user-controlled-ref'})
    assert response.status_code==500
    assert response.json()['support_reference']==response.headers['x-request-id']
    assert response.headers['x-request-id']!='user-controlled-ref'
    assert response.headers['cache-control']=='no-store'
    assert response.headers['x-frame-options']=='DENY'
    assert "default-src 'none'" in response.headers['content-security-policy']
    for forbidden in ['synthetic-sensitive-token','private-customer-path','secret-code','user-controlled-ref']:
        assert forbidden not in caplog.text and forbidden not in response.text
    records=[json.loads(row.message) for row in caplog.records if row.name=='nova.requests']
    assert records[-1]['route']=='/receipt/{secret}' and records[-1]['status']==500
    assert request_id.get() is None


def test_reference_unique_per_request_and_existing_errors_preserved():
    from nova.app import app
    client=TestClient(app)
    a=client.get('/api/privacy/ai');b=client.get('/health')
    assert a.status_code==401 and b.status_code==200
    assert re.fullmatch('[a-f0-9]{32}',a.headers['x-request-id'])
    assert a.headers['x-request-id']!=b.headers['x-request-id']


@pytest.mark.parametrize('platform',['x','instagram','facebook','tiktok'])
def test_oauth_failure_does_not_surface_provider_payload(monkeypatch,platform):
    from types import SimpleNamespace
    from nova import social
    secret='synthetic-provider-secret-never-display'
    response=SimpleNamespace(status_code=400,text=secret,json=lambda:{'error':secret})
    monkeypatch.setattr(social.httpx,'post',lambda *a,**k:response)
    monkeypatch.setattr(social.httpx,'get',lambda *a,**k:response)
    monkeypatch.setenv('X_OAUTH2_CLIENT_ID','synthetic')
    calls={'x':lambda:social._x_token({}), 'instagram':lambda:social.instagram_exchange('synthetic'),
           'facebook':lambda:social.meta_exchange('synthetic'), 'tiktok':lambda:social._tiktok_token({})}
    with pytest.raises(RuntimeError) as failure:calls[platform]()
    assert secret not in str(failure.value)
