from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import timezone,timedelta

from sqlalchemy import select,update

from .db import Activity, MediaAsset, ScheduledPost, SessionLocal, Publication, PublishReview, Draft, utcnow
from .social import publish_platform
from .publishing_workflow import dispatch,update_draft_status

log = logging.getLogger("nova.scheduler")


def recover_stale_publication(db, item, stale):
    """Recover only the exact stale attempt observed; never race a new checkpoint."""
    previous=item.result_json
    evidence=json.loads(previous or '{}')
    from .tiktok_outcomes import recover_evidence
    recovered=recover_evidence(evidence) if item.platform=='tiktok' else None
    status=recovered or 'unknown'
    if not recovered:evidence['error']='Worker interrupted; check the destination before retrying.'
    claimed=db.execute(update(Publication).where(
        Publication.id==item.id,Publication.status==item.status,
        Publication.status.in_(['publishing','queued']),Publication.review_code==item.review_code,
        Publication.result_json==previous,Publication.updated_at==item.updated_at,
        Publication.updated_at<stale,
    ).values(status=status,result_json=json.dumps(evidence),updated_at=utcnow()).execution_options(synchronize_session=False))
    if claimed.rowcount!=1:
        db.rollback();db.refresh(item);return False
    if status=='failed':
        from .allowances import finish
        finish(db,f'publication:{item.id}',False)
    db.commit();db.refresh(item)
    return True


def process_due(limit: int = 25) -> dict[str, int]:
    published = failed = 0
    with SessionLocal() as db:
        from .db import PendingConnection
        from sqlalchemy import delete
        db.execute(delete(PendingConnection).where(PendingConnection.expires_at<utcnow()))
        # Never automatically resend an uncertain request after a crash.
        stale=utcnow()-timedelta(minutes=15)
        candidates=db.scalars(select(Publication).where(Publication.status.in_(['publishing','queued']),Publication.updated_at<stale)).all()
        stuck=[item for item in candidates if recover_stale_publication(db,item,stale)]
        for job in db.scalars(select(ScheduledPost).where(ScheduledPost.status=='publishing',ScheduledPost.updated_at<stale)).all():
            content=json.loads(job.content_json or '{}')
            item=db.get(Publication,content.get('publication_id')) if content.get('publication_id') else None
            if (item and item.user_id==job.user_id and item.draft_id==job.draft_id
                    and item.platform==job.platform and item.connection_id==job.connection_id
                    and item.review_code==content.get('review_code')
                    and item.status in {'pending','published','failed','unknown'}):
                evidence=json.loads(item.result_json or '{}')
                values={'status':item.status,'error':evidence.get('error'),'platform_post_id':evidence.get('post_id'),'post_url':evidence.get('url')}
            else:
                values={'status':'unknown','error':'Worker interrupted; verify destination.'}
            db.execute(update(ScheduledPost).where(
                ScheduledPost.id==job.id,ScheduledPost.status=='publishing',
                ScheduledPost.updated_at==job.updated_at,ScheduledPost.content_json==job.content_json,
            ).values(**values).execution_options(synchronize_session=False))
        db.commit()
        for item in stuck:update_draft_status(db,item.draft_id)
        # Prioritise pending jobs; old unknown rows without receipts cannot be checked.
        pending=db.scalars(select(Publication).where(Publication.platform=='tiktok',Publication.status=='pending').order_by(Publication.updated_at,Publication.id).limit(limit)).all()
        uncertain=db.scalars(select(Publication).where(
            Publication.platform=='tiktok',Publication.status=='unknown',
            Publication.result_json.contains('"post_id": "'),
            ~Publication.result_json.contains('"post_id": ""'),
        ).order_by(Publication.updated_at,Publication.id).limit(limit)).all()
        pending+=uncertain
        for item in pending:
            try:
                from .tiktok_status import reconcile
                reconcile(db,item)
            except Exception:db.rollback();log.warning('Pending publication could not be checked; it will not be resent')
        rows = db.scalars(
            select(ScheduledPost)
            .where(ScheduledPost.status == "scheduled", ScheduledPost.scheduled_at <= utcnow())
            .order_by(ScheduledPost.scheduled_at.asc())
            .limit(limit)
        ).all()
        for row in rows:
            claimed=db.execute(update(ScheduledPost).where(
                ScheduledPost.id==row.id, ScheduledPost.status=='scheduled',
                ScheduledPost.scheduled_at==row.scheduled_at,
                ScheduledPost.updated_at==row.updated_at,
                ScheduledPost.scheduled_at<=utcnow(),
            ).values(status='publishing',updated_at=utcnow()).execution_options(synchronize_session=False))
            if claimed.rowcount!=1:db.rollback();continue
            db.commit();db.refresh(row)
            try:
                content = json.loads(row.content_json)
                if content.get('publication_id'):
                    item=db.get(Publication,content['publication_id']);review=db.get(PublishReview,content['review_code'])
                    if not item or not review:raise RuntimeError('Missing reviewed publication')
                    dispatch(db,item,json.loads(review.payload_json),publish_platform)
                    db.refresh(item);row.status=item.status
                    result=json.loads(item.result_json or '{}');row.platform_post_id=result.get('post_id');row.post_url=result.get('url');row.error=result.get('error');db.commit()
                    update_draft_status(db,row.draft_id)
                    published+=int(row.status=='published');failed+=int(row.status in {'failed','unknown'})
                    continue
                posts = content.get("posts") or []
                link_url = content.get("link_url") or ""
                publish_options = content.get("publish_options") or {}
                media_ids = json.loads(row.media_asset_ids_json or "[]")
                assets = [db.get(MediaAsset, int(mid)) for mid in media_ids]
                if any(not a or a.user_id!=row.user_id for a in assets):raise RuntimeError("Scheduled media unavailable")
                if not row.connection_id:raise RuntimeError("Scheduled account unavailable; manual review required")
                result = publish_platform(db, user_id=row.user_id, platform=row.platform, posts=posts, assets=assets, link_url=link_url, options=publish_options,connection_id=row.connection_id)
                row.status = "pending" if result.get("pending") else "published"
                row.platform_post_id = result.get("post_id")
                row.post_url = result.get("url")
                db.add(Activity(user_id=row.user_id, brand_id=row.brand_id, draft_id=row.draft_id, platform=row.platform, action="scheduled_publish", status=row.status, text="\n\n".join(posts), platform_post_id=row.platform_post_id, url=row.post_url))
                published += 1
            except Exception as exc:
                log.exception("Scheduled %s post %s failed", row.platform, row.id)
                row.status = "unknown"; row.error = "Publication outcome is unconfirmed. Check the destination before retrying."
                db.add(Activity(user_id=row.user_id, brand_id=row.brand_id, draft_id=row.draft_id, platform=row.platform, action="scheduled_publish", status="unknown", text=row.content_json[:2000], error="Publication could not be confirmed"))
                failed += 1
            db.commit()
    return {"published": published, "failed": failed}


async def loop() -> None:
    interval = max(int(os.environ.get("SCHEDULER_INTERVAL_SECONDS", "60")), 30)
    while True:
        try:
            await asyncio.to_thread(process_due)
        except Exception:
            log.exception("Scheduler loop failed")
        await asyncio.sleep(interval)
