"""Reconcile existing receipts only. This module never creates a post."""
import json
import re
from datetime import datetime, timedelta
from sqlalchemy import update
from .db import Publication, Activity, ScheduledPost, PublishReview, utcnow
from .social import selected_connection, resolve_tiktok_post


def reconcile(db, item):
    if item.platform != 'tiktok' or item.status not in {'pending', 'published'}:
        return
    stored = json.loads(item.result_json or '{}')
    if not stored.get('post_id') or stored.get('url'):
        return
    if item.status == 'published' and stored.get('privacy_level') != 'PUBLIC_TO_EVERYONE':
        return
    checked = stored.get('status_checked_at')
    if checked and datetime.fromisoformat(checked) > utcnow() - timedelta(seconds=15):
        return
    previous = item.result_json
    stored['status_checked_at'] = utcnow().isoformat()
    claimed = db.execute(update(Publication).where(
        Publication.id == item.id, Publication.status == item.status,
        Publication.result_json == previous,
    ).values(result_json=json.dumps(stored)).execution_options(synchronize_session=False))
    if claimed.rowcount != 1:
        db.rollback()
        db.refresh(item)
        return
    db.commit()
    db.refresh(item)
    try:
        conn = selected_connection(db, item.user_id, 'tiktok', item.connection_id)
        state = resolve_tiktok_post(db, conn, stored['post_id'])
        remote = str(state.get('status', '')).upper()
        if remote == 'PUBLISH_COMPLETE':
            item.status = 'published'
            stored.update(pending=False, requires_tiktok_completion=False)
            ids = state.get('public_ids') or []
            # A receipt is not a public post ID. Never manufacture a receipt URL.
            if ids and re.fullmatch(r'[0-9]+', str(ids[0])) and re.fullmatch(r'[\w.]+', conn.username or '', re.ASCII):
                review = db.get(PublishReview, item.review_code)
                payload = json.loads(review.payload_json) if review else {}
                media = payload.get('media') or []
                kind = 'photo' if media and media[0].get('kind') == 'image' else 'video'
                stored['url'] = f'https://www.tiktok.com/@{conn.username}/{kind}/{ids[0]}'
        elif remote == 'SEND_TO_USER_INBOX':
            stored.update(requires_tiktok_completion=True, delivered_to_inbox=True)
        elif remote in {'FAILED', 'PUBLISH_FAILED'} and item.status == 'pending':
            from .allowances import finish
            item.status = 'failed'
            stored['error'] = 'TikTok reported this publication failed. Review before retrying.'
            finish(db, f'publication:{item.id}', False)
        item.result_json = json.dumps(stored)
        db.execute(update(Activity).where(Activity.draft_id == item.draft_id, Activity.platform == 'tiktok', Activity.platform_post_id == stored['post_id']).values(status=item.status, url=stored.get('url')))
        db.execute(update(ScheduledPost).where(ScheduledPost.draft_id == item.draft_id, ScheduledPost.platform == 'tiktok', ScheduledPost.status.in_(['pending', 'published'])).values(status=item.status, post_url=stored.get('url')))
        db.commit()
        from .publishing_workflow import update_draft_status
        update_draft_status(db, item.draft_id)
    except Exception:
        db.rollback()  # Keep the last confirmed state; never retry delivery.
        db.refresh(item)
