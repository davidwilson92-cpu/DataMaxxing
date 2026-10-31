"""Opt-in read-only distribution export. No customer content or contact details."""
import hashlib
import hmac
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Header, HTTPException, Query, Response
from sqlalchemy import func, select
from .db import SessionLocal, User, ProductEvent, BillingAccount, utcnow
from .security import encrypt, decrypt

router = APIRouter()
log = logging.getLogger(__name__)

def token():
    return os.environ.get('DISTRIBUTION_READ_TOKEN', '')

def enabled():
    return len(token()) >= 32

def reference(value):
    try:
        return str(uuid.UUID(value)) if value else ''
    except (ValueError, TypeError, AttributeError):
        return ''

def attribution(request):
    try:
        data = json.loads(decrypt(request.cookies.get('zova_distribution', '')))
        if data['expires'] > utcnow().timestamp():
            return reference(data.get('proposal')), reference(data.get('partner'))
    except Exception:
        pass
    return '', ''

async def capture_reference(request, call_next):
    response = await call_next(request)
    if not enabled() or request.method != 'GET' or response.status_code >= 400:
        return response
    if any(attribution(request)):
        return response
    proposal, partner = reference(request.query_params.get('zova_ref')), reference(request.query_params.get('zova_partner'))
    if proposal or partner:
        payload = json.dumps({'proposal': proposal, 'partner': partner, 'expires': utcnow().timestamp()+30*86400})
        response.set_cookie('zova_distribution', encrypt(payload), max_age=30*86400, httponly=True,
                            secure=request.url.scheme == 'https', samesite='lax', path='/')
    return response

def record_signup(uid, request):
    if not enabled():
        return
    proposal, partner = attribution(request)
    if not proposal and not partner:
        return
    try:
        with SessionLocal() as db:
            key = f'{uid}:distribution_ref:{proposal}:{partner}'
            if not db.scalar(select(ProductEvent).where(ProductEvent.user_id == uid, ProductEvent.kind == 'distribution_ref')):
                db.add(ProductEvent(key=key, user_id=uid, kind='distribution_ref'))
                db.commit()
    except Exception:
        # Signup must remain successful even if optional attribution fails.
        log.warning('Distribution attribution unavailable')

def record_paid(db, uid, event):
    """Called inside the verified Stripe webhook transaction, before its receipt commits."""
    obj = event.get('data', {}).get('object', {})
    if enabled() and event.get('livemode') is True and event.get('type') == 'invoice.paid' and obj.get('paid') is True and type(obj.get('amount_paid')) is int and obj['amount_paid'] > 0:
        key = f'{uid}:distribution_paid:{event["id"]}'
        if len(key) <= 200 and not db.get(ProductEvent, key):
            db.add(ProductEvent(key=key, user_id=uid, kind='distribution_paid'))

def iso(value):
    return value.replace(tzinfo=timezone.utc).isoformat() if value and value.tzinfo is None else value.isoformat() if value else None

@router.get('/internal/distribution', include_in_schema=False)
def export(response: Response, authorization: str | None = Header(default=None), after: int = Query(0, ge=0), limit: int = Query(250, ge=1, le=500)):
    supplied = (authorization or '').removeprefix('Bearer ')
    if not enabled() or not hmac.compare_digest(supplied.encode(), token().encode()):
        raise HTTPException(401, 'Invalid distribution credential')
    response.headers['Cache-Control'] = 'no-store'
    with SessionLocal() as db:
        users = db.scalars(select(User).where(User.id > after).order_by(User.id).limit(limit+1)).all()
        more = len(users) > limit
        users = users[:limit]
        ids = [u.id for u in users]
        rows = db.scalars(select(ProductEvent).where(ProductEvent.user_id.in_(ids))).all() if ids else []
        records = []
        for user in users:
            events = [e for e in rows if e.user_id == user.id]
            ref = next((e.key.split(':') for e in events if e.kind == 'distribution_ref'), [])
            paid = [e.created_at for e in events if e.kind == 'distribution_paid']
            records.append({'customerId': hmac.new(token().encode(), f'user:{user.id}'.encode(), hashlib.sha256).hexdigest(),
                            'createdAt': iso(user.created_at), 'active': user.active,
                            'proposalId': reference(ref[2]) if len(ref) == 4 else '', 'partnerId': reference(ref[3]) if len(ref) == 4 else '',
                            'paidAt': iso(min(paid)) if paid else None,
                            'activity': sorted({e.kind for e in events if e.kind in {'generated','draft_useful','published','connected'}})})
        return {'schemaVersion': 1, 'observedAt': iso(utcnow()), 'records': records,
                'nextCursor': users[-1].id if more else None,
                'totals': {'accounts': db.scalar(select(func.count(User.id))),
                           'liveActiveSubscriptions': db.scalar(select(func.count(BillingAccount.key)).where(BillingAccount.mode == 'live', BillingAccount.status == 'active')),
                           'testActiveSubscriptions': db.scalar(select(func.count(BillingAccount.key)).where(BillingAccount.mode == 'test', BillingAccount.status == 'active'))},
                'coverage': {'productMetricsEnabled': os.environ.get('PRODUCT_METRICS_ENABLED','false').lower() == 'true',
                             'attribution': 'First-touch web signup only, after enablement; no historical attribution or native deep-link attribution.',
                             'payments': 'Positive live invoice.paid receipts after enablement only. No historical revenue, refunds or test-payment conversions.',
                             'billingMode': os.environ.get('STRIPE_MODE','off')}}
