"""Bounded, brand-scoped performance evidence; no invented missing metrics."""
import json
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .db import PerformanceSnapshot, utcnow


def fresh(checked_at):
    try:
        checked=datetime.fromisoformat(checked_at.replace('Z','+00:00'))
        if checked.tzinfo is None:return False
        return utcnow()-timedelta(hours=24) <= checked <= utcnow()+timedelta(minutes=1)
    except (ValueError,TypeError,AttributeError):
        return False


def record(db, uid, view):
    payload = {
        'period':view['period'], 'note':view['note'], 'fetched_at':view['fetched_at'],
        'platforms':view['platforms'], 'unavailable':view['unavailable'],
        'posts':[{'platform':p.get('platform'), 'text':str(p.get('text') or '')[:500],
                  'created_at':p.get('created_at'),
                  **{k:p.get(k) for k in ('likes','comments','shares','views')}}
                 for p in view['top_posts'][:6]],
    }
    row = db.scalar(select(PerformanceSnapshot).where(PerformanceSnapshot.user_id == uid,PerformanceSnapshot.brand_id == db.info.get('brand_id',0)))
    if row is None:
        row = PerformanceSnapshot(user_id=uid,brand_id=db.info.get('brand_id',0))
        db.add(row)
    row.payload_json = json.dumps(payload)
    row.fetched_at = utcnow()
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # Another tab's first refresh won; its snapshot remains valid.


def context(db, uid):
    row = db.scalar(select(PerformanceSnapshot).where(PerformanceSnapshot.user_id == uid,PerformanceSnapshot.brand_id == db.info.get('brand_id',0)))
    if row is None:
        return {'available':False, 'note':'No performance snapshot yet. Open Performance to check connected accounts. Recommendations use your strategy and recent work.'}
    if row.fetched_at.replace(tzinfo=None) < (utcnow()-timedelta(hours=24)).replace(tzinfo=None):
        return {'available':False, 'note':'Performance evidence is more than 24 hours old. Open Performance to refresh it; recommendations will not use stale metrics.'}
    try:
        payload = json.loads(row.payload_json)
        if not isinstance(payload,dict) or not isinstance(payload.get('posts'),list):raise ValueError()
    except (ValueError,TypeError):
        return {'available':False, 'note':'Saved performance evidence could not be read. Open Performance to refresh it; recommendations use your strategy.'}
    return {'available':bool(payload.get('posts')), 'evidence':payload,
            'note':'Uses the latest Performance check (within 24 hours). This is a limited recent-post sample, not proof of growth.' if payload.get('posts') else 'No recent post evidence is available. Recommendations use your strategy, not assumed engagement results.'}
