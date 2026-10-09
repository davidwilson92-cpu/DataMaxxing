from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import timezone,timedelta

from sqlalchemy import select,update

from .db import Activity, MediaAsset, ScheduledPost, SessionLocal, Publication, PublishReview, Draft, utcnow
from .social import publish_platform,resolve_tiktok_post,selected_connection
from .publishing_workflow import capability_error,dispatch,update_draft_status,publication_connection

log = logging.getLogger("nova.scheduler")


class SchedulePreflightError(RuntimeError):
    """A scheduled job was rejected before any external publishing call."""


def scheduled_assets(db, job):
    """Legacy jobs have no review ledger; validate their exact persisted boundary."""
    try:
        if not job.connection_id:
            raise RuntimeError('Missing connection')
        conn = selected_connection(db, job.user_id, job.platform, job.connection_id)
        if (conn.user_id, conn.brand_id) != (job.user_id, job.brand_id):
            raise RuntimeError('Connection boundary mismatch')
        if job.draft_id is not None:
            draft = db.get(Draft, job.draft_id)
            if not draft or (draft.user_id, draft.brand_id) != (job.user_id, job.brand_id):
                raise RuntimeError('Draft boundary mismatch')
        ids = json.loads(job.media_asset_ids_json or '[]')
        if not isinstance(ids, list) or any(type(mid) is not int for mid in ids):
            raise ValueError('Invalid media references')
        assets = [db.get(MediaAsset, mid) for mid in ids]
        if any(not asset or (asset.user_id, asset.brand_id) != (job.user_id, job.brand_id) for asset in assets):
            raise RuntimeError('Media boundary mismatch')
        if capability_error(conn, assets):
            raise RuntimeError('Publishing permission unavailable')
        return assets
    except (RuntimeError, ValueError, TypeError):
        raise SchedulePreflightError('The scheduled account, draft, media or permissions are unavailable. Review before retrying.') from None


def process_due(limit: int = 25) -> dict[str, int]:
    from .legacy_queue import process_legacy
    legacy_counts = process_legacy(limit)
    published, failed = legacy_counts['published'], legacy_counts['failed']
    with SessionLocal() as db:
        from .db import PendingConnection
        from sqlalchemy import delete
        db.execute(delete(PendingConnection).where(PendingConnection.expires_at<utcnow()))
        # Never automatically resend an uncertain request after a crash.
        stale=utcnow()-timedelta(minutes=15)
        stuck=db.scalars(select(Publication).where(Publication.status=='publishing',Publication.updated_at<stale)).all()
        for item in stuck:
            evidence=json.loads(item.result_json or '{}')
            evidence['error']='Worker interrupted; check the destination before retrying.'
            db.execute(update(Publication).where(
                Publication.id==item.id,Publication.status=='publishing',Publication.updated_at==item.updated_at
            ).values(status='unknown',result_json=json.dumps(evidence)).execution_options(synchronize_session=False))
        db.commit();db.expire_all()
        interrupted=db.scalars(select(ScheduledPost).where(ScheduledPost.status=='publishing',ScheduledPost.updated_at<stale)).all()
        for job in interrupted:
            content=json.loads(job.content_json or '{}')
            item=db.get(Publication,content.get('publication_id')) if content.get('publication_id') else None
            linked=(item and
                    (item.user_id,item.brand_id,item.draft_id,item.connection_id,item.platform)==
                    (job.user_id,job.brand_id,job.draft_id,job.connection_id,job.platform))
            values={'status':'unknown','error':'Worker interrupted; verify destination.'}
            if linked and item.status in {'queued','scheduled'}:
                # The external-send claim never happened: this job is safe to reclaim.
                values={'status':'scheduled','error':None}
            elif linked and item.status in {'published','pending','failed','cancelled'}:
                # The ledger committed before the worker could update the job row.
                result=json.loads(item.result_json or '{}')
                values={'status':item.status,'error':result.get('error'),
                        'platform_post_id':result.get('post_id'),'post_url':result.get('url')}
            db.execute(update(ScheduledPost).where(
                ScheduledPost.id==job.id,ScheduledPost.status=='publishing',ScheduledPost.updated_at==job.updated_at
            ).values(**values).execution_options(synchronize_session=False))
        db.commit()
        for item in stuck:update_draft_status(db,item.draft_id)
        pending=db.scalars(select(Publication).where(Publication.platform=='tiktok',Publication.status=='pending').limit(limit)).all()
        for item in pending:
            try:
                stored=json.loads(item.result_json);conn=publication_connection(db,item)
                state=resolve_tiktok_post(db,conn,stored['post_id']);remote=str(state.get('status','')).upper()
                if remote=='PUBLISH_COMPLETE':
                    item.status='published';stored['pending']=False
                    if state.get('public_ids'):stored['url']='https://www.tiktok.com/@'+conn.username+'/video/'+str(state['public_ids'][0])
                elif remote=='FAILED':
                    from .allowances import finish
                    item.status='failed';stored['error']='TikTok reported this publication failed. Review before retrying.'
                    finish(db,f'publication:{item.id}',False)
                item.result_json=json.dumps(stored);db.commit()
                db.execute(update(Activity).where(Activity.user_id==item.user_id,Activity.brand_id==item.brand_id,Activity.draft_id==item.draft_id,Activity.platform==item.platform,Activity.platform_post_id==stored.get('post_id'),Activity.status=='pending').values(status=item.status));db.commit()
                db.execute(update(ScheduledPost).where(ScheduledPost.user_id==item.user_id,ScheduledPost.brand_id==item.brand_id,ScheduledPost.connection_id==item.connection_id,ScheduledPost.draft_id==item.draft_id,ScheduledPost.platform==item.platform,ScheduledPost.status=='pending').values(status=item.status));db.commit()
                update_draft_status(db,item.draft_id)
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
                    if (not item or not review or
                            (item.user_id,item.brand_id,item.draft_id,item.platform,item.connection_id,item.review_code) !=
                            (row.user_id,row.brand_id,row.draft_id,row.platform,row.connection_id,review.code) or
                            (review.user_id,review.brand_id,review.draft_id)!=(row.user_id,row.brand_id,row.draft_id)):
                        raise RuntimeError('Invalid reviewed publication ownership')
                    dispatch(db,item,json.loads(review.payload_json),publish_platform)
                    db.refresh(item);row.status=item.status
                    result=json.loads(item.result_json or '{}');row.platform_post_id=result.get('post_id');row.post_url=result.get('url');row.error=result.get('error');db.commit()
                    update_draft_status(db,row.draft_id)
                    published+=int(row.status=='published');failed+=int(row.status in {'failed','unknown'})
                    continue
                posts = content.get("posts") or []
                link_url = content.get("link_url") or ""
                publish_options = content.get("publish_options") or {}
                assets = scheduled_assets(db, row)
                result = publish_platform(db, user_id=row.user_id, platform=row.platform, posts=posts, assets=assets, link_url=link_url, options=publish_options,connection_id=row.connection_id)
                row.status = "pending" if result.get("pending") else "published"
                row.platform_post_id = result.get("post_id")
                row.post_url = result.get("url")
                db.add(Activity(user_id=row.user_id, brand_id=row.brand_id, draft_id=row.draft_id, platform=row.platform, action="scheduled_publish", status=row.status, text="\n\n".join(posts), platform_post_id=row.platform_post_id, url=row.post_url))
                published += 1
            except SchedulePreflightError as exc:
                # No provider call happened. Keep this distinct from an ambiguous send.
                row.status = 'failed'; row.error = str(exc)
                db.add(Activity(user_id=row.user_id, brand_id=row.brand_id, draft_id=None,
                                platform=row.platform, action='scheduled_publish',
                                status='failed', error=row.error))
                failed += 1
            except Exception as exc:
                log.warning("Scheduled %s post %s failed; outcome unconfirmed", row.platform, row.id)
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
            log.error("Scheduler loop failed; inspect operational status")
        await asyncio.sleep(interval)
