"""Hosted Stripe billing. Test records never replace live account entitlements."""
from __future__ import annotations
import hashlib
import hmac
import json
import os
import re
import time
import uuid
from urllib.parse import urlencode, urlsplit
import httpx
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .db import BillingAccount, BillingEvent, User, utcnow

STRIPE_API = 'https://api.stripe.com/v1'
BLOCKING = {'active','trialing','past_due','unpaid','incomplete','paused'}


def mode():
    value=os.environ.get('STRIPE_MODE','off').lower()
    return value if value in {'test','live'} else 'off'


def plans():
    tiers={name:os.environ.get('STRIPE_'+name.upper()+'_PRICE_ID') for name in
           ('basic_monthly','basic_annual','premium_monthly','premium_annual')}
    if any(tiers.values()):return {name:price for name,price in tiers.items() if price}
    # Retain compatibility with already-configured Creator checkout attempts.
    return {name:price for name,price in {
        'monthly':os.environ.get('STRIPE_MONTHLY_PRICE_ID') or os.environ.get('STRIPE_PRICE_ID'),
        'annual':os.environ.get('STRIPE_ANNUAL_PRICE_ID')}.items() if price}


def plan_label(plan):
    return plan.replace('_',' · ').title() if '_' in plan else 'Creator · '+plan.title()


def configured():
    key=os.environ.get('STRIPE_SECRET_KEY','')
    return (mode()!='off' and key.startswith(('sk_'+mode()+'_','rk_'+mode()+'_'))
            and bool(plans()) and bool(os.environ.get('STRIPE_WEBHOOK_SECRET')))


def checkout_enabled():
    return configured() and (mode()=='test' or os.environ.get('STRIPE_LIVE_CHECKOUT_ENABLED','false').lower()=='true')


def require_subscription():
    return os.environ.get('REQUIRE_SUBSCRIPTION','false').lower() in {'1','true','yes'}


def has_access(user):
    return not require_subscription() or user.subscription_status in {'active','trialing'}


def _request(method,path,data=None,key=None):
    if not configured():raise RuntimeError('Billing is not available yet.')
    headers={'Authorization':'Bearer '+os.environ['STRIPE_SECRET_KEY']}
    if os.environ.get('STRIPE_API_VERSION'):headers['Stripe-Version']=os.environ['STRIPE_API_VERSION']
    if key:headers['Idempotency-Key']=key
    try:
        if method=='GET':response=httpx.get(STRIPE_API+path,headers=headers,params=data,timeout=20)
        else:
            headers['Content-Type']='application/x-www-form-urlencoded'
            response=httpx.post(STRIPE_API+path,headers=headers,content=urlencode(data or {}),timeout=20)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError,ValueError) as exc:
        raise RuntimeError('Stripe could not complete this request. Please retry shortly.') from exc


def _id(value,prefix):
    if not isinstance(value,str) or not re.fullmatch(prefix+r'[A-Za-z0-9_]+',value):
        raise ValueError('Invalid Stripe reference')
    return value


def _url(value,host):
    parsed=urlsplit(value or '')
    if parsed.scheme!='https' or parsed.hostname!=host:raise RuntimeError('Stripe returned an unexpected redirect.')
    return value


def _locked(db,user_id):
    key=f'{user_id}:{mode()}'
    if not db.get(BillingAccount,key):
        user=db.get(User,user_id)
        legacy=mode()=='live'
        with db.begin_nested():
            try:
                db.add(BillingAccount(key=key,user_id=user_id,mode=mode(),customer_id=user.stripe_customer_id if legacy else None,subscription_id=user.stripe_subscription_id if legacy else None,status=user.subscription_status if legacy else 'none'))
                db.flush()
            except IntegrityError:
                raise RuntimeError('Billing is busy. Please retry.')
    # A write lock serializes SQLite too; PostgreSQL holds the row lock until commit.
    db.execute(update(BillingAccount).where(BillingAccount.key==key).values(revision=BillingAccount.revision+1))
    row=db.scalar(select(BillingAccount).where(BillingAccount.key==key).execution_options(populate_existing=True))
    return row


def _sync(db,row):
    if not row.customer_id:return
    data=_request('GET','/subscriptions',{'customer':row.customer_id,'status':'all','limit':100})
    if data.get('has_more'):raise RuntimeError('Billing needs a support review before continuing.')
    allowed=set(plans().values())
    subscriptions=[s for s in data.get('data',[]) if s.get('customer')==row.customer_id and
        (s.get('id')==row.subscription_id or any(i.get('price',{}).get('id') in allowed for i in s.get('items',{}).get('data',[])))]
    if any(bool(s.get('livemode'))!=(row.mode=='live') for s in subscriptions):raise RuntimeError('Stripe mode does not match this account.')
    subscriptions.sort(key=lambda s:(s.get('status') in BLOCKING,s.get('created',0)),reverse=True)
    if subscriptions:
        sub=subscriptions[0];items=sub.get('items',{}).get('data',[])
        row.subscription_id=sub['id'];row.status=sub.get('status','unknown')
        row.price_id=items[0].get('price',{}).get('id') if items else None
        row.cancel_at_period_end=bool(sub.get('cancel_at_period_end') or sub.get('cancel_at'))
        row.period_end=sub.get('cancel_at') or sub.get('current_period_end') or (items[0].get('current_period_end') if items else None)
    else:
        row.status='none';row.subscription_id=None;row.price_id=None;row.cancel_at_period_end=False;row.period_end=None
    row.synced_at=utcnow()
    if row.mode=='live':
        user=db.get(User,row.user_id)
        user.stripe_customer_id=row.customer_id;user.stripe_subscription_id=row.subscription_id;user.subscription_status=row.status


def create_checkout(db,user,base_url,plan='monthly'):
    if not checkout_enabled():raise RuntimeError('Checkout is disabled. Your current access is unchanged.')
    if plan not in plans():raise ValueError('Choose an available plan.')
    row=_locked(db,user.id)
    if not row.customer_id:
        customer=_request('POST','/customers',{'metadata[user_id]':str(user.id)},f'zova-customer-{row.key}')
        row.customer_id=_id(customer.get('id'),'cus_')
    _sync(db,row)
    if row.status in BLOCKING:
        db.commit();raise ValueError('You already have a subscription. Manage it from Billing.')
    if row.checkout_session:
        session=fetch_checkout_session(row.checkout_session)
        if session.get('status')=='open':
            if json.loads(row.checkout_payload)['line_items[0][price]']!=plans()[plan]:
                raise ValueError('An existing checkout is open. Complete it or wait for it to expire before changing plans.')
            url=_url(session.get('url'),'checkout.stripe.com');db.commit();return url
        if session.get('status')!='expired' and not (session.get('status')=='complete' and row.subscription_id and row.status in {'canceled','incomplete_expired'}):
            db.commit();raise ValueError('Checkout is processing. Refresh your billing status shortly.')
        row.checkout_key=None;row.checkout_session=None;row.checkout_payload=None
    if row.checkout_key and int(time.time())-(row.checkout_started or 0)>23*3600:
        raise RuntimeError('This checkout needs reconciliation. Contact support before trying again.')
    if not row.checkout_key:
        price=_request('GET','/prices/'+_id(plans()[plan],'price_'))
        recurring=price.get('recurring') or {}
        if not price.get('active') or price.get('type')!='recurring' or price.get('livemode') is not (mode()=='live') or recurring.get('interval')!=('year' if plan.endswith('annual') else 'month') or recurring.get('interval_count')!=1:
            raise RuntimeError('This subscription plan is unavailable.')
        payload={'mode':'subscription','managed_payments[enabled]':'false','adaptive_pricing[enabled]':'false','customer':row.customer_id,'line_items[0][price]':plans()[plan],'line_items[0][quantity]':'1',
            'success_url':base_url+'/billing/success?session_id={CHECKOUT_SESSION_ID}','cancel_url':base_url+'/subscribe?cancelled=1',
            'client_reference_id':str(user.id),'metadata[user_id]':str(user.id),'subscription_data[metadata][user_id]':str(user.id)}
        if not row.subscription_id:
            payload['subscription_data[trial_period_days]']='7'
            payload['payment_method_collection']='always'
            payload['subscription_data[trial_settings][end_behavior][missing_payment_method]']='cancel'
        row.checkout_key='zova-checkout-'+uuid.uuid4().hex;row.checkout_started=int(time.time());row.checkout_payload=json.dumps(payload)
    elif json.loads(row.checkout_payload)['line_items[0][price]']!=plans()[plan]:
        raise ValueError('Retry the original plan while its checkout is being confirmed.')
    db.commit()  # Persist the retry key and exact parameters before contacting Stripe.
    row=_locked(db,user.id)
    session=_request('POST','/checkout/sessions',json.loads(row.checkout_payload),row.checkout_key)
    row.checkout_session=_id(session.get('id'),'cs_');url=_url(session.get('url'),'checkout.stripe.com')
    db.commit();return url


def create_portal(db,user,base_url):
    if not configured():raise RuntimeError('Billing is not available yet.')
    row=_locked(db,user.id)
    if not row.customer_id:raise ValueError('No billing account is linked yet.')
    data={'customer':row.customer_id,'return_url':base_url+'/subscribe'}
    if os.environ.get('STRIPE_PORTAL_CONFIGURATION_ID'):data['configuration']=os.environ['STRIPE_PORTAL_CONFIGURATION_ID']
    result=_request('POST','/billing_portal/sessions',data,'zova-portal-'+uuid.uuid4().hex)
    db.commit();return _url(result.get('url'),'billing.stripe.com')


def fetch_checkout_session(session_id):
    return _request('GET','/checkout/sessions/'+_id(session_id,'cs_'))


def verify_return(db,user,session_id):
    data=fetch_checkout_session(session_id)
    row=_locked(db,user.id)
    if str(data.get('client_reference_id'))!=str(user.id) or data.get('customer')!=row.customer_id or bool(data.get('livemode'))!=(mode()=='live'):
        raise PermissionError('This checkout does not belong to your billing account.')
    if data.get('mode')!='subscription':raise ValueError('Not a subscription checkout.')
    if data.get('status')!='complete':raise RuntimeError('Checkout has not completed yet.')
    _sync(db,row);db.commit()  # A redirect or payment_status alone never grants access.


def refresh(db,user):
    if not configured():raise RuntimeError('Billing is not available yet.')
    row=_locked(db,user.id);_sync(db,row);db.commit()


def summary(db,user):
    row=db.get(BillingAccount,f'{user.id}:{mode()}')
    return {'mode':mode(),'ready':configured(),'checkout_enabled':checkout_enabled(),'plans':{key:plan_label(key) for key in plans()},
        'trial_eligible':not bool(row and row.subscription_id),
        'plan_label':next((plan_label(key) for key,value in plans().items() if row and value==row.price_id),'Zova membership'),
        'status':row.status if row else (user.subscription_status if mode()!='test' else 'none'),
        'customer':bool(row.customer_id if row else user.stripe_customer_id if mode()=='live' else None),
        'cancelling':bool(row and row.cancel_at_period_end),'period_end':row.period_end if row else None,
        'synced_at':row.synced_at if row else None}


def verify_webhook(raw_body: bytes, signature_header: str) -> bool:
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    if not secret:
        return False
    values = {}
    for piece in signature_header.split(","):
        if "=" in piece:
            k, v = piece.split("=", 1)
            values.setdefault(k, []).append(v)
    try:
        timestamp = int(values["t"][0])
    except Exception:
        return False
    if abs(time.time() - timestamp) > 300:
        return False
    signed = f"{timestamp}.".encode() + raw_body
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, sig) for sig in values.get("v1", []))


def apply_event(db,event):
    if not configured():raise RuntimeError('Billing webhook is not configured.')
    if not isinstance(event,dict) or not isinstance(event.get('id'),str) or not event['id'].startswith('evt_') or len(event['id'])>150:raise ValueError('Invalid Stripe event')
    if event.get('livemode') is not (mode()=='live'):raise ValueError('Incorrect Stripe event mode')
    if db.get(BillingEvent,event['id']):return
    etype=event.get('type','')
    if not isinstance(etype,str) or not isinstance(event.get('data'),dict) or not isinstance(event['data'].get('object'),dict):raise ValueError('Invalid Stripe event')
    obj=event['data']['object']
    relevant=(etype in {'checkout.session.completed','checkout.session.async_payment_succeeded','checkout.session.async_payment_failed','invoice.paid','invoice.payment_failed'} or etype.startswith('customer.subscription.'))
    if relevant:
        customer=obj.get('customer')
        row=db.scalar(select(BillingAccount).where(BillingAccount.customer_id==customer,BillingAccount.mode==mode())) if customer else None
        if not row and mode()=='live' and customer:
            legacy=db.scalar(select(User).where(User.stripe_customer_id==customer))
            if legacy:row=_locked(db,legacy.id)
        if row:
            row=_locked(db,row.user_id)
            if db.get(BillingEvent,event['id']):db.rollback();return
            _sync(db,row)  # Retrieve current Stripe state under the account lock, not event order.
    db.add(BillingEvent(event_id=event['id'],mode=mode(),event_type=str(etype)[:100]))
    try:db.commit()
    except IntegrityError:db.rollback()  # Another delivery committed the same event atomically.
