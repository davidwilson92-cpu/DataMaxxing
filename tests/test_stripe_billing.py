import hashlib
import hmac
import json
import time
from concurrent.futures import ThreadPoolExecutor
import pytest
from test_account_integrity import account
from nova import billing
from nova.db import BillingAccount, BillingEvent, SessionLocal, User


@pytest.fixture
def stripe(monkeypatch):
    for tier in ('BASIC','PREMIUM'):
        for interval in ('MONTHLY','ANNUAL'):monkeypatch.delenv(f'STRIPE_{tier}_{interval}_PRICE_ID',raising=False)
    monkeypatch.setenv('STRIPE_MODE','test')
    monkeypatch.setenv('STRIPE_SECRET_KEY','sk_test_synthetic')
    monkeypatch.setenv('STRIPE_PRICE_ID','price_monthly')
    monkeypatch.setenv('STRIPE_WEBHOOK_SECRET','whsec_synthetic')
    monkeypatch.setenv('REQUIRE_SUBSCRIPTION','false')
    monkeypatch.delenv('STRIPE_MONTHLY_PRICE_ID',raising=False)
    monkeypatch.delenv('STRIPE_ANNUAL_PRICE_ID',raising=False)
    state={'subscriptions':[],'sessions':{},'requests':[],'fail':False}
    def request(method,path,data=None,key=None):
        state['requests'].append((method,path,data,key))
        if state['fail']:raise RuntimeError('Synthetic outage')
        if path=='/customers':return {'id':'cus_'+key.replace(':','_').replace('-','_')}
        if path=='/subscriptions':return {'data':state['subscriptions']}
        if path.startswith('/prices/'):return {'active':True,'type':'recurring','livemode':False,'recurring':{'interval':'month','interval_count':1}}
        if path=='/checkout/sessions':
            session=state['sessions'].setdefault(key,{'id':'cs_'+key.replace('-','_'),'status':'open','url':'https://checkout.stripe.com/c/pay/test','customer':data['customer'],'client_reference_id':data['client_reference_id'],'mode':'subscription','livemode':False})
            return session
        if path.startswith('/checkout/sessions/'):return next(s for s in state['sessions'].values() if s['id']==path.rsplit('/',1)[1])
        if path=='/billing_portal/sessions':return {'url':'https://billing.stripe.com/p/session/test'}
        raise AssertionError(path)
    monkeypatch.setattr(billing,'_request',request)
    return state


def checkout(client):
    return client.post('/billing/checkout',data={'plan':'monthly'},follow_redirects=False)


def subscription(customer,status='active',**extra):
    return {'id':'sub_synthetic','customer':customer,'status':status,'livemode':False,'created':1,'items':{'data':[{'price':{'id':'price_monthly'},'current_period_end':1900000000}]},**extra}


def signed(event,secret='whsec_synthetic',timestamp=None):
    raw=json.dumps(event).encode();timestamp=timestamp or int(time.time())
    sig=hmac.new(secret.encode(),str(timestamp).encode()+b'.'+raw,hashlib.sha256).hexdigest()
    return raw,{'stripe-signature':f't={timestamp},v1={sig}'}


def event(customer,eid='evt_synthetic',kind='customer.subscription.updated'):
    return {'id':eid,'type':kind,'livemode':False,'data':{'object':{'customer':customer,'status':'active'}}}


def test_checkout_reuses_session_and_isolates_test_entitlements(stripe):
    client,uid,*_=account()
    assert checkout(client).headers['location'].startswith('https://checkout.stripe.com/')
    assert checkout(client).headers['location'].startswith('https://checkout.stripe.com/')
    assert len(stripe['sessions'])==1
    with SessionLocal() as db:
        row=db.get(BillingAccount,f'{uid}:test')
        assert row.checkout_key and row.customer_id
        assert db.get(User,uid).stripe_customer_id is None
    posts=[r for r in stripe['requests'] if r[1]=='/checkout/sessions' and r[0]=='POST']
    assert posts[0][2]['line_items[0][price]']=='price_monthly'
    assert client.post('/billing/checkout',data={'plan':'price_attacker'},follow_redirects=False).headers['location'].startswith('/subscribe?error=')


def test_signed_duplicate_and_old_events_retrieve_current_state(stripe):
    client,uid,*_=account();checkout(client)
    customer=next(iter(stripe['sessions'].values()))['customer']
    stripe['subscriptions']=[subscription(customer,cancel_at_period_end=True)]
    raw,headers=signed(event(customer))
    assert client.post('/billing/webhook',content=raw,headers=headers).status_code==200
    count=len(stripe['requests'])
    assert client.post('/billing/webhook',content=raw,headers=headers).status_code==200
    assert len(stripe['requests'])==count
    stripe['subscriptions']=[subscription(customer,'canceled')]
    old=event(customer,'evt_old','customer.subscription.created')
    raw,headers=signed(old)
    assert client.post('/billing/webhook',content=raw,headers=headers).status_code==200
    with SessionLocal() as db:
        assert db.get(BillingAccount,f'{uid}:test').status=='canceled'
        assert db.get(User,uid).subscription_status=='none'
        assert db.get(BillingEvent,'evt_old')


def test_webhook_failures_retry_without_acknowledgement(stripe):
    client,uid,*_=account();checkout(client)
    customer=next(iter(stripe['sessions'].values()))['customer']
    raw,headers=signed(event(customer,'evt_retry'))
    stripe['fail']=True
    assert client.post('/billing/webhook',content=raw,headers=headers).status_code==503
    with SessionLocal() as db:assert db.get(BillingEvent,'evt_retry') is None
    stripe['fail']=False
    assert client.post('/billing/webhook',content=raw,headers=headers).status_code==200
    assert client.post('/billing/webhook',content=raw,headers={'stripe-signature':'bad'}).status_code==400
    expired,h=signed(event(customer),timestamp=int(time.time())-600)
    assert client.post('/billing/webhook',content=expired,headers=h).status_code==400
    wrong=event(customer,'evt_live');wrong['livemode']=True
    raw,h=signed(wrong)
    assert client.post('/billing/webhook',content=raw,headers=h).status_code==400


def test_return_verifies_owner_and_real_subscription_status(stripe):
    client,uid,*_=account();other,*_=account();checkout(client)
    session=next(iter(stripe['sessions'].values()));session['payment_status']='paid';session['status']='complete'
    stripe['subscriptions']=[subscription(session['customer'],'past_due')]
    url='/billing/success?session_id='+session['id']
    assert other.get(url,follow_redirects=False).status_code==403
    assert client.get(url,follow_redirects=False).headers['location']=='/subscribe?returned=1'
    with SessionLocal() as db:
        assert db.get(BillingAccount,f'{uid}:test').status=='past_due'
        assert db.get(User,uid).subscription_status=='none'
    assert checkout(client).headers['location'].startswith('/subscribe?error=')


def test_mutations_require_post_and_same_origin(stripe):
    client,*_=account()
    assert client.get('/billing/checkout',follow_redirects=False).headers['location']=='/subscribe'
    assert client.get('/billing/portal',follow_redirects=False).headers['location']=='/subscribe'
    assert not stripe['requests']
    assert client.post('/billing/checkout',headers={'origin':'https://attacker.test'},data={'plan':'monthly'}).status_code==403
    assert not stripe['requests']
    assert billing._url('https://checkout.stripe.com/test','checkout.stripe.com')
    with pytest.raises(RuntimeError):billing._url('https://evil.test','checkout.stripe.com')


def test_default_off_and_key_mode_mismatch(monkeypatch):
    monkeypatch.setenv('STRIPE_SECRET_KEY','sk_live_synthetic')
    monkeypatch.setenv('STRIPE_PRICE_ID','price_synthetic')
    monkeypatch.setenv('STRIPE_WEBHOOK_SECRET','whsec_synthetic')
    monkeypatch.delenv('STRIPE_MODE',raising=False)
    assert not billing.configured()
    monkeypatch.setenv('STRIPE_MODE','test');assert not billing.configured()
    monkeypatch.setenv('STRIPE_MODE','live');assert billing.configured()
    monkeypatch.setenv('STRIPE_LIVE_CHECKOUT_ENABLED','false');assert not billing.checkout_enabled()


def test_concurrent_checkouts_share_one_session(stripe):
    client,uid,*_=account()
    checkout(client)  # Existing identity; concurrent retries must use the same attempt.
    def run(_):
        with SessionLocal() as db:return billing.create_checkout(db,db.get(User,uid),'http://testserver')
    with ThreadPoolExecutor(max_workers=2) as pool:urls=list(pool.map(run,range(2)))
    assert urls[0]==urls[1] and len(stripe['sessions'])==1


def test_real_http_transport_form_encoding_and_sanitized_errors(monkeypatch):
    import httpx
    monkeypatch.setenv('STRIPE_MODE','test');monkeypatch.setenv('STRIPE_SECRET_KEY','sk_test_synthetic')
    monkeypatch.setenv('STRIPE_PRICE_ID','price_synthetic');monkeypatch.setenv('STRIPE_WEBHOOK_SECRET','whsec_synthetic')
    calls=[]
    def post(url,**kwargs):
        calls.append(kwargs)
        return httpx.Response(200,json={'id':'cs_test'},request=httpx.Request('POST',url))
    monkeypatch.setattr(httpx,'post',post)
    billing._request('POST','/checkout/sessions',{'line_items[0][price]':'price_test'},'retry-key')
    assert calls[0]['content']=='line_items%5B0%5D%5Bprice%5D=price_test'
    assert calls[0]['headers']['Idempotency-Key']=='retry-key'
    def failure(url,**kwargs):return httpx.Response(400,text='secret diagnostic',request=httpx.Request('POST',url))
    monkeypatch.setattr(httpx,'post',failure)
    with pytest.raises(RuntimeError,match='Stripe could not') as exc:billing._request('POST','/customers')
    assert 'secret diagnostic' not in str(exc.value)


def test_uncertain_checkout_reuses_persisted_idempotency_key(stripe,monkeypatch):
    client,uid,*_=account()
    original=billing._request
    lost={'once':True}
    def interrupted(method,path,data=None,key=None):
        result=original(method,path,data,key)
        if path=='/checkout/sessions' and method=='POST' and lost['once']:
            lost['once']=False
            raise RuntimeError('Response lost after Stripe created checkout')
        return result
    monkeypatch.setattr(billing,'_request',interrupted)
    assert checkout(client).headers['location'].startswith('/subscribe?error=')
    with SessionLocal() as db:key=db.get(BillingAccount,f'{uid}:test').checkout_key
    assert checkout(client).headers['location'].startswith('https://checkout.stripe.com')
    assert len(stripe['sessions'])==1 and key in stripe['sessions']


def test_portal_is_bound_to_own_customer_and_pending_return_does_not_grant(stripe):
    client,uid,*_=account();other,*_=account();checkout(client)
    session=next(iter(stripe['sessions'].values()))
    response=client.post('/billing/portal',follow_redirects=False)
    assert response.headers['location'].startswith('https://billing.stripe.com')
    portal=[r for r in stripe['requests'] if r[1]=='/billing_portal/sessions'][-1]
    assert portal[2]['customer']==session['customer']
    assert other.post('/billing/portal',follow_redirects=False).headers['location'].startswith('/subscribe?error=')
    assert client.get('/billing/success?session_id='+session['id'],follow_redirects=False).headers['location']=='/subscribe?pending=1'
    with SessionLocal() as db:assert db.get(User,uid).subscription_status=='none'


def test_live_sync_updates_existing_entitlements_only_after_provider_verification(stripe,monkeypatch):
    client,uid,*_=account()
    monkeypatch.setenv('STRIPE_MODE','live');monkeypatch.setenv('STRIPE_SECRET_KEY','sk_live_synthetic')
    with SessionLocal() as db:
        user=db.get(User,uid);user.stripe_customer_id='cus_live_existing';user.stripe_subscription_id='sub_synthetic';user.subscription_status='active';db.commit()
    stripe['subscriptions']=[subscription('cus_live_existing','past_due',livemode=True)]
    assert client.post('/billing/refresh',follow_redirects=False).status_code==303
    with SessionLocal() as db:
        assert db.get(User,uid).subscription_status=='past_due'
        assert db.get(BillingAccount,f'{uid}:live').customer_id=='cus_live_existing'
    assert billing.has_access(User(subscription_status='past_due'))  # Testing gate remains disabled.


def test_expired_checkout_and_cancelled_subscription_allow_new_attempt(stripe):
    client,uid,*_=account();checkout(client)
    first=next(iter(stripe['sessions'].values()));first['status']='expired'
    assert checkout(client).headers['location'].startswith('https://checkout.stripe.com')
    assert len(stripe['sessions'])==2
    second=list(stripe['sessions'].values())[-1];second['status']='complete'
    stripe['subscriptions']=[subscription(second['customer'],'canceled')]
    assert checkout(client).headers['location'].startswith('https://checkout.stripe.com')
    assert len(stripe['sessions'])==3


def test_wrong_billing_interval_is_rejected_before_checkout(stripe,monkeypatch):
    client,*_=account();original=billing._request
    def wrong_interval(method,path,data=None,key=None):
        result=original(method,path,data,key)
        if path.startswith('/prices/'):result['recurring']['interval']='year'
        return result
    monkeypatch.setattr(billing,'_request',wrong_interval)
    assert checkout(client).headers['location'].startswith('/subscribe?error=')
    assert not stripe['sessions']


@pytest.mark.parametrize('plan',['basic_monthly','basic_annual','premium_monthly','premium_annual'])
def test_tier_prices_and_seven_day_trial(stripe,monkeypatch,plan):
    for key in ('basic_monthly','basic_annual','premium_monthly','premium_annual'):
        monkeypatch.setenv('STRIPE_'+key.upper()+'_PRICE_ID','price_'+key)
    original=billing._request
    def request(method,path,data=None,key=None):
        result=original(method,path,data,key)
        if path.startswith('/prices/'):
            result['recurring']['interval']='year' if path.endswith('annual') else 'month'
        return result
    monkeypatch.setattr(billing,'_request',request)
    client,*_=account()
    page=client.get('/subscribe').text
    assert 'Basic · Monthly' in page and 'Premium · Annual' in page and '7-day free trial' in page
    result=client.post('/billing/checkout',data={'plan':plan},follow_redirects=False)
    assert result.headers['location'].startswith('https://checkout.stripe.com')
    payload=[r[2] for r in stripe['requests'] if r[1]=='/checkout/sessions' and r[0]=='POST'][-1]
    assert payload['line_items[0][price]']=='price_'+plan
    assert payload['subscription_data[trial_period_days]']=='7'
    assert payload['payment_method_collection']=='always'
    assert payload['subscription_data[trial_settings][end_behavior][missing_payment_method]']=='cancel'


def test_returning_subscriber_does_not_receive_repeat_trial(stripe):
    client,*_=account();checkout(client)
    session=next(iter(stripe['sessions'].values()));session['status']='complete'
    stripe['subscriptions']=[subscription(session['customer'],'canceled')]
    checkout(client)
    payload=[r[2] for r in stripe['requests'] if r[1]=='/checkout/sessions' and r[0]=='POST'][-1]
    assert 'subscription_data[trial_period_days]' not in payload
