"""Unscoped workers must enforce the same ownership boundary as web requests."""
import json

import pytest
from sqlalchemy import select

from nova.db import Brand, Draft, MediaAsset, ScheduledPost, SessionLocal, SocialConnection, utcnow
from nova.scheduler import process_due
from test_reviewed_publication import prepared
from test_account_integrity import account


@pytest.mark.parametrize('mismatch', ['connection', 'media', 'draft', 'permission',
                                    'other_owner', 'inactive', 'wrong_platform',
                                    'missing_connection', 'bad_media_id', 'none'])
def test_old_schedule_checks_every_resource_before_provider_call(monkeypatch, mismatch):
    _, uid, _, body = prepared()
    owner = account()[1] if mismatch == 'other_owner' else uid
    with SessionLocal() as db:
        other_brand = Brand(user_id=uid, name='Other worker boundary brand')
        db.add(other_brand); db.flush()
        original = db.scalar(select(SocialConnection).where(SocialConnection.user_id == uid))
        conn = SocialConnection(user_id=owner, brand_id=other_brand.id if mismatch == 'connection' else 0,
                                platform='facebook' if mismatch == 'wrong_platform' else 'x',
                                active=mismatch != 'inactive', account_id='worker-test',
                                scope='tweet.read' if mismatch == 'permission' else 'tweet.write',
                                encrypted_access_token=original.encrypted_access_token)
        asset = MediaAsset(user_id=uid, brand_id=other_brand.id if mismatch == 'media' else 0,
                           filename='synthetic.jpg', mime_type='image/jpeg', storage_key='synthetic')
        db.add_all([conn, asset]); db.flush()
        draft_id = body['draft_id']
        if mismatch == 'draft':
            draft = Draft(user_id=uid, brand_id=other_brand.id)
            db.add(draft); db.flush(); draft_id = draft.id
        job = ScheduledPost(user_id=uid, brand_id=0, draft_id=draft_id,
                            platform='x', connection_id=None if mismatch == 'missing_connection' else conn.id,
                            content_json=json.dumps({'posts': ['Approved synthetic post']}),
                            media_asset_ids_json=json.dumps([str(asset.id) if mismatch == 'bad_media_id' else asset.id]), scheduled_at=utcnow())
        db.add(job); db.commit(); job_id = job.id
    calls = []
    monkeypatch.setattr('nova.scheduler.publish_platform',
                        lambda *a, **k: calls.append(k) or {'post_id': 'synthetic'})
    process_due(); process_due()
    with SessionLocal() as db:
        job = db.get(ScheduledPost, job_id)
        if mismatch == 'none':
            assert len(calls) == 1
            assert job.status == 'published'
        else:
            assert calls == []
            assert job.status == 'failed'
            assert 'review' in job.error.lower()


def test_valid_old_job_with_ambiguous_send_is_never_retried(monkeypatch):
    _, uid, _, body = prepared()
    with SessionLocal() as db:
        conn = db.scalar(select(SocialConnection).where(SocialConnection.user_id == uid))
        # Pre-ledger jobs may not have a draft. Preserve support for those records.
        job = ScheduledPost(user_id=uid, platform='x', connection_id=conn.id,
                            content_json=json.dumps({'posts': ['Synthetic timeout']}),
                            scheduled_at=utcnow())
        db.add(job); db.commit(); job_id = job.id
    calls = []
    def uncertain(*args, **kwargs):
        calls.append(kwargs)
        raise TimeoutError('synthetic-secret-must-not-leak')
    monkeypatch.setattr('nova.scheduler.publish_platform', uncertain)
    process_due(); process_due()
    with SessionLocal() as db:
        row = db.get(ScheduledPost, job_id)
        assert len(calls) == 1
        assert row.status == 'unknown'
        assert 'synthetic-secret' not in row.error
