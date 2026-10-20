"""Local disconnection: stop unsent work without rewriting provider outcomes."""
import json
from sqlalchemy import select, update
from . import allowances
from .db import Activity, Draft, Publication, PublishReview, ScheduledPost, utcnow


def unlink_local(db, connection):
    uid, cid = connection.user_id, connection.id
    connection.active = False
    connection.encrypted_access_token = ''
    connection.encrypted_refresh_token = None
    draft_ids = set()
    jobs = db.scalars(select(ScheduledPost).where(
        ScheduledPost.user_id == uid, ScheduledPost.connection_id == cid,
        ScheduledPost.status == 'scheduled',
    )).all()
    for job in jobs:
        changed = db.execute(update(ScheduledPost).where(
            ScheduledPost.id == job.id, ScheduledPost.status == 'scheduled',
        ).values(status='cancelled', updated_at=utcnow()).execution_options(synchronize_session=False))
        if changed.rowcount and job.draft_id: draft_ids.add(job.draft_id)
    publications = db.scalars(select(Publication).where(
        Publication.user_id == uid, Publication.connection_id == cid,
        Publication.status.in_(['queued', 'scheduled']),
    )).all()
    for publication in publications:
        changed = db.execute(update(Publication).where(
            Publication.id == publication.id,
            Publication.status.in_(['queued', 'scheduled']),
        ).values(status='cancelled', updated_at=utcnow()).execution_options(synchronize_session=False))
        if changed.rowcount:
            allowances.finish(db, f'publication:{publication.id}', False)
            draft_ids.add(publication.draft_id)
    # Reconnecting the same destination must not revive an older unused approval.
    for review in db.scalars(select(PublishReview).where(
        PublishReview.user_id == uid, PublishReview.status == 'review',
        PublishReview.expires_at > utcnow(),
    )).all():
        try:
            targets = json.loads(review.payload_json)['targets']
            affected = any(target['connection_id'] == cid for target in targets.values())
        except (ValueError, KeyError, TypeError, AttributeError):
            affected = True  # An invalid review must not prevent disconnection.
        if affected:
            db.execute(update(PublishReview).where(
                PublishReview.code == review.code, PublishReview.status == 'review',
            ).values(status='cancelled').execution_options(synchronize_session=False))
    db.add(Activity(user_id=uid, brand_id=connection.brand_id,
                    platform=connection.platform, action='unlink', status='local_disconnected'))
    db.commit()
    db.expire_all()
    from .publishing_workflow import update_draft_status
    for draft_id in draft_ids:
        if db.scalar(select(Publication.id).where(Publication.draft_id == draft_id)):
            update_draft_status(db, draft_id)
        elif not db.scalar(select(ScheduledPost.id).where(
            ScheduledPost.draft_id == draft_id, ScheduledPost.status != 'cancelled',
        )):
            draft = db.get(Draft, draft_id)
            if draft and draft.status == 'scheduled':
                draft.status = 'cancelled'
                db.commit()
