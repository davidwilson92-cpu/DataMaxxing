"""Bounded, brand-scoped performance evidence; no invented missing metrics."""
import json
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .db import PerformanceSnapshot, SocialConnection, utcnow


def connection_stamp(connections):
    return sorted(f'{c.platform}:{c.id}:{c.account_id}' for c in connections)


def fresh(checked_at):
    try:
        checked=datetime.fromisoformat(checked_at.replace('Z','+00:00'))
        if checked.tzinfo is None:return False
        return utcnow()-timedelta(hours=24) <= checked <= utcnow()+timedelta(minutes=1)
    except (ValueError,TypeError,AttributeError):
        return False


def record(db, uid, view):
    payload = {
        'connections':connection_stamp(db.scalars(select(SocialConnection).where(
            SocialConnection.user_id==uid,SocialConnection.active.is_(True))).all()),
        'last_attempt_at':utcnow().isoformat(), 'period':view['period'], 'note':view['note'], 'fetched_at':view['fetched_at'],
        'platforms':view['platforms'], 'unavailable':view['unavailable'],
        'posts':[{'platform':p.get('platform'), 'text':str(p.get('text') or '')[:500],
                  'created_at':p.get('created_at'), 'format':p.get('format'),
                  **{k:p.get(k) for k in ('likes','comments','shares','views')}}
                 for p in view.get('sample_posts',view['top_posts'])[:30]],
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


def recommendation_context(db, uid):
    """Refresh a bounded provider sample automatically, with a durable retry cooldown.

    Never pass expired metrics as fresh or erase usable evidence after a failed read.
    The caller's existing brand scope and AI consent apply to all operations.
    """
    from .social import recent_posts_for_user
    from .analytics_view import dashboard, valid_metric
    connections = db.scalars(select(SocialConnection).where(SocialConnection.user_id==uid,
        SocialConnection.active.is_(True))).all()
    if not connections:
        return {'available':False,'note':'Connect a social account for performance-led ideas. These use your direction and voice.'}
    active_platforms = {conn.platform for conn in connections}
    stamp = connection_stamp(connections)
    def current_context():
        result = context(db,uid)
        if result.get('evidence'):
            evidence = result['evidence']
            if evidence.get('connections') != stamp:
                return {'available':False,'note':'Connections changed. These ideas use your direction and voice until results refresh.'}
            evidence['posts'] = [p for p in evidence.get('posts',[]) if p.get('platform') in active_platforms
                and any(valid_metric(p.get(key)) for key in ('likes','comments','shares','views'))]
            evidence['platforms'] = {k:v for k,v in evidence.get('platforms',{}).items() if k in active_platforms}
            result['available'] = bool(evidence['posts'])
            evidence.pop('connections',None)
            evidence.pop('attempt_connections',None)
            if not result['available']:
                result['note'] = 'No usable performance counters yet. These ideas use your direction and voice.'
        return result
    row = db.scalar(select(PerformanceSnapshot).where(PerformanceSnapshot.user_id==uid,
        PerformanceSnapshot.brand_id==db.info.get('brand_id',0)))
    try:
        payload = json.loads(row.payload_json) if row else {}
        attempted = datetime.fromisoformat(payload.get('last_attempt_at',payload.get('fetched_at','')))
        if payload.get('attempt_connections',payload.get('connections')) == stamp and attempted.tzinfo and utcnow()-timedelta(minutes=15) <= attempted <= utcnow()+timedelta(minutes=1):
            return current_context()
    except (ValueError,TypeError,AttributeError):
        payload = {}
    try:
        feed = recent_posts_for_user(db,uid,limit=30,quick=True)
        if not feed.get('posts') and feed.get('unavailable'):
            raise ValueError('Provider sample unavailable')
        db.expire_all()
        latest_connections = db.scalars(select(SocialConnection).where(SocialConnection.user_id==uid,
            SocialConnection.active.is_(True))).all()
        if connection_stamp(latest_connections) != stamp:
            return {'available':False,'note':'Connections changed during refresh. These ideas use your direction and voice.'}
        accounts = {conn.platform:{'connected':True} for conn in latest_connections}
        view = dashboard(accounts,feed,window_days=30)
        record(db,uid,view)
        return current_context()
    except Exception:
        # No provider exception or credential data is exposed to the model or UI.
        db.rollback()
        row = db.scalar(select(PerformanceSnapshot).where(PerformanceSnapshot.user_id==uid,
            PerformanceSnapshot.brand_id==db.info.get('brand_id',0)))
        if row is None:
            row = PerformanceSnapshot(user_id=uid,brand_id=db.info.get('brand_id',0))
            db.add(row)
        else:
            try: payload = json.loads(row.payload_json)
            except (ValueError,TypeError): payload = {}
        payload = payload if isinstance(payload,dict) else {}
        payload['last_attempt_at'] = utcnow().isoformat()
        payload['attempt_connections'] = stamp
        row.payload_json = json.dumps(payload)
        db.commit()
        result = current_context()
        result['note'] = ('Latest refresh unavailable; using the previous check from within 24 hours.'
            if result['available'] else 'Performance could not be refreshed. These ideas use your direction and voice.')
        return result
