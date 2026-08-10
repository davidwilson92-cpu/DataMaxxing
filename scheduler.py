from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import timezone

from sqlalchemy import select

from .db import Activity, MediaAsset, ScheduledPost, SessionLocal, utcnow
from .social import publish_platform

log = logging.getLogger("nova.scheduler")


def process_due(limit: int = 25) -> dict[str, int]:
    published = failed = 0
    with SessionLocal() as db:
        rows = db.scalars(
            select(ScheduledPost)
            .where(ScheduledPost.status == "scheduled", ScheduledPost.scheduled_at <= utcnow())
            .order_by(ScheduledPost.scheduled_at.asc())
            .limit(limit)
        ).all()
        for row in rows:
            row.status = "publishing"; db.commit()
            try:
                content = json.loads(row.content_json)
                posts = content.get("posts") or []
                link_url = content.get("link_url") or ""
                media_ids = json.loads(row.media_asset_ids_json or "[]")
                assets = [db.get(MediaAsset, int(mid)) for mid in media_ids]
                assets = [a for a in assets if a is not None and a.user_id == row.user_id]
                result = publish_platform(db, user_id=row.user_id, platform=row.platform, posts=posts, assets=assets, link_url=link_url)
                row.status = "pending" if result.get("pending") else "published"
                row.platform_post_id = result.get("post_id")
                row.post_url = result.get("url")
                db.add(Activity(user_id=row.user_id, draft_id=row.draft_id, platform=row.platform, action="scheduled_publish", status=row.status, text="\n\n".join(posts), platform_post_id=row.platform_post_id, url=row.post_url))
                published += 1
            except Exception as exc:
                log.exception("Scheduled %s post %s failed", row.platform, row.id)
                row.status = "failed"; row.error = str(exc)
                db.add(Activity(user_id=row.user_id, draft_id=row.draft_id, platform=row.platform, action="scheduled_publish", status="failed", text=row.content_json[:2000], error=str(exc)))
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
