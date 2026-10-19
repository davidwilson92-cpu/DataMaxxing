import pytest
from fastapi.testclient import TestClient
from nova.app import app
from nova.ai_consent import VERSION
from nova.db import AIConsent, SessionLocal
from test_account_integrity import account


@pytest.fixture(autouse=True)
def real_permission_gate(monkeypatch):
    monkeypatch.delenv('ZOVA_AI_CONSENT_REQUIRED', raising=False)


@pytest.mark.parametrize('path', [
    '/api/ai/generate', '/api/ai/rewrite', '/api/ai/schedule', '/api/voice/learn',
    '/api/voice/scan-socials', '/api/conversation/plan', '/api/insights',
    '/api/strategy/propose', '/api/strategy/recommend',
    '/api/strategy/actions/1/draft', '/api/series/occurrences/1/draft',
])
def test_ai_routes_refuse_before_validation_or_provider_calls(path):
    client, *_ = account()
    result = client.post(path, json={'synthetic_secret':'must not leave Zova'})
    assert result.status_code == 403
    assert result.json()['code'] == 'ai_permission_required'
    assert client.post('/api/drafts').status_code == 200


def test_choice_is_account_bound_versioned_and_revocable():
    client, uid, *_ = account()
    other, *_ = account()
    assert not client.get('/api/privacy/ai').json()['allowed']
    assert client.post('/api/privacy/ai', json={'allowed':True,'version':'old'}).status_code == 409
    assert client.post('/api/privacy/ai', json={'allowed':True,'version':VERSION,'user_id':uid+1}).status_code == 422
    assert client.post('/api/privacy/ai', json={'allowed':'true','version':VERSION}).status_code == 422
    assert client.post('/api/privacy/ai', json={'allowed':True,'version':VERSION}).status_code == 200
    assert client.get('/api/privacy/ai').json()['allowed']
    assert not other.get('/api/privacy/ai').json()['allowed']
    # Harmless deterministic plan; no model request and no grant/publication.
    message={'message':'Create a caption','selected_platforms':['x']}
    assert client.post('/api/conversation/plan',json=message).status_code == 200
    assert client.post('/api/privacy/ai',json={'allowed':False,'version':VERSION}).status_code == 200
    assert client.post('/api/conversation/plan',json=message).status_code == 403
    with SessionLocal() as db:
        assert db.get(AIConsent,uid).allowed is False


def test_anonymous_and_cross_site_cannot_change_choice():
    assert TestClient(app).post('/api/privacy/ai',json={'allowed':True,'version':VERSION}).status_code == 401
    client,*_=account()
    assert client.post('/api/privacy/ai',headers={'Origin':'https://attacker.example'},json={'allowed':True,'version':VERSION}).status_code == 403
    assert not client.get('/api/privacy/ai').json()['allowed']


def test_choice_is_in_export_and_old_versions_require_new_permission():
    client,uid,*_=account()
    client.post('/api/privacy/ai',json={'allowed':True,'version':VERSION})
    from nova.data_lifecycle import export_account
    with SessionLocal() as db:
        assert export_account(db,uid)['zova_ai_consent'][0]['allowed'] is True
        db.get(AIConsent,uid).version='old';db.commit()
    assert not client.get('/api/privacy/ai').json()['allowed']
