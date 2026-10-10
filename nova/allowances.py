"""Account-wide monthly allowances, shared across brands. Enforcement is opt-in."""
import os
import uuid
from contextlib import contextmanager
from fastapi import HTTPException
from sqlalchemy import select, update, func
from .db import User, BillingAccount, UsageEntry, SocialConnection, Brand, utcnow

PLANS = {
    'basic': {'name': 'Basic', 'monthly': 999, 'annual': 9900, 'brands': 1, 'accounts': 4, 'publications': 100, 'ai': 150},
    'premium': {'name': 'Premium', 'monthly': 1999, 'annual': 19900, 'brands': 2, 'accounts': 8, 'publications': 250, 'ai': 400},
}


def enabled():
    return os.environ.get('PLAN_LIMITS_ENABLED', 'false').lower() == 'true'


def tier(db, uid):
    from .billing import plan_for_price, mode,account_for
    # Test billing cannot affect live access. Testing enforcement requires explicit test scope.
    scope = 'test' if mode() == 'test' and os.environ.get('PLAN_LIMITS_MODE') == 'test' else 'live'
    row = account_for(db,uid,scope)
    if not row or row.status not in {'active','trialing'}:
        return None
    key = plan_for_price(row.price_id) or ''
    return key.split('_')[0] if key.split('_')[0] in PLANS else None


def lock(db, uid):
    db.execute(update(User).where(User.id == uid).values(updated_at=User.updated_at))


def count(db, uid, kind, period=None):
    return db.scalar(select(func.coalesce(func.sum(UsageEntry.amount), 0)).where(
        UsageEntry.user_id == uid, UsageEntry.kind == kind,
        UsageEntry.period == (period or utcnow().strftime('%Y-%m')), UsageEntry.state.in_(['reserved','used']))) or 0


def limit(db, uid, kind, current, added=1):
    if not enabled():
        return
    selected = tier(db, uid)
    if not selected:
        raise HTTPException(402, 'Your plan needs verification. Open Billing; your saved work is safe.')
    if current + added > PLANS[selected][kind]:
        label={'ai':'AI action','publications':'publication','accounts':'social account','brands':'brand workspace'}[kind]
        raise HTTPException(402, f'Your {PLANS[selected]["name"]} {label} allowance is reached. Open Billing to review usage. Your saved work is safe.')


def reserve(db, uid, kind, key, amount=1):
    validate_usage(uid,kind,key)
    if type(amount) is not int or not 1<=amount<=2147483647:
        raise ValueError('Usage amount must be a positive database integer')
    lock(db, uid)
    prior = db.get(UsageEntry, key, populate_existing=True)
    if prior and (prior.user_id!=uid or prior.kind!=kind):
        raise HTTPException(409,'Usage reservation does not match this operation.')
    if prior and prior.state != 'released':
        if prior.state not in {'reserved','used'} or prior.amount!=amount:
            raise HTTPException(409,'Usage reservation changed. Review this operation before retrying.')
        return prior
    period = utcnow().strftime('%Y-%m')
    limit(db, uid, kind, count(db, uid, kind, period), amount)
    if prior:
        prior.period=period; prior.amount=amount; prior.state='reserved'
        return prior
    row = UsageEntry(key=key, user_id=uid, kind=kind, period=period, amount=amount)
    db.add(row); db.flush()
    return row


def validate_usage(uid,kind,key):
    if type(uid) is not int or uid<=0 or not isinstance(kind,str) or kind not in {'ai','publications'} or not isinstance(key,str) or not 1<=len(key)<=180:
        raise ValueError('A valid account, usage kind and operation key are required')


def finish(db, uid, kind, key, success=True):
    validate_usage(uid,kind,key)
    if type(success) is not bool:raise ValueError('Usage result must be explicit')
    lock(db,uid)
    row=db.get(UsageEntry, key, populate_existing=True)
    if row:
        if row.user_id!=uid or row.kind!=kind:
            raise HTTPException(409,'Usage reservation does not match this operation.')
        if row.state not in {'reserved','used','released'}:
            raise HTTPException(409,'Usage reservation requires review.')
        row.state='used' if success else 'released'


@contextmanager
def ai_action(db, uid):
    key=f'ai:{uid}:{uuid.uuid4().hex}'
    reserve(db, uid, 'ai', key); db.commit()
    from .readiness import ai_user
    context_token=ai_user.set(uid)
    try:
        yield
    except Exception:
        db.rollback(); finish(db,uid,'ai',key,False); db.commit()
        raise
    else:
        finish(db,uid,'ai',key); db.commit()
    finally:
        ai_user.reset(context_token)


def connection_slot(db, uid):
    lock(db,uid)
    current=db.scalar(select(func.count(SocialConnection.id)).where(SocialConnection.user_id==uid,SocialConnection.active.is_(True)).execution_options(all_brands=True)) or 0
    limit(db,uid,'accounts',current)


def brand_slot(db, uid):
    lock(db,uid)
    current=1+(db.scalar(select(func.count(Brand.id)).where(Brand.user_id==uid)) or 0)
    # During free testing support the full Premium experience without enabling enforcement.
    if not enabled() and current>=PLANS['premium']['brands']:
        raise HTTPException(409,'Two brand workspaces are available during testing.')
    limit(db,uid,'brands',current)


def summary(db, uid):
    selected=tier(db,uid)
    return {'enabled':enabled(),'tier':selected,'plan':PLANS.get(selected),
            'period':utcnow().strftime('%B %Y'),'ai':count(db,uid,'ai'),'publications':count(db,uid,'publications'),
            'accounts':db.scalar(select(func.count(SocialConnection.id)).where(SocialConnection.user_id==uid,SocialConnection.active.is_(True)).execution_options(all_brands=True)) or 0,
            'brands':1+(db.scalar(select(func.count(Brand.id)).where(Brand.user_id==uid)) or 0)}
