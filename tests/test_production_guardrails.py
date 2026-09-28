import json
import secrets

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from nova.db import Brand, Draft, MediaAsset, Publication, PublishReview, SessionLocal, SocialConnection, User
from nova.password_policy import password_error
from nova.security import hash_password, verify_password
from test_account_integrity import account
from test_reviewed_publication import prepared, review


@pytest.mark.parametrize('password', ['short', 'abcdefghijklmN', 'a' * 15, 'password123456789', 'x' * 257])
def test_new_password_rejects_short_common_and_oversized(password):
    assert password_error(password)


@pytest.mark.parametrize('password', ['three quiet rivers', 'X' * 64 + 'y', 'é' * 255 + 'z'])
def test_long_passwords_and_passphrases_need_no_composition_rule(password):
    assert password_error(password) is None
    assert verify_password(password, hash_password(password))


def test_existing_short_password_can_still_log_in_but_not_be_chosen_again():
    client, uid, _, email = account()
    with SessionLocal() as db:
        db.get(User, uid).password_hash = hash_password('old-short-12')
        db.commit()
    response = client.post('/login', data={'email': email, 'password': 'old-short-12'}, follow_redirects=False)
    assert response.headers['location'] == '/studio'
    response = client.post('/account/password', data={'current_password': 'old-short-12', 'new_password': 'short-again', 'new_password_confirmation': 'short-again'}, follow_redirects=False)
    assert 'error=' in response.headers['location']
    assert client.post('/reset-password', data={'token': 'unused', 'password': 'short-again', 'confirmation': 'short-again'}).status_code == 400
    response = client.post('/signup', data={'name': 'Synthetic', 'country': 'GB', 'email': secrets.token_hex(8)+'@example.test', 'password': 'short-again', 'password_confirmation': 'short-again', 'accept_terms': 'yes'}, follow_redirects=False)
    assert '15' in response.headers['location']
    assert 'minlength="1"' in client.get('/login').text
    assert 'minlength="15"' in client.get('/signup').text


@pytest.mark.parametrize('field', ['user_id', 'brand_id'])
def test_unscoped_worker_cannot_reassign_tenant_ownership(field):
    client, uid, _, body = prepared()
    with SessionLocal() as db:
        row = db.get(Draft, body['draft_id'])
        setattr(row, field, getattr(row, field) + 1)
        with pytest.raises(HTTPException, match='ownership'):
            db.commit()
        db.rollback()
        assert db.get(Draft, body['draft_id']).user_id == uid
        assert db.get(Draft, body['draft_id']).brand_id == 0


def test_worker_rejects_same_owner_different_brand_account():
    from nova.publishing_workflow import dispatch
    client, uid, _, body = prepared()
    approved = review(client, body)
    with SessionLocal() as db:
        brand = Brand(user_id=uid, name='Another workspace')
        db.add(brand); db.flush()
        original = db.scalar(select(SocialConnection).where(SocialConnection.user_id == uid))
        other = SocialConnection(user_id=uid, brand_id=brand.id, platform='x', account_id='another', scope='tweet.write', encrypted_access_token=original.encrypted_access_token)
        db.add(other); db.flush()
        payload = json.loads(db.get(PublishReview, approved['review_token']).payload_json)
        payload['targets']['x'].update(connection_id=other.id, account_id=other.account_id)
        publication = Publication(user_id=uid, brand_id=0, draft_id=body['draft_id'], platform='x', connection_id=other.id, review_code=approved['review_token'], status='queued')
        db.add(publication); db.commit()
        calls=[]
        dispatch(db, publication, payload, lambda *a, **k: calls.append(k))
        assert not calls
        assert publication.status == 'failed'


@pytest.mark.parametrize('route', ['/api/voice/scan-socials', '/api/voice/learn'])
def test_provider_exception_never_reaches_response_or_logs(monkeypatch, caplog, route):
    import nova.app as module
    client, *_ = account()
    secret = 'access_token=never-expose-this-synthetic-token'
    def fail(*args, **kwargs):
        raise RuntimeError(secret)
    monkeypatch.setattr(module, 'learn_voice_from_socials', fail)
    monkeypatch.setattr(module.ai, 'infer_voice_profile', fail)
    response = client.post(route, json={'content': 'A sample of my writing for analysis. ' * 3})
    assert response.status_code == 502
    assert secret not in response.text
    assert secret not in caplog.text
    assert 'unchanged' in response.text


@pytest.mark.parametrize('interrupted_claim', [False, True])
def test_immediate_publish_survives_browser_loss_and_worker_restart(monkeypatch, interrupted_claim):
    from datetime import timedelta
    from nova.db import ScheduledPost, utcnow
    from nova.scheduler import process_due
    client, uid, _, body = prepared()
    approved = review(client, body)
    calls=[]
    monkeypatch.setattr('nova.scheduler.publish_platform', lambda *a, **k: calls.append(k) or {'post_id': 'synthetic-queued'})
    response = client.post('/api/publish', json=approved)
    assert response.status_code == 200
    assert response.json()['results']['x']['status'] == 'queued'
    assert calls == []  # No external I/O in the request.
    client.close()
    with SessionLocal() as db:
        publication = db.scalar(select(Publication).where(Publication.draft_id == body['draft_id']))
        job = db.scalar(select(ScheduledPost).where(ScheduledPost.draft_id == body['draft_id']))
        publication.updated_at = utcnow() - timedelta(hours=1)
        if interrupted_claim:
            job.status = 'publishing'
            job.updated_at = utcnow() - timedelta(hours=1)
        db.commit()
    process_due()
    process_due()
    assert len(calls) == 1
    with SessionLocal() as db:
        assert db.scalar(select(Publication).where(Publication.draft_id == body['draft_id'])).status == 'published'


def test_queued_immediate_job_can_be_cancelled_before_worker_claim(monkeypatch):
    from nova.scheduler import process_due
    client, uid, _, body = prepared()
    approved = review(client, body)
    calls=[]
    monkeypatch.setattr('nova.scheduler.publish_platform', lambda *a, **k: calls.append(k))
    assert client.post('/api/publish', json=approved).status_code == 200
    job = client.get('/api/schedules').json()[0]
    assert client.post(f"/api/schedules/{job['id']}/cancel").status_code == 200
    process_due()
    assert not calls
    assert client.get('/api/publications/'+str(body['draft_id'])).json()['results']['x']['status'] == 'cancelled'


@pytest.mark.parametrize('ledger_state', ['published', 'publishing'])
def test_restart_preserves_provider_evidence_and_never_resends(monkeypatch, ledger_state):
    from datetime import timedelta
    from nova.db import ScheduledPost, utcnow
    from nova.scheduler import process_due
    client, uid, _, body = prepared()
    assert client.post('/api/publish', json=review(client, body)).status_code == 200
    with SessionLocal() as db:
        publication = db.scalar(select(Publication).where(Publication.draft_id == body['draft_id']))
        job = db.scalar(select(ScheduledPost).where(ScheduledPost.draft_id == body['draft_id']))
        publication.status = ledger_state
        publication.result_json = json.dumps({'container_id': 'retained-checkpoint', 'post_id': 'confirmed-id'} if ledger_state == 'published' else {'container_id': 'retained-checkpoint'})
        publication.updated_at = job.updated_at = utcnow() - timedelta(hours=1)
        job.status = 'publishing'
        db.commit()
    calls=[]
    monkeypatch.setattr('nova.scheduler.publish_platform', lambda *a, **k: calls.append(k))
    process_due()
    assert not calls
    with SessionLocal() as db:
        publication = db.scalar(select(Publication).where(Publication.draft_id == body['draft_id']))
        job = db.scalar(select(ScheduledPost).where(ScheduledPost.draft_id == body['draft_id']))
        assert json.loads(publication.result_json)['container_id'] == 'retained-checkpoint'
        assert job.status == ('published' if ledger_state == 'published' else 'unknown')
        if ledger_state == 'published':
            assert job.platform_post_id == 'confirmed-id'
