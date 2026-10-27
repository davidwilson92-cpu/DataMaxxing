"""Native presentation uses the established device/brand security boundary."""
import pytest
from fastapi.testclient import TestClient
from nova.app import app
from nova.db import Brand, SocialConnection, SessionLocal
from test_ios_beta_handoff import sign_in, handoff, CALLBACK


@pytest.fixture
def native(monkeypatch):
    monkeypatch.setenv('ZOVA_MOBILE_ENABLED', 'true')
    monkeypatch.setenv('ZOVA_IOS_REDIRECT_URI', CALLBACK)
    monkeypatch.setenv('RATE_LIMIT_SCALE', '100')
    client, web, uid, pair, _ = sign_in()
    response = client.post('/api/v1/native-web-session', json={'ticket': handoff(client)})
    assert response.status_code == 200, response.text
    client.headers.pop('Authorization')
    return client, web, uid, pair


def test_native_account_contract_exposes_only_owned_presentation(native):
    client, _, uid, _ = native
    with SessionLocal() as db:
        db.add(SocialConnection(user_id=uid, platform='instagram', account_id='hidden-account-id',
            username='creator', display_name='Creator name', encrypted_access_token='never-serialize-token', active=True))
        db.commit()
    reply = client.get('/api/native/account')
    assert reply.status_code == 200, reply.text
    data = reply.json()
    assert data['presentation_version'] == 1
    assert data['profile']['id'] == uid
    assert data['connections'][0]['name'] == 'Creator name'
    assert data['billing']['native_purchases'] is False
    assert 'timezone' in data['voice'] and 'approved_examples' in data['voice']
    assert not any(secret in reply.text for secret in ['hidden-account-id', 'never-serialize-token', 'password_hash', 'encrypted_access_token'])
    assert reply.headers['cache-control'] == 'no-store'


def test_native_account_brands_and_revoked_device_are_rejected(native):
    client, _, uid, pair = native
    from test_account_integrity import account
    _, other_uid, _, _ = account()
    with SessionLocal() as db:
        brand = Brand(user_id=other_uid, name='Other brand')
        db.add(brand); db.commit(); db.refresh(brand); brand_id = brand.id
    assert client.get('/api/native/account', headers={'X-Zova-Brand': str(brand_id)}).status_code == 404
    assert client.get('/api/native/account', headers={'X-Zova-Brand': 'invalid'}).status_code == 400
    assert TestClient(app).get('/api/native/account').status_code == 401
    assert TestClient(app).get('/api/native/deletion-confirmation').status_code == 401
    assert client.post('/api/v1/auth/logout', headers={'Authorization': 'Bearer ' + pair['access_token']}).status_code == 204
    assert client.get('/api/native/account').status_code == 401


def test_native_client_retains_ai_origin_and_revision_guards(native, monkeypatch):
    client, _, uid, _ = native
    monkeypatch.setenv('ZOVA_AI_CONSENT_REQUIRED', 'true')
    reply = client.post('/api/ai/generate', json={'brief':'Synthetic post', 'platforms':['instagram']})
    assert reply.status_code == 403 and reply.json()['code'] == 'ai_permission_required'
    assert client.post('/api/drafts', json={}, headers={'Origin':'https://untrusted.example'}).status_code == 403
    draft = client.post('/api/drafts', json={}).json()
    payload = {'brief':'Native draft', 'revision':draft['revision'], 'platforms':[], 'variants':{},
               'workspace':{'composer':'Unsent idea', 'conversation':[]}}
    saved = client.patch('/api/drafts/' + str(draft['id']), json=payload)
    assert saved.status_code == 200
    assert client.patch('/api/drafts/' + str(draft['id']), json=payload).status_code == 409
    assert client.get('/api/drafts/' + str(draft['id'])).json()['workspace']['composer'] == 'Unsent idea'


def test_native_deletion_proof_is_bound_to_this_session(native):
    client, web, _, _ = native
    proof = client.get('/api/native/deletion-confirmation').json()['proof']
    reply = web.post('/account/deletion', data={'confirmation':'DELETE', 'current_password':'old-password-123', 'proof':proof})
    assert reply.status_code == 400


def test_native_history_pagination_retains_owner_filter_and_revisions(native):
    from nova.db import Draft
    client, _, uid, _ = native
    with SessionLocal() as db:
        db.add_all([Draft(user_id=uid, brief=f'Native history {n}', revision=n) for n in range(105)])
        db.commit()
    first = client.get('/api/drafts').json()
    second = client.get('/api/drafts?offset=100').json()
    assert len(first) == 100 and len(second) == 5
    assert not set(row['id'] for row in first).intersection(row['id'] for row in second)
    assert all(type(row['revision']) is int for row in first + second)
    assert client.get('/api/drafts?offset=-1').status_code == 422
    assert client.get('/api/drafts?offset=100001').status_code == 422
    found = client.get('/api/drafts?q=Native%20history%20104&offset=0').json()
    assert len(found) == 1 and found[0]['brief'] == 'Native history 104'


def test_native_schedule_status_filters_and_summary_match_web_semantics(native):
    from nova.db import Draft
    client, _, uid, _ = native
    with SessionLocal() as db:
        db.add_all([Draft(user_id=uid, brief='Native ' + state, status=state)
                    for state in ['draft', 'cancelled', 'failed', 'partial', 'needs_review', 'published']])
        db.commit()
    assert {r['status'] for r in client.get('/api/drafts?status=draft').json()} == {'draft', 'cancelled'}
    assert {r['status'] for r in client.get('/api/drafts?status=needs_review').json()} == {'failed', 'partial', 'needs_review'}
    assert {r['status'] for r in client.get('/api/drafts?status=published').json()} == {'published'}
    assert client.get('/api/drafts?status=invalid').status_code == 422
    result = client.get('/api/native/schedule-summary')
    assert result.status_code == 200 and 'no-store' in result.headers['cache-control']
    assert result.json() == {'drafts': 2, 'scheduled': 0, 'overdue': 0, 'unconfirmed': 0, 'needs_review': 3}
    assert TestClient(app).get('/api/native/schedule-summary').status_code == 401
