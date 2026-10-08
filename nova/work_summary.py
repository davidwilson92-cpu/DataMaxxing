"""Customer-facing labels and scoped work counts; never infer provider success."""
import json
import re
from datetime import timedelta
from sqlalchemy import select, func
from .db import Draft, Publication, ScheduledPost, utcnow


def draft_title(row):
    if row.title:
        return row.title
    try:
        workspace = json.loads(row.workspace_json or '{}')
        messages = workspace.get('conversation', [])
        first = next((m.get('content', '') for m in messages if isinstance(m, dict) and m.get('role') == 'user' and m.get('content')), '')
        text = first or row.brief or workspace.get('composer', '')
    except (ValueError, TypeError, AttributeError):
        text = row.brief
    text = re.sub(r'^\s*Topic:\s*', '', str(text or ''), flags=re.I)
    text = re.split(r'\bAssumptions\s*:', text, maxsplit=1, flags=re.I)[0]
    text = ' '.join(text.split()).strip(' ,;')
    if not text:
        return 'New idea'
    return text if len(text) <= 72 else text[:69].rsplit(' ', 1)[0] + '…'


def work_summary(db, user_id):
    # Explicit scope even in a background/unscoped session.
    brand_id = db.info.get('brand_id', 0)
    now = utcnow()
    def count(model, *where):
        return db.scalar(select(func.count()).select_from(model).where(model.user_id == user_id, model.brand_id == brand_id, *where)) or 0
    return {
        'drafts': count(Draft, Draft.status.in_(('draft','cancelled'))),
        'scheduled': count(ScheduledPost, ScheduledPost.status == 'scheduled', ScheduledPost.scheduled_at >= now, ScheduledPost.scheduled_at < now + timedelta(days=7)),
        'overdue': count(ScheduledPost, ScheduledPost.status == 'scheduled', ScheduledPost.scheduled_at < now - timedelta(minutes=5)),
        'unconfirmed': count(Publication, Publication.status.in_(('unknown','pending','publishing','queued'))),
        'needs_review': count(Draft, Draft.status.in_(('needs_review','failed','partial'))),
    }
