"""Minimal first-party measurement: no prompts, IPs, emails or provider payloads."""
import json
import logging
import os
import uuid
from contextvars import ContextVar
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .db import AICall, ProductEvent, SessionLocal, Draft, User, utcnow, get_db
from .security import current_user

log = logging.getLogger(__name__)
ai_user = ContextVar('ai_user', default=None)
router = APIRouter()
EVENTS = {'signup', 'visit', 'generated', 'revised', 'connected', 'reviewed', 'published', 'draft_useful'}


def event(uid, kind, identity):
    if os.environ.get('PRODUCT_METRICS_ENABLED', 'false').lower() != 'true':
        return
    if kind not in EVENTS:
        raise ValueError('Unknown product event')
    # Callers use internal row IDs or UTC dates, never content/customer input.
    try:
        with SessionLocal() as db:
            db.add(ProductEvent(key=f'{uid}:{kind}:{identity}', user_id=uid, kind=kind))
            db.commit()
    except IntegrityError:
        pass
    except Exception:
        log.warning('Product measurement unavailable')


def estimate(model, usage):
    """Configured GBP per million tokens, including cached input; missing != zero."""
    try:
        rate = json.loads(os.environ.get('AI_GBP_RATES_JSON', '{}')).get(model)
        if not rate or not rate.get('as_of'):
            return None, None
        values = [usage.get('input_tokens'), usage.get('output_tokens')]
        cached = usage.get('input_tokens_details', {}).get('cached_tokens', 0)
        if any(type(n) is not int or n < 0 for n in [*values, cached]) or cached > values[0]:
            return None, None
        rates = [Decimal(str(rate[k])) for k in ['input', 'cached_input', 'output']]
        if any(not r.is_finite() or r < 0 for r in rates):
            return None, None
        amount = ((values[0]-cached)*rates[0] + cached*rates[1] + values[1]*rates[2])/Decimal(1000000)
        return str(amount), str(rate['as_of'])[:30]
    except (ValueError, TypeError, KeyError, InvalidOperation, AttributeError):
        return None, None


def record_ai(model, status, payload=None):
    usage = payload.get('usage', {}) if isinstance(payload, dict) else {}
    if not isinstance(usage,dict):usage={}
    def tokens(value):
        return value if type(value) is int and 0 <= value <= 2147483647 else None
    try:
        estimate_gbp, date = estimate(model, usage)
        rates=json.loads(os.environ.get('AI_GBP_RATES_JSON','{}')).get(model,{}) if date else {}
        snapshot={k:rates.get(k) for k in ['input','cached_input','output','as_of','source']}
        with SessionLocal() as db:
            db.add(AICall(id=uuid.uuid4().hex, user_id=ai_user.get(), model=model[:120], status=status,
                input_tokens=tokens(usage.get('input_tokens')), output_tokens=tokens(usage.get('output_tokens')),
                cached_tokens=tokens((usage.get('input_tokens_details') or {}).get('cached_tokens')),
                estimated_gbp=estimate_gbp, rate_date=date,rate_snapshot=json.dumps(snapshot)))
            db.commit()
    except Exception:
        # A telemetry failure must not cause a duplicate generation or lose customer output.
        log.warning('AI usage recording unavailable')


def spend_summary(db):
    start=utcnow().replace(day=1,hour=0,minute=0,second=0,microsecond=0)
    rows=db.scalars(select(AICall).where(AICall.created_at>=start)).all()
    total=sum((Decimal(r.estimated_gbp) for r in rows if r.estimated_gbp is not None),Decimal(0))
    threshold=None
    try:
        value=Decimal(os.environ.get('AI_MONTHLY_ALERT_GBP',''))
        if value.is_finite() and value>0: threshold=value
    except InvalidOperation: pass
    return {'period':start.strftime('%Y-%m'),'calls':len(rows),'estimated_gbp':str(total),
        'unpriced_calls':sum(r.estimated_gbp is None for r in rows),
        'threshold_gbp':str(threshold) if threshold is not None else None,
        'threshold_exceeded':threshold is not None and total>=threshold,
        'complete':all(r.estimated_gbp is not None for r in rows),
        'note':'Token counts are provider-reported; GBP costs are configured estimates, not invoices. Missing usage and failed requests may have unmeasured cost.'}


def cohort_report(db, now=None):
    now=now or utcnow()
    users=db.scalars(select(User)).all()
    events=db.scalars(select(ProductEvent)).all()
    by_user={}
    for row in events: by_user.setdefault(row.user_id,[]).append(row)
    cohorts={}
    for user in users:
        rows=by_user.get(user.id,[])
        signup=next((r for r in rows if r.kind=='signup'),None)
        if not signup: continue  # Do not imply historical collection.
        started=signup.created_at.replace(tzinfo=now.tzinfo)
        cohort=cohorts.setdefault(started.strftime('%Y-%m-%d'),{'signups':0,'generated':0,'useful':0,'published':0,'d7_eligible':0,'d7_returned':0,'seconds_to_useful':[]})
        cohort['signups']+=1
        for field,kind in [('generated','generated'),('useful','draft_useful'),('published','published')]:
            cohort[field]+=int(any(r.kind==kind for r in rows))
        useful=[r.created_at.replace(tzinfo=now.tzinfo) for r in rows if r.kind=='draft_useful']
        if useful: cohort['seconds_to_useful'].append(max(0,int((min(useful)-started).total_seconds())))
        if now>=started+timedelta(days=8):
            cohort['d7_eligible']+=1
            cohort['d7_returned']+=int(any(r.kind=='visit' and started+timedelta(days=7)<=r.created_at.replace(tzinfo=now.tzinfo)<started+timedelta(days=8) for r in rows))
    return {'enabled':os.environ.get('PRODUCT_METRICS_ENABLED','false').lower()=='true','cohorts':cohorts,
        'definition':'Useful means explicit customer feedback, not generation. D7 is a signed-in Studio visit 7–8 days after signup; immature cohorts excluded. No historic backfill.'}


@router.post('/api/drafts/{draft_id}/useful')
def useful(draft_id:int, request:Request, db=Depends(get_db)):
    user=current_user(request)
    row=db.get(Draft,draft_id)
    if not row or row.user_id!=user.id: raise HTTPException(404,'Draft not found')
    if not json.loads(row.variants_json or '{}'): raise HTTPException(409,'Create a draft version first')
    if os.environ.get('PRODUCT_METRICS_ENABLED','false').lower()!='true':
        raise HTTPException(409,'Feedback measurement is not enabled')
    event(user.id,'draft_useful',row.id)
    return {'recorded':True}
