import json
import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text, update

from nova.app import app
from nova.db import Creator, LegacyPublication, SessionLocal, engine, utcnow
from nova.legacy_queue import process_legacy
from nova.security import encrypt, hash_api_key


@pytest.fixture(autouse=True)
def settle_synthetic_jobs():
    yield
    with SessionLocal() as db:
        # Keep ledger content for the CI backup/restore comparison; no test job
        # may unexpectedly contact a provider in a later scheduler test.
        db.execute(update(LegacyPublication).where(LegacyPublication.status.in_(['queued','publishing']))
                   .values(status='cancelled')); db.commit()


def account():
    key = secrets.token_hex(20)
    with SessionLocal() as db:
        row = Creator(name='Synthetic', x_username='test_' + secrets.token_hex(8),
                      api_key_hash=hash_api_key(key), encrypted_x_api_key=encrypt('key'),
                      encrypted_x_api_secret=encrypt('secret'), encrypted_x_access_token=encrypt('access'),
                      encrypted_x_access_token_secret=encrypt('access-secret'))
        db.add(row); db.commit()
        return TestClient(app), row.id, {'Authorization': 'Bearer ' + key}


def submit(client, headers, key=None, content='Approved synthetic post'):
    return client.post('/x/post', headers=headers, json={'text': content, 'approved': True,
                       'idempotency_key': key or secrets.token_hex(16)})


def test_http_only_enqueues_and_duplicate_returns_same_job(monkeypatch):
    import nova.app as module
    monkeypatch.setattr(module, 'publish_legacy_creator', lambda *args: pytest.fail('HTTP sent to provider'))
    client, _, headers = account()
    key = secrets.token_hex(16)
    first = submit(client, headers, key)
    assert first.status_code == 202
    assert first.json()['status'] == 'queued'
    assert first.json()['success'] is False
    assert submit(client, headers, key).json()['job_id'] == first.json()['job_id']
    assert submit(client, headers, key, 'Different content').status_code == 409
    calls = []
    process_legacy(publisher=lambda *args: calls.append(args[0]) or {'post_id': '123', 'url': 'https://x.com/test/status/123'})
    process_legacy(publisher=lambda *args: pytest.fail('Duplicate external send'))
    assert calls == ['Approved synthetic post']
    status = client.get(first.json()['status_url'], headers=headers).json()
    assert status['status'] == 'published'
    assert status['post_id'] == '123'
    assert submit(client, headers, key).json()['status'] == 'published'


def test_missing_approval_and_key_are_rejected():
    client, _, headers = account()
    assert client.post('/x/post', headers=headers, json={'text': 'post', 'approved': True}).status_code == 400
    assert client.post('/x/post', headers=headers, json={'text': 'post', 'idempotency_key': secrets.token_hex(16)}).status_code == 400
    assert client.post('/x/post', json={'text': 'post'}).status_code == 401


def test_other_creator_cannot_read_job_and_key_is_scoped():
    client, _, headers = account()
    other, _, other_headers = account()
    key = secrets.token_hex(16)
    first = submit(client, headers, key).json()
    second = submit(other, other_headers, key).json()
    assert first['job_id'] != second['job_id']
    assert other.get(first['status_url'], headers=other_headers).status_code == 404
    assert client.get(first['status_url']).status_code == 401


@pytest.mark.parametrize('field,value', [('active', False), ('x_username', 'changed_account'),
                                        ('api_key_hash', 'revoked'), ('encrypted_x_access_token', 'changed')])
def test_worker_rechecks_approval_authority(field, value):
    client, uid, headers = account()
    job_id = submit(client, headers).json()['job_id']
    with SessionLocal() as db:
        setattr(db.get(Creator, uid), field, value); db.commit()
    calls = []
    process_legacy(publisher=lambda content, creator, db: calls.append(creator.id) or {'post_id': 'other'})
    assert uid not in calls
    with SessionLocal() as db:
        assert db.get(LegacyPublication, job_id).status == 'failed'


def test_timeout_and_stale_claim_are_not_replayed(caplog):
    client, uid, headers = account()
    first = submit(client, headers).json()['job_id']
    def timeout(content, creator, db):
        raise TimeoutError('access_token=SYNTHETIC-DO-NOT-EXPOSE')
    process_legacy(publisher=timeout)
    second = submit(client, headers).json()['job_id']
    with SessionLocal() as db:
        row = db.get(LegacyPublication, second)
        row.status = 'publishing'; row.updated_at = utcnow() - timedelta(minutes=16); db.commit()
    process_legacy(publisher=lambda *args: pytest.fail('Uncertain job resent'))
    for job_id in (first, second):
        result = client.get('/x/jobs/' + job_id, headers=headers)
        assert result.json()['status'] == 'unknown'
        assert 'SYNTHETIC-DO-NOT-EXPOSE' not in result.text
    assert 'SYNTHETIC-DO-NOT-EXPOSE' not in caplog.text


def test_concurrent_submissions_and_workers_send_once():
    client, uid, headers = account()
    key = secrets.token_hex(16)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: submit(TestClient(app), headers, key), range(4)))
    assert all(r.status_code == 202 for r in results)
    assert len({r.json()['job_id'] for r in results}) == 1
    calls = []
    def publish(content, creator, db):
        calls.append(creator.id)
        return {'post_id': 'once'}
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: process_legacy(publisher=publish), range(2)))
    assert calls.count(uid) == 1


def test_queue_migration_is_repeatable_and_preserves_jobs():
    from nova.migrations import run_legacy_queue_migration
    client, uid, headers = account()
    job_id = submit(client, headers).json()['job_id']
    run_legacy_queue_migration(engine, LegacyPublication.__table__)
    run_legacy_queue_migration(engine, LegacyPublication.__table__)
    with SessionLocal() as db:
        assert db.get(LegacyPublication, job_id).creator_id == uid
        assert db.execute(text("SELECT COUNT(*) FROM zova_schema_migrations WHERE version='20260929_legacy_publication_queue'")).scalar() == 1


def test_cancel_is_owner_scoped_and_cannot_recall_claimed_job():
    client, _, headers = account()
    other, _, other_headers = account()
    job = submit(client, headers).json()
    url = job['status_url'] + '/cancel'
    assert other.post(url, headers=other_headers).status_code == 404
    assert client.post(url, headers=headers).json()['status'] == 'cancelled'
    assert client.post(url, headers=headers).json()['status'] == 'cancelled'
    process_legacy(publisher=lambda *args: pytest.fail('Cancelled job sent'))
    with SessionLocal() as db:
        row = db.get(LegacyPublication, job['job_id'])
        row.status = 'publishing'; db.commit()
    assert client.post(url, headers=headers).status_code == 409


def test_approved_content_is_immutable_and_ops_are_content_free(monkeypatch):
    from fastapi import HTTPException
    client, _, headers = account()
    job = submit(client, headers, content='Private content should not appear in operations').json()
    with SessionLocal() as db:
        row = db.get(LegacyPublication, job['job_id'])
        row.text = 'Changed without approval'
        with pytest.raises(HTTPException): db.commit()
        db.rollback()
        row = db.get(LegacyPublication, job['job_id'])
        row.status = 'unknown'; db.commit()
    monkeypatch.setenv('SCHEDULER_SECRET', 'synthetic-operations')
    assert client.get('/internal/status').status_code == 401
    response = client.get('/internal/status', headers={'Authorization': 'Bearer synthetic-operations'})
    assert response.json()['legacy_unknown_jobs'] >= 1
    assert response.json()['status'] == 'attention'
    assert 'Private content' not in response.text
