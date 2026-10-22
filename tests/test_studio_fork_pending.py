"""Generating a new idea must atomically resolve the old chat's pending turn."""
import json
import pytest
from sqlalchemy import event, func, select
from fastapi.testclient import TestClient

from nova.db import Draft, MediaAsset, SessionLocal
from test_account_integrity import account


def prepared():
    client, uid, token, _ = account()
    with SessionLocal() as db:
        media = MediaAsset(user_id=uid, filename='synthetic.mp4', mime_type='video/mp4',
            storage_key='synthetic-not-uploaded', public_url='https://example.test/media.mp4', size_bytes=20)
        db.add(media); db.commit(); media_id = media.id
    draft = client.post('/api/drafts', json={}).json()
    pending = 'A second caption, this time mentioning our sponsor'
    workspace = {'pending_message':pending, 'composer':'A separate unsent thought',
        'conversation':[{'role':'user','content':'The original idea'}, {'role':'user','content':pending}],
        'media_asset_ids':[media_id], 'link_url':'https://example.test/sponsor',
        'selected_platforms':['tiktok'], 'active_platform':'tiktok', 'platform_selection_explicit':True,
        'video_duration':6, 'instagram_format':'story', 'text_history':[{'tiktok':{'posts':['Earlier caption']}}]}
    saved = client.patch(f"/api/drafts/{draft['id']}", json={'revision':draft['revision'],
        'brief':'Original idea', 'instruction':'Original direction', 'platforms':['tiktok'],
        'variants':{'tiktok':{'posts':['Original caption']}}, 'workspace':workspace})
    assert saved.status_code == 200, saved.text
    # A future server-owned field must not be stripped from the source workspace.
    with SessionLocal() as db:
        row = db.get(Draft, draft['id'])
        state = json.loads(row.workspace_json); state['future_metadata'] = {'preserve':'yes'}
        row.workspace_json = json.dumps(state); db.commit()
    source = client.get(f"/api/drafts/{draft['id']}").json()
    payload = {'brief':pending, 'platforms':['tiktok'], 'source_draft_id':source['id'],
        'source_revision':source['revision']}
    return client, uid, token, source, payload


def draft_count(uid):
    with SessionLocal() as db:
        return db.scalar(select(func.count(Draft.id)).where(Draft.user_id == uid))


def generated(monkeypatch):
    import nova.app as module
    monkeypatch.setattr(module.ai, 'generate_variants', lambda **kwargs:
        {'tiktok':{'posts':['A new sponsored caption']}})
    monkeypatch.setattr(module, 'publish_platform', lambda *a, **k: pytest.fail('Generation cannot publish'))


def test_fork_consumes_source_pending_and_saves_target_workspace_atomically(monkeypatch):
    generated(monkeypatch)
    client, uid, _, source, payload = prepared()
    before = draft_count(uid)
    response = client.post('/api/ai/generate', json=payload)
    assert response.status_code == 200, response.text
    target = client.get(f"/api/drafts/{response.json()['draft_id']}").json()
    old = client.get(f"/api/drafts/{source['id']}").json()
    assert target['id'] != source['id'] and draft_count(uid) == before + 1
    assert old['revision'] == source['revision'] + 1
    assert old['workspace'] == {**source['workspace'], 'pending_message':''}
    for field in ('brief','instruction','variants','platforms','thread_length','status'):
        assert old[field] == source[field]
    assert target['workspace']['pending_message'] == ''
    for field in ('conversation','composer','media_asset_ids','media','link_url','video_duration','instagram_format'):
        assert target['workspace'][field] == source['workspace'][field]
    assert target['workspace']['selected_platforms'] == ['tiktok']
    assert target['workspace']['active_platform'] == 'tiktok'
    assert target['workspace']['text_history'] == []
    assert target['variants'] == {'tiktok':{'posts':['A new sponsored caption']}}
    assert target['status'] == 'draft'
    # A lost browser response cannot replay the old source revision into a second fork.
    assert client.post('/api/ai/generate', json=payload).status_code == 409
    assert draft_count(uid) == before + 1


@pytest.mark.parametrize('fork', [True, False])
def test_generation_failure_retains_pending_and_does_not_create(monkeypatch, fork):
    import nova.app as module
    client, uid, _, source, payload = prepared()
    def failure(**kwargs):
        raise RuntimeError('Synthetic model failure')
    monkeypatch.setattr(module.ai, 'generate_variants', failure)
    if not fork:
        payload = {'draft_id':source['id'], 'brief':payload['brief'], 'platforms':['tiktok']}
    before = draft_count(uid)
    assert client.post('/api/ai/generate', json=payload).status_code == 502
    old = client.get(f"/api/drafts/{source['id']}").json()
    assert old['workspace'] == source['workspace'] and old['revision'] == source['revision']
    assert draft_count(uid) == before


def test_successful_existing_generation_consumes_only_pending_marker(monkeypatch):
    generated(monkeypatch)
    client, uid, _, source, payload = prepared()
    before = draft_count(uid)
    response = client.post('/api/ai/generate', json={'draft_id':source['id'], 'brief':payload['brief'],
        'platforms':['tiktok']})
    assert response.status_code == 200, response.text
    saved = client.get(f"/api/drafts/{source['id']}").json()
    assert saved['workspace'] == {**source['workspace'], 'pending_message':''}
    assert saved['revision'] == source['revision'] + 1 and draft_count(uid) == before


@pytest.mark.parametrize('invalid', ['foreign','immutable','stale'])
def test_invalid_source_is_rejected_before_generation_without_mutation(monkeypatch, invalid):
    import nova.app as module
    client, uid, _, source, payload = prepared()
    other, other_uid, *_ = account()
    if invalid == 'foreign':
        caller, expected = other, 404
    else:
        caller, expected = client, 409
        with SessionLocal() as db:
            row = db.get(Draft, source['id'])
            if invalid == 'immutable': row.status = 'published'
            else: row.revision += 1
            db.commit()
    before = draft_count(uid) + draft_count(other_uid)
    monkeypatch.setattr(module.ai, 'generate_variants', lambda **kwargs: pytest.fail('Invalid source must not call AI'))
    assert caller.post('/api/ai/generate', json=payload).status_code == expected
    assert client.get(f"/api/drafts/{source['id']}").json()['workspace'] == source['workspace']
    assert draft_count(uid) + draft_count(other_uid) == before


@pytest.mark.parametrize('fork', [True, False])
@pytest.mark.parametrize('change', ['revision','immutable'])
def test_source_change_during_generation_cannot_clear_or_create(monkeypatch, fork, change):
    import nova.app as module
    client, uid, _, source, payload = prepared()
    before = draft_count(uid)
    def racing_generation(**kwargs):
        with SessionLocal() as db:
            row = db.get(Draft, source['id'])
            state = json.loads(row.workspace_json); state['composer'] = 'Newer text in another tab'
            row.workspace_json = json.dumps(state)
            if change == 'revision': row.revision += 1
            else: row.status = 'published'
            db.commit()
        return {'tiktok':{'posts':['Stale model response']}}
    monkeypatch.setattr(module.ai, 'generate_variants', racing_generation)
    if not fork:
        payload = {'draft_id':source['id'], 'brief':payload['brief'], 'platforms':['tiktok']}
    result = client.post('/api/ai/generate', json=payload)
    assert result.status_code == 409, result.text
    saved = client.get(f"/api/drafts/{source['id']}").json()
    assert saved['workspace']['pending_message'] == source['workspace']['pending_message']
    assert saved['workspace']['composer'] == 'Newer text in another tab'
    assert saved['variants'] == source['variants'] and draft_count(uid) == before


def test_failed_target_insert_rolls_back_source_pending_clear(monkeypatch):
    import nova.app as module
    generated(monkeypatch)
    client, uid, token, source, payload = prepared()
    before = draft_count(uid)
    def fail_target_insert(mapper, connection, target):
        if target.user_id == uid and target.brief == payload['brief']:
            raise RuntimeError('Synthetic target storage failure')
    event.listen(Draft, 'before_insert', fail_target_insert)
    try:
        failing_client = TestClient(module.app, raise_server_exceptions=False)
        failing_client.cookies.set('nova_session', token)
        assert failing_client.post('/api/ai/generate', json=payload).status_code == 500
    finally:
        event.remove(Draft, 'before_insert', fail_target_insert)
    saved = client.get(f"/api/drafts/{source['id']}").json()
    assert saved['workspace'] == source['workspace'] and saved['revision'] == source['revision']
    assert draft_count(uid) == before


@pytest.mark.parametrize('body', [
    {'source_draft_id':1}, {'source_revision':0},
    {'draft_id':1,'source_draft_id':2,'source_revision':0},
    {'source_draft_id':0,'source_revision':0}, {'source_draft_id':1,'source_revision':-1},
])
def test_source_metadata_requires_a_new_draft_and_complete_revision(body):
    client, *_ = account()
    result = client.post('/api/ai/generate', json={'brief':'Synthetic','platforms':['tiktok'],**body})
    assert result.status_code == 422
