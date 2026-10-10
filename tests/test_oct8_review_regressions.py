"""Synthetic adversarial checks for October UX/reliability acceptance."""
from datetime import timedelta
import pytest
from sqlalchemy import select
from sqlalchemy.sql.dml import Update
from test_reviewed_publication import prepared, review
from nova.db import SessionLocal, ScheduledPost, Publication, utcnow
from nova import scheduler


@pytest.mark.parametrize("change", ["reschedule", "cancel"])
def test_schedule_change_after_due_scan_wins_before_worker_claim(monkeypatch, change):
    client, _, _, body = prepared()
    future = (utcnow()+timedelta(days=1)).isoformat()
    body['scheduled_local'] = future
    assert client.post('/api/schedule', json=review(client, body)).status_code == 200
    with SessionLocal() as db:
        row = db.scalar(select(ScheduledPost).where(ScheduledPost.draft_id == body['draft_id']))
        row.scheduled_at = utcnow()-timedelta(minutes=1)
        db.commit(); job_id = row.id
    calls = []
    monkeypatch.setattr(scheduler, 'publish_platform', lambda *a, **kw: calls.append(kw) or {'post_id':'synthetic'})
    intercepted = []
    def worker_session():
        db = SessionLocal()
        original = db.execute
        def execute(statement, *args, **kwargs):
            if (not intercepted and isinstance(statement, Update)
                and statement.table.name == ScheduledPost.__tablename__
                and statement.compile().params.get('status') == 'publishing'):
                intercepted.append(True)
                response = client.post(f'/api/schedules/{job_id}/{change}',
                    json={'scheduled_local':future} if change == 'reschedule' else None)
                assert response.status_code == 200, response.text
            return original(statement, *args, **kwargs)
        db.execute = execute
        return db
    monkeypatch.setattr(scheduler, 'SessionLocal', worker_session)
    scheduler.process_due()
    assert intercepted and calls == []
    with SessionLocal() as db:
        row = db.get(ScheduledPost, job_id)
        assert row.status == ('scheduled' if change == 'reschedule' else 'cancelled')
        publication = db.scalar(select(Publication).where(Publication.draft_id == body['draft_id']))
        assert publication.status == row.status
