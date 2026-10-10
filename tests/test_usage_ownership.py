from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import pytest
from fastapi import HTTPException
from nova import allowances,billing
from nova.db import SessionLocal,UsageEntry,BillingAccount,User
from test_account_integrity import account


@pytest.mark.parametrize('state',['reserved','used','released'])
def test_reservation_and_completion_reject_foreign_owner_or_kind(state):
    _,owner,*_=account();_,other,*_=account()
    key=f'ownership:{owner}'
    with SessionLocal() as db:
        db.add(UsageEntry(key=key,user_id=owner,kind='publications',period='2026-09',amount=3,state=state));db.commit()
    for uid,kind in [(other,'publications'),(owner,'ai')]:
        for operation in ('reserve','finish'):
            with SessionLocal() as db:
                with pytest.raises(HTTPException) as error:
                    if operation=='reserve':allowances.reserve(db,uid,kind,key,3)
                    else:allowances.finish(db,uid,kind,key,False)
                assert error.value.status_code==409
                db.rollback()
                row=db.get(UsageEntry,key)
                assert (row.user_id,row.kind,row.period,row.amount,row.state)==(owner,'publications','2026-09',3,state)


def test_released_reservation_can_retry_in_new_month_with_new_amount(monkeypatch):
    _,uid,*_=account();key=f'retry-month:{uid}'
    monkeypatch.setenv('PLAN_LIMITS_ENABLED','false')
    monkeypatch.setattr(allowances,'utcnow',lambda:datetime(2026,9,30,tzinfo=timezone.utc))
    with SessionLocal() as db:
        allowances.reserve(db,uid,'publications',key,3);db.commit()
        allowances.finish(db,uid,'publications',key,False);db.commit()
    monkeypatch.setattr(allowances,'utcnow',lambda:datetime(2026,10,1,tzinfo=timezone.utc))
    with SessionLocal() as db:
        row=allowances.reserve(db,uid,'publications',key,2);db.commit()
        assert (row.period,row.amount,row.state)==('2026-10',2,'reserved')
        with pytest.raises(HTTPException):allowances.reserve(db,uid,'publications',key,4)
        db.rollback()
        allowances.finish(db,uid,'publications',key);db.commit()
        assert allowances.count(db,uid,'publications')==2
        assert allowances.count(db,uid,'publications','2026-09')==0


def test_concurrent_matching_retries_keep_single_usage_record():
    _,uid,*_=account();key=f'concurrent-retry:{uid}'
    with SessionLocal() as db:
        allowances.reserve(db,uid,'publications',key,3);db.commit()
        allowances.finish(db,uid,'publications',key,False);db.commit()
    def retry(_):
        with SessionLocal() as db:
            row=allowances.reserve(db,uid,'publications',key,3);db.commit()
            return row.key
    with ThreadPoolExecutor(max_workers=2) as pool:assert list(pool.map(retry,range(2)))==[key,key]
    with SessionLocal() as db:assert allowances.count(db,uid,'publications')==3


@pytest.mark.parametrize('amount',[0,-1,True,1.5,2147483648])
def test_invalid_usage_amount_is_rejected_without_record(amount):
    _,uid,*_=account();key=f'invalid-amount:{uid}'
    with SessionLocal() as db:
        with pytest.raises(ValueError):allowances.reserve(db,uid,'ai',key,amount)
        assert db.get(UsageEntry,key) is None


@pytest.mark.parametrize('mismatch',['owner','mode'])
def test_billing_lookup_rejects_key_owner_and_mode_mismatch(monkeypatch,mismatch):
    client,uid,*_=account();_,other,*_=account()
    monkeypatch.setenv('STRIPE_MODE','test')
    monkeypatch.setenv('PLAN_LIMITS_MODE','test')
    monkeypatch.setattr(billing,'_request',lambda *a,**k:pytest.fail('No provider request for mismatched billing ownership'))
    with SessionLocal() as db:
        db.add(BillingAccount(key=f'{uid}:test',user_id=other if mismatch=='owner' else uid,
            mode='live' if mismatch=='mode' else 'test',customer_id=f'cus_foreign_{uid}',status='active'))
        db.commit()
    for operation in ('lookup','lock','summary','tier'):
        with SessionLocal() as db:
            with pytest.raises(RuntimeError,match='ownership'):
                if operation=='lookup':billing.account_for(db,uid,'test')
                elif operation=='lock':billing._locked(db,uid)
                elif operation=='summary':billing.summary(db,db.get(User,uid))
                else:allowances.tier(db,uid)
            db.rollback()
            assert db.get(BillingAccount,f'{uid}:test').revision==0
    response=client.get('/subscribe')
    assert response.status_code==503
    assert 'Your billing details need a check.' in response.text
    assert 'Back to Studio' in response.text and 'Contact Zova support' in response.text
    assert 'Sign out' in response.text
    assert f'cus_foreign_{uid}' not in response.text
    assert '/billing/checkout' not in response.text


def test_billing_disabled_mode_remains_available(monkeypatch):
    client,uid,*_=account()
    monkeypatch.setenv('STRIPE_MODE','off')
    response=client.get('/subscribe')
    assert response.status_code==200
    assert 'Free beta access' in response.text
    with SessionLocal() as db:
        with pytest.raises(RuntimeError,match='not available'):
            billing._locked(db,uid)
        assert db.get(BillingAccount,f'{uid}:off') is None


def test_disabled_limits_do_not_depend_on_billing_lookup(monkeypatch):
    _,uid,*_=account()
    monkeypatch.setenv('PLAN_LIMITS_ENABLED','false')
    monkeypatch.setattr(allowances,'tier',lambda *a:pytest.fail('Disabled limits must not query billing'))
    with SessionLocal() as db:
        allowances.reserve(db,uid,'ai',f'free-testing:{uid}');db.commit()
        assert allowances.count(db,uid,'ai')==1
