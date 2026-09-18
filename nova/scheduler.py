from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import timezone,timedelta

from sqlalchemy import select,update

from .db import Activity, MediaAsset, ScheduledPost, SessionLocal, Publication, PublishReview, Draft, utcnow
from .social import publish_platform,resolve_tiktok_post,selected_connection
from .publishing_workflow import dispatch,update_draft_status

log = logging.getLogger("nova.scheduler")


def process_due(limit: int = 25) -> dict[str, int]:
    published = failed = 0
    with SessionLocal() as db:
        # Never automatically resend an uncertain request after a crash.
        stale=utcnow()-timedelta(minutes=15)
        stuck=db.scalars(select(Publication).where(Publication.status.in_(['publishing','queued']),Publication.updated_at<stale)).all()
        for item in stuck:
            item.status='unknown';item.result_json=json.dumps({'error':'Worker interrupted; check the destination before retrying.'})
        db.execute(update(ScheduledPost).where(ScheduledPost.status=='publishing',ScheduledPost.updated_at<stale).values(status='unknown',error='Worker interrupted; verify destination.'))
        db.commit()
        for item in stuck:update_draft_status(db,item.draft_id)
        pending=db.scalars(select(Publication).where(Publication.platform=='tiktok',Publication.status=='pending').limit(limit)).all()
        for item in pending:
            try:
                stored=json.loads(item.result_json);conn=selected_connection(db,item.user_id,item.platform,item.connection_id)
                state=resolve_tiktok_post(db,conn,stored['post_id']);remote=str(state.get('status','')).upper()
                if remote=='PUBLISH_COMPLETE':
                    item.status='published';stored['pending']=False
                    if state.get('public_ids'):stored['url']='https://www.tiktok.com/@'+conn.username+'/video/'+str(state['public_ids'][0])
                elif remote=='FAILED':
                    from .allowances import finish
                    item.status='failed';stored['error']='TikTok reported this publication failed. Review before retrying.'
                    finish(db,f'publication:{item.id}',False)
                item.result_json=json.dumps(stored);db.commit()
                db.execute(update(Activity).where(Activity.draft_id==item.draft_id,Activity.platform==item.platform,Activity.platform_post_id==stored.get('post_id'),Activity.status=='pending').values(status=item.status));db.commit()
                db.execute(update(ScheduledPost).where(ScheduledPost.draft_id==item.draft_id,ScheduledPost.platform==item.platform,ScheduledPost.status=='pending').values(status=item.status));db.commit()
                update_draft_status(db,item.draft_id)
            except Exception:db.rollback();log.warning('Pending publication could not be checked; it will not be resent')
        rows = db.scalars(
            select(ScheduledPost)
            .where(ScheduledPost.status == "scheduled", ScheduledPost.scheduled_at <= utcnow())
            .order_by(ScheduledPost.scheduled_at.asc())
            .limit(limit)
        ).all()
        for row in rows:
            claimed=db.execute(update(ScheduledPost).where(ScheduledPost.id==row.id,ScheduledPost.status=='scheduled').values(status='publishing',updated_at=utcnow()).execution_options(synchronize_session=False))
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
