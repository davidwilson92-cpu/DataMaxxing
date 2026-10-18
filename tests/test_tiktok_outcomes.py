"""Real adapter + ledger recovery with synthetic provider responses only."""
import json
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import select

from nova import social, tiktok_status
from nova.db import Activity, Draft, MediaAsset, Publication, ScheduledPost, SessionLocal, SocialConnection, UsageEntry, utcnow
from nova.tiktok_outcomes import init_rejection
from test_reviewed_publication import prepared
from test_tiktok_direct_post import setup


def reviewed(monkeypatch, inbox=False):
    asset, options, _, info = setup(monkeypatch)
    if inbox:
        monkeypatch.setenv('TIKTOK_SEND_TO_INBOX', 'true')
        options = {'posting_mode': 'inbox'}
    client, uid, _, body = prepared(('tiktok',))
    with SessionLocal() as db:
        conn = db.scalar(select(SocialConnection).where(SocialConnection.user_id == uid))
        conn.scope = 'video.upload' if inbox else 'video.publish'
        media = MediaAsset(user_id=uid, filename='synthetic.mp4', mime_type='video/mp4',
                           storage_key=asset.storage_key, public_url=asset.public_url, size_bytes=20)
        db.add(media); db.commit()
        body['media_asset_ids'] = [media.id]
    body['publish_options'] = {'tiktok': options}
    assert client.patch(f"/api/drafts/{body['draft_id']}", json={
        'platforms': ['tiktok'], 'variants': body['variants'],
        'workspace': {'media_asset_ids': body['media_asset_ids']},
    }).status_code == 200
    response = client.post('/api/publish-review', json=body)
    assert response.status_code == 200, response.text
    return client, body, {**body, 'review_token': response.json()['review_token']}, info


@pytest.mark.parametrize('status,code', [
    (403, 'unaudited_client_can_only_post_to_private_accounts'),
    (200, 'invalid_param'), (401, 'scope_not_authorized'),
    (429, 'rate_limit_exceeded'), (403, 'url_ownership_unverified'),
])
def test_explicit_rejection_is_failed_and_never_automatically_resent(monkeypatch, status, code):
    client, body, approved, _ = reviewed(monkeypatch)
    calls = []
    def reject(url, **kw):
        calls.append(url)
        return httpx.Response(status, json={'error': {
            'code': code, 'message': 'secret-token private-provider-body', 'log_id': 'SAFE_LOG_123',
        }})
    monkeypatch.setattr(social.httpx, 'post', reject)
    result = client.post('/api/publish', json=approved).json()['results']['tiktok']
    assert result['status'] == 'failed'
    assert result['provider_error_code'] == code and result['provider_log_id'] == 'SAFE_LOG_123'
    assert 'secret-token' not in json.dumps(result) and 'private-provider-body' not in json.dumps(result)
    assert 'unconfirmed' not in result['error']
    client.post('/api/publish', json=approved)
    client.get(f"/api/publications/{body['draft_id']}")
    assert len(calls) == 1
    with SessionLocal() as db:
        row = db.scalar(select(Publication).where(Publication.draft_id == body['draft_id']))
        assert db.get(UsageEntry, f'publication:{row.id}').state == 'released'
    # A new explicit review is possible; merely opening it does not send anything.
    assert client.post('/api/publish-review', json=body).status_code == 200
    assert len(calls) == 1


@pytest.mark.parametrize('mode', ['timeout', 'server_error', 'html', 'no_receipt', 'unknown_code', 'contradiction'])
def test_ambiguous_init_remains_unknown_and_locked(monkeypatch, mode):
    client, body, approved, _ = reviewed(monkeypatch)
    calls = []
    def uncertain(url, **kw):
        calls.append(url)
        if mode == 'timeout':
            raise httpx.ReadTimeout('secret-token')
        if mode == 'server_error':
            return httpx.Response(503, json={'error': {'code': 'invalid_param'}})
        if mode == 'html':
            return httpx.Response(502, text='private-provider-body')
        if mode == 'unknown_code':
            return httpx.Response(400, json={'error': {'code': 'undocumented_error'}})
        if mode == 'contradiction':
            return httpx.Response(403, json={'data': {'publish_id': 'ambiguous'}, 'error': {'code': 'invalid_param'}})
        return httpx.Response(200, json={'data': {}, 'error': {'code': 'ok'}})
    monkeypatch.setattr(social.httpx, 'post', uncertain)
    result = client.post('/api/publish', json=approved).json()['results']['tiktok']
    assert result['status'] == 'unknown' and 'unconfirmed' in result['error']
    assert 'secret-token' not in json.dumps(result)
    assert client.post('/api/publish-review', json=body).status_code == 409
    client.post('/api/publish', json=approved)
    assert len(calls) == 1


def test_changed_creator_settings_fail_before_sending(monkeypatch):
    client, _, approved, info = reviewed(monkeypatch)
    info['privacy_level_options'] = ['SELF_ONLY']
    calls = []
    monkeypatch.setattr(social.httpx, 'post', lambda *a, **kw: calls.append(kw))
    result = client.post('/api/publish', json=approved).json()['results']['tiktok']
    assert result['status'] == 'failed' and 'no post was sent' in result['error']
    assert calls == []


def test_upload_failure_keeps_accepted_receipt_and_reconciles_without_resend(monkeypatch):
    client, body, approved, _ = reviewed(monkeypatch, inbox=True)
    calls = []
    monkeypatch.setattr(social.httpx, 'post', lambda url, **kw: calls.append(url) or httpx.Response(200, json={
        'data': {'publish_id': 'accepted-inbox', 'upload_url': 'https://example.test/upload'}, 'error': {'code': 'ok'},
    }))
    def broken_upload(*a, **kw):
        raise httpx.ReadTimeout('synthetic interrupted upload')
    monkeypatch.setattr(social.httpx, 'put', broken_upload)
    result = client.post('/api/publish', json=approved).json()['results']['tiktok']
    assert result['status'] == 'pending' and result['post_id'] == 'accepted-inbox'
    assert result['requires_tiktok_completion'] and 'error' not in result
    checks = []
    monkeypatch.setattr(tiktok_status, 'resolve_tiktok_post', lambda *a: checks.append(a[-1]) or {'status': 'FAILED'})
    result = client.get(f"/api/publications/{body['draft_id']}").json()['results']['tiktok']
    assert result['status'] == 'failed'
    assert checks == ['accepted-inbox'] and len(calls) == 1


def test_interrupted_worker_preserves_receipt_and_only_checks_status(monkeypatch):
    from nova import scheduler
    client, body, approved, _ = reviewed(monkeypatch)
    with SessionLocal() as db:
        conn = db.scalar(select(SocialConnection).where(SocialConnection.account_id == 'original-tiktok').order_by(SocialConnection.id.desc()))
        row = Publication(user_id=conn.user_id, draft_id=body['draft_id'], platform='tiktok',
            connection_id=conn.id, review_code=approved['review_token'], status='publishing',
            updated_at=utcnow()-timedelta(minutes=20), result_json=json.dumps({
                'phase': 'tiktok_accepted', 'post_id': 'durable-receipt', 'privacy_level': 'SELF_ONLY', 'posting_mode': 'direct',
            }))
        db.add(row); db.commit()
    checks = []
    monkeypatch.setattr(tiktok_status, 'resolve_tiktok_post', lambda *a: checks.append(a[-1]) or {'status': 'PUBLISH_COMPLETE'})
    monkeypatch.setattr(scheduler, 'publish_platform', lambda *a, **kw: pytest.fail('Recovery must never resend'))
    scheduler.process_due(limit=500)
    result = client.get(f"/api/publications/{body['draft_id']}").json()['results']['tiktok']
    assert result['status'] == 'published' and result['post_id'] == 'durable-receipt'
    assert 'durable-receipt' in checks and 'error' not in result and not result.get('url')


def test_legacy_unknown_without_evidence_remains_locked(monkeypatch):
    client, body, approved, _ = reviewed(monkeypatch)
    with SessionLocal() as db:
        conn = db.scalar(select(SocialConnection).where(SocialConnection.account_id == 'original-tiktok').order_by(SocialConnection.id.desc()))
        db.add(Publication(user_id=conn.user_id, draft_id=body['draft_id'], platform='tiktok',
            connection_id=conn.id, review_code=approved['review_token'], status='unknown',
            result_json=json.dumps({'error': 'Previous outcome unconfirmed.'})))
        db.commit()
    monkeypatch.setattr(tiktok_status, 'resolve_tiktok_post', lambda *a: pytest.fail('No receipt to poll'))
    assert client.get(f"/api/publications/{body['draft_id']}").json()['results']['tiktok']['status'] == 'unknown'
    assert client.post('/api/publish-review', json=body).status_code == 409


def test_rejection_metadata_has_no_raw_message_or_untrusted_log_id():
    evidence = init_rejection(403, {'error': {'code': 'invalid_param', 'log_id': 'secret token https://url', 'message': 'do not store'}})
    assert evidence == {'provider_error_code': 'invalid_param'}
    assert init_rejection(200, {'error': {'code': {'unexpected': 'object'}}}) is None


@pytest.mark.parametrize('reason,expected', [
    ('video_pull_failed', 'could not download'),
    ('spam_risk_text', 'do not resend'),
    ('auth_removed', 'access was removed'),
    ('private-provider-body', 'reported this publication failed'),
])
def test_confirmed_failed_status_explains_only_known_reasons(monkeypatch, reason, expected):
    from test_tiktok_results import pending
    client, draft, _ = pending()
    monkeypatch.setattr(tiktok_status, 'resolve_tiktok_post', lambda *a: {'status': 'FAILED', 'fail_reason': reason})
    result = client.get(f'/api/publications/{draft}').json()['results']['tiktok']
    assert result['status'] == 'failed' and result['pending'] is False
    assert expected in result['error']
    assert 'private-provider-body' not in json.dumps(result)
    if reason != 'private-provider-body':
        assert result['provider_error_code'] == reason


def test_unknown_with_receipt_can_only_reconcile_not_resend(monkeypatch):
    from test_tiktok_results import pending
    client, draft, row_id = pending()
    with SessionLocal() as db:
        row = db.get(Publication, row_id)
        row.status = 'unknown'
        stored = json.loads(row.result_json)
        stored['error'] = 'Interrupted after receipt.'
        row.result_json = json.dumps(stored); db.commit()
    checks = []
    monkeypatch.setattr(tiktok_status, 'resolve_tiktok_post', lambda *a: checks.append(a[-1]) or {'status': 'PUBLISH_COMPLETE'})
    result = client.get(f'/api/publications/{draft}').json()['results']['tiktok']
    assert result['status'] == 'published' and 'error' not in result
    assert checks == ['receipt-only']


def test_late_provider_state_does_not_downgrade_confirmed_publication(monkeypatch):
    from test_tiktok_results import pending
    client, draft, row_id = pending()
    with SessionLocal() as db:
        row = db.get(Publication, row_id); row.status = 'published'; db.commit()
    monkeypatch.setattr(tiktok_status, 'resolve_tiktok_post', lambda *a: {'status': 'SEND_TO_USER_INBOX'})
    result = client.get(f'/api/publications/{draft}').json()['results']['tiktok']
    assert result['status'] == 'published' and not result.get('requires_tiktok_completion')


def test_status_error_envelope_cannot_report_success(monkeypatch):
    monkeypatch.setattr(social, 'access_token', lambda *a: 'synthetic')
    monkeypatch.setattr(social.httpx, 'post', lambda *a, **kw: httpx.Response(200, json={
        'error': {'code': 'access_token_invalid'}, 'data': {'status': 'PUBLISH_COMPLETE'},
    }))
    assert social.resolve_tiktok_post(None, None, 'synthetic-receipt') == {'status': 'unknown'}


def test_unknown_without_receipts_cannot_starve_pending_worker_checks(monkeypatch):
    from nova import scheduler
    from test_tiktok_results import pending
    client, draft, row_id = pending()
    with SessionLocal() as db:
        current = db.get(Publication, row_id)
        current.updated_at = utcnow()-timedelta(days=1)
        for _ in range(30):
            old = Draft(user_id=current.user_id); db.add(old); db.flush()
            db.add(Publication(user_id=current.user_id, draft_id=old.id, platform='tiktok',
                connection_id=current.connection_id, review_code='synthetic', status='unknown',
                updated_at=utcnow()-timedelta(days=2), result_json='{}'))
        db.commit()
    checks = []
    monkeypatch.setattr(tiktok_status, 'resolve_tiktok_post', lambda *a: checks.append(a[-1]) or {'status': 'PUBLISH_COMPLETE'})
    scheduler.process_due(limit=1)
    with SessionLocal() as db:
        assert db.get(Publication, row_id).status == 'published'
    assert checks == ['receipt-only']


def test_worker_syncs_confirmed_rejection_to_exact_scheduled_job(monkeypatch):
    from nova import scheduler
    client, body, approved, _ = reviewed(monkeypatch)
    with SessionLocal() as db:
        conn = db.scalar(select(SocialConnection).where(SocialConnection.account_id == 'original-tiktok').order_by(SocialConnection.id.desc()))
        item = Publication(user_id=conn.user_id, draft_id=body['draft_id'], platform='tiktok', connection_id=conn.id,
            review_code=approved['review_token'], status='publishing', updated_at=utcnow()-timedelta(minutes=20),
            result_json=json.dumps({'phase': 'tiktok_rejected', 'provider_error_code': 'invalid_param'}))
        db.add(item); db.flush()
        job = ScheduledPost(user_id=conn.user_id, draft_id=item.draft_id, platform='tiktok', connection_id=conn.id,
            content_json=json.dumps({'publication_id': item.id, 'review_code': item.review_code}),
            status='publishing', scheduled_at=utcnow()-timedelta(minutes=30), updated_at=utcnow()-timedelta(minutes=20))
        db.add(job); db.commit(); job_id = job.id
    monkeypatch.setattr(scheduler, 'publish_platform', lambda *a, **kw: pytest.fail('Must not resend'))
    scheduler.process_due()
    with SessionLocal() as db:
        job = db.get(ScheduledPost, job_id)
        assert job.status == 'failed' and 'rejected the post settings' in job.error


def test_slow_status_result_cannot_replace_a_new_receipt(monkeypatch):
    from test_tiktok_results import pending
    client, draft, row_id = pending()
    def late_result(*args):
        # A different status poll resolved failure and the owner reviewed a new try.
        with SessionLocal() as db:
            row = db.get(Publication, row_id)
            row.status = 'pending'
            row.result_json = json.dumps({'post_id': 'new-reviewed-receipt', 'pending': True})
            db.commit()
        return {'status': 'PUBLISH_COMPLETE', 'public_ids': ['1234567890123456789']}
    monkeypatch.setattr(tiktok_status, 'resolve_tiktok_post', late_result)
    result = client.get(f'/api/publications/{draft}').json()['results']['tiktok']
    assert result['status'] == 'pending' and result['post_id'] == 'new-reviewed-receipt'
    assert not result.get('url')


def replace_attempt(draft):
    with SessionLocal() as db:
        row = db.scalar(select(Publication).where(Publication.draft_id == draft))
        row.status = 'pending'; row.review_code = 'newly-reviewed-attempt'
        row.result_json = json.dumps({'post_id': 'new-attempt-receipt', 'pending': True})
        usage = db.get(UsageEntry, f'publication:{row.id}')
        usage.state = 'reserved'
        db.commit()


def assert_new_attempt_untouched(draft, result):
    assert result['status'] == 'pending' and result['post_id'] == 'new-attempt-receipt'
    with SessionLocal() as db:
        row = db.scalar(select(Publication).where(Publication.draft_id == draft))
        assert row.review_code == 'newly-reviewed-attempt'
        assert db.get(UsageEntry, f'publication:{row.id}').state == 'reserved'
        assert not db.scalar(select(Activity).where(Activity.draft_id == draft, Activity.action == 'publish'))


def test_paused_validation_worker_cannot_send_after_recovery_and_new_review(monkeypatch):
    client, body, approved, info = reviewed(monkeypatch)
    calls = []
    def resumed_creator(*args):
        replace_attempt(body['draft_id'])
        return info
    monkeypatch.setattr(social, '_tiktok_creator_info', resumed_creator)
    monkeypatch.setattr(social.httpx, 'post', lambda *a, **kw: calls.append(kw))
    result = client.post('/api/publish', json=approved).json()['results']['tiktok']
    assert_new_attempt_untouched(body['draft_id'], result)
    assert calls == []


@pytest.mark.parametrize('failure', [False, True])
def test_old_dispatch_completion_cannot_overwrite_new_review(monkeypatch, failure):
    import nova.app as app_module
    from nova.publication_evidence import checkpoint
    client, body, approved, _ = reviewed(monkeypatch)
    def old_dispatch(*args, **kwargs):
        checkpoint('tiktok_accepted', post_id='old-attempt-receipt')
        replace_attempt(body['draft_id'])
        if failure:
            raise RuntimeError('Old worker failed after replacement')
        return {'post_id': 'old-attempt-receipt', 'pending': True}
    monkeypatch.setattr(app_module, 'publish_platform', old_dispatch)
    result = client.post('/api/publish', json=approved).json()['results']['tiktok']
    assert_new_attempt_untouched(body['draft_id'], result)


def test_stale_recovery_cannot_overwrite_checkpoint_that_started_sending(monkeypatch):
    from nova import scheduler
    client, body, approved, _ = reviewed(monkeypatch)
    with SessionLocal() as db:
        conn = db.scalar(select(SocialConnection).where(SocialConnection.account_id == 'original-tiktok').order_by(SocialConnection.id.desc()))
        item = Publication(user_id=conn.user_id, draft_id=body['draft_id'], platform='tiktok', connection_id=conn.id,
            review_code=approved['review_token'], status='publishing', updated_at=utcnow()-timedelta(minutes=20),
            result_json=json.dumps({'phase': 'tiktok_validating'}))
        db.add(item); db.commit(); item_id = item.id
        # Scheduler has its stale snapshot, but the live worker advances first.
        with SessionLocal() as live_db:
            live = live_db.get(Publication, item_id)
            live.result_json = json.dumps({'phase': 'tiktok_publish_requested'})
            live.updated_at = utcnow(); live_db.commit()
        assert scheduler.recover_stale_publication(db, item, utcnow()-timedelta(minutes=15)) is False
        db.refresh(item)
        assert item.status == 'publishing'
        assert json.loads(item.result_json)['phase'] == 'tiktok_publish_requested'
