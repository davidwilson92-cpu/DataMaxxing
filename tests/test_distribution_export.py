import json
import pytest
from sqlalchemy import select
from test_account_integrity import account
from nova import distribution
from nova.db import SessionLocal, ProductEvent

TOKEN='synthetic-distribution-token-000000000000000000'

def test_export_requires_dedicated_token_and_omits_customer_data(monkeypatch):
    client,uid,*_=account()
    monkeypatch.setenv('DISTRIBUTION_READ_TOKEN',TOKEN)
    monkeypatch.setenv('ADMIN_API_KEY','admin-fixture')
    assert client.get('/internal/distribution').status_code==401
    assert client.get('/internal/distribution',headers={'Authorization':'Bearer admin-fixture'}).status_code==401
    result=client.get('/internal/distribution',headers={'Authorization':'Bearer '+TOKEN})
    assert result.status_code==200 and result.headers['cache-control']=='no-store'
    data=result.json()
    assert data['schemaVersion']==1 and data['records']
    assert all(len(r['customerId'])==64 for r in data['records'])
    assert not any(k in result.text for k in ['password_hash','stripe_customer_id','display_name','@'])
    assert client.get('/internal/status',headers={'Authorization':'Bearer '+TOKEN}).status_code==401

def test_cookie_reference_is_validated_and_first_touch_is_preserved(monkeypatch):
    client,uid,*_=account();monkeypatch.setenv('DISTRIBUTION_READ_TOKEN',TOKEN)
    ref='11111111-1111-4111-8111-111111111111'
    result=client.get('/signup?zova_ref='+ref)
    cookie=client.cookies.get('zova_distribution');assert cookie
    client.get('/signup?zova_ref=22222222-2222-4222-8222-222222222222')
    assert client.cookies.get('zova_distribution')==cookie
    class Request: cookies={'zova_distribution':cookie}
    distribution.record_signup(uid,Request());distribution.record_signup(uid,Request())
    with SessionLocal() as db:
        rows=db.scalars(select(ProductEvent).where(ProductEvent.user_id==uid,ProductEvent.kind=='distribution_ref')).all()
        assert len(rows)==1 and ref in rows[0].key
    class Forged: cookies={'zova_distribution':'untrusted'}
    assert distribution.attribution(Forged())==('','')
    assert distribution.reference('https://bad.example')==''

def test_only_positive_live_invoice_receipts_count(monkeypatch):
    _,uid,*_=account();monkeypatch.setenv('DISTRIBUTION_READ_TOKEN',TOKEN)
    event={'id':'evt_distribution_fixture','type':'invoice.paid','livemode':False,'data':{'object':{'paid':True,'amount_paid':999}}}
    with SessionLocal() as db:
        distribution.record_paid(db,uid,event);db.commit()
        assert not db.get(ProductEvent,f'{uid}:distribution_paid:{event["id"]}')
        event['livemode']=True;event['data']['object']['amount_paid']=0
        distribution.record_paid(db,uid,event);db.commit()
        assert not db.get(ProductEvent,f'{uid}:distribution_paid:{event["id"]}')
        event['data']['object']['amount_paid']=999
        distribution.record_paid(db,uid,event);db.commit()
        distribution.record_paid(db,uid,event);db.commit()
        assert db.get(ProductEvent,f'{uid}:distribution_paid:{event["id"]}')

def test_export_paginates_without_duplicate_users(monkeypatch):
    client,*_=account();account();monkeypatch.setenv('DISTRIBUTION_READ_TOKEN',TOKEN)
    headers={'Authorization':'Bearer '+TOKEN}
    first=client.get('/internal/distribution?limit=1',headers=headers).json()
    assert first['nextCursor'] is not None
    second=client.get('/internal/distribution',params={'limit':1,'after':first['nextCursor']},headers=headers).json()
    assert first['records'][0]['customerId']!=second['records'][0]['customerId']
