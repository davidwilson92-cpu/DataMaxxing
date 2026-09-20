import json
from datetime import timedelta
from decimal import Decimal
import pytest
from sqlalchemy import select
from test_account_integrity import account
from nova import ai, allowances, readiness, recovery, verification
from nova.db import SessionLocal, User, Draft, AICall, ProductEvent, EmailVerification, MediaAsset, SocialConnection, BillingAccount, utcnow
from nova.security import hash_api_key, encrypt, user_from_session


def test_customer_offer_support_and_recovery_brand(monkeypatch):
    client,*_=account()
    monkeypatch.setenv('SUPPORT_EMAIL','support@example.test')
    monkeypatch.setenv('LEGAL_ENTITY_NAME','Synthetic Zova Operator')
    for path in ['/','/signup','/help','/account','/subscribe']:
        html=client.get(path).text
        assert '9.99' in html and '199' in html,path
    for path in ['/help','/account','/subscribe?error=1','/forgot-password','/reset-password']:
        html=client.get(path).text
        assert 'support@example.test' in html,path
    assert 'Synthetic Zova Operator' in client.get('/forgot-password').text
    assert 'account timezone' in client.get('/help').text
    assert 'for="analyticsQuestionText"' in client.get('/analytics').text


def test_cost_usage_recorded_without_content_and_failures_unknown(monkeypatch):
    _,uid,*_=account()
    monkeypatch.setenv('OPENAI_MODEL','synthetic-model')
    monkeypatch.setenv('OPENAI_API_KEY','synthetic-only')
    monkeypatch.setenv('AI_GBP_RATES_JSON',json.dumps({'synthetic-model':{'input':1,'cached_input':.1,'output':4,'as_of':'synthetic-2026-09-20'}}))
    class Response:
        status_code=200
        def json(self):return {'output_text':'Synthetic answer','usage':{'input_tokens':1000,'input_tokens_details':{'cached_tokens':200},'output_tokens':100}}
    monkeypatch.setattr(ai.httpx,'post',lambda *a,**k:Response())
    with SessionLocal() as db:
        with allowances.ai_action(db,uid):assert ai._responses('PRIVATE PROMPT')=='Synthetic answer'
    with SessionLocal() as db:
        row=db.scalar(select(AICall).where(AICall.user_id==uid))
        assert row.input_tokens==1000 and Decimal(row.estimated_gbp)==Decimal('.00122')
        assert not hasattr(row,'prompt')
    monkeypatch.setattr(ai.httpx,'post',lambda *a,**k:(_ for _ in ()).throw(TimeoutError('synthetic timeout')))
    with SessionLocal() as db:
        with pytest.raises(TimeoutError):
            with allowances.ai_action(db,uid):ai._responses('PRIVATE RETRY')
    with SessionLocal() as db:
        rows=db.scalars(select(AICall).where(AICall.user_id==uid)).all()
        assert len(rows)==2 and sum(r.estimated_gbp is None for r in rows)==1
        assert allowances.count(db,uid,'ai')==1
    assert readiness.ai_user.get() is None


def test_spend_alert_and_unknown_cost(monkeypatch):
    from scripts.check_service import check
    monkeypatch.setenv('AI_MONTHLY_ALERT_GBP','0.0001')
    with SessionLocal() as db:
        db.add(AICall(id='alert-synthetic',model='synthetic',status='returned',estimated_gbp='2'))
        db.add(AICall(id='missing-synthetic',model='unknown',status='unconfirmed'))
        db.commit();report=readiness.spend_summary(db)
    assert report['threshold_exceeded'] and not report['complete']
    assert check({'database':'reachable','ai_spend':report})['status']=='attention'
    monkeypatch.setenv('AI_GBP_RATES_JSON','{}')
    assert readiness.estimate('unknown',{'input_tokens':10,'output_tokens':10})==(None,None)


def test_product_events_off_and_explicit_usefulness_owned(monkeypatch):
    client,uid,*_=account();other,*_=account()
    with SessionLocal() as db:
        draft=Draft(user_id=uid,brief='private idea',variants_json='{"x":["private output"]}')
        db.add(draft);db.commit();did=draft.id
    monkeypatch.setenv('PRODUCT_METRICS_ENABLED','false')
    readiness.event(uid,'signup',uid)
    assert client.post(f'/api/drafts/{did}/useful').status_code==409
    monkeypatch.setenv('PRODUCT_METRICS_ENABLED','true')
    assert other.post(f'/api/drafts/{did}/useful').status_code==404
    assert client.post(f'/api/drafts/{did}/useful').status_code==200
    assert client.post(f'/api/drafts/{did}/useful').status_code==200
    with SessionLocal() as db:
        events=db.scalars(select(ProductEvent).where(ProductEvent.user_id==uid)).all()
        assert len(events)==1 and events[0].kind=='draft_useful'
        assert 'private' not in events[0].key


def test_cohort_eligibility_and_usefulness_distinct(monkeypatch):
    _,uid,*_=account();now=utcnow()
    monkeypatch.setenv('PRODUCT_METRICS_ENABLED','true')
    with SessionLocal() as db:
        for kind,offset in [('signup',9),('generated',9),('visit',1.5)]:
            db.add(ProductEvent(key=f'{uid}:cohort:{kind}',user_id=uid,kind=kind,created_at=now-timedelta(days=offset)))
        db.commit();report=readiness.cohort_report(db,now)
        cohort=report['cohorts'][(now-timedelta(days=9)).strftime('%Y-%m-%d')]
        assert cohort['generated']>=1 and cohort['useful']==0
        assert cohort['d7_eligible']>=1 and cohort['d7_returned']>=1


def test_email_verification_owned_expiring_single_use(monkeypatch):
    client,uid,session,email=account();other,*_=account();sent=[]
    monkeypatch.setattr(recovery,'recovery_ready',lambda:True)
    monkeypatch.setattr(verification,'deliver',lambda address,token:sent.append(token))
    assert client.post('/account/verify-email').status_code==200
    token=sent[0]
    assert other.post('/verify-email',data={'token':token}).status_code==400
    assert client.post('/verify-email',data={'token':token}).status_code==200
    assert client.post('/verify-email',data={'token':token}).status_code==400
    with SessionLocal() as db:assert db.get(User,uid).email_verified_at is not None
    assert user_from_session(session).id==uid
    with SessionLocal() as db:
        db.add(EmailVerification(token_hash=hash_api_key('expired-synthetic'),user_id=uid,email=email,expires_at=utcnow()-timedelta(minutes=1)));db.commit()
    assert client.post('/verify-email',data={'token':'expired-synthetic'}).status_code==400


def test_recovery_delivery_failure_invalidates_link(monkeypatch):
    client,uid,*_=account()
    from nova.db import RecoveryToken
    monkeypatch.setattr(recovery,'send_recovery_email',lambda *a:(_ for _ in ()).throw(OSError('synthetic mail failure')))
    with SessionLocal() as db:
        db.add(RecoveryToken(token_hash=hash_api_key('failed-delivery'),user_id=uid,auth_version=0,expires_at=utcnow()+timedelta(minutes=15)));db.commit()
    recovery.deliver_recovery('synthetic@example.test','failed-delivery')
    with SessionLocal() as db:assert db.get(RecoveryToken,hash_api_key('failed-delivery')).used


def test_export_and_local_erasure_preserve_other_user(tmp_path):
    from nova.data_lifecycle import export_account,erase_local_account
    from nova.storage import UPLOAD_DIR
    client,uid,token,email=account();_,other_uid,*_=account()
    path=UPLOAD_DIR/f'erase-{uid}.png';path.write_bytes(b'synthetic')
    with SessionLocal() as db:
        db.add(Draft(user_id=uid,brief='Private draft'))
        db.add(SocialConnection(user_id=uid,platform='x',account_id='synthetic',encrypted_access_token=encrypt('secret')))
        db.add(MediaAsset(user_id=uid,filename='private.png',mime_type='image/png',storage_key=str(path),size_bytes=9))
        db.commit()
        exported=export_account(db,uid)
        assert exported['nova_users'][0]['email']==email
        assert 'password_hash' not in json.dumps(exported) and 'encrypted_access_token' not in json.dumps(exported)
        with pytest.raises(ValueError):erase_local_account(db,uid,'verified-case-123')
        result=erase_local_account(db,uid,'verified-case-123',writes_paused=True)
        assert result['status']=='active_store_erased' and not path.exists()
        assert db.get(User,other_uid).active
        assert not db.get(User,uid).active
        assert 'Private draft' not in json.dumps(export_account(db,uid))
    assert user_from_session(token) is None


def test_erasure_blocks_active_billing_and_remote_storage():
    from nova.data_lifecycle import erase_plan,erase_local_account
    _,uid,*_=account()
    with SessionLocal() as db:
        db.add(BillingAccount(key=f'{uid}:test',user_id=uid,mode='test',status='active'))
        db.add(MediaAsset(user_id=uid,filename='remote.png',mime_type='image/png',storage_key='nova/remote.png'))
        db.commit()
        assert len(erase_plan(db,uid)['blockers'])==2
        with pytest.raises(ValueError):erase_local_account(db,uid,'verified-case-remote',writes_paused=True)
        assert db.get(User,uid).active


def test_cost_model_missing_inputs_never_claims_margin():
    from scripts.unit_economics import scenarios
    missing=scenarios({})
    assert len(missing['scenarios'])==12
    assert all(r['estimated_contribution_gbp'] is None for r in missing['scenarios'])
    supplied={key:0 for key in missing['missing_inputs']};supplied['ai_per_action']=.01
    actual=scenarios(supplied)['scenarios']
    assert Decimal(actual[1]['estimated_monthly_cost_gbp'])>Decimal(actual[0]['estimated_monthly_cost_gbp'])
    assert Decimal(actual[2]['estimated_monthly_cost_gbp'])>Decimal(actual[1]['estimated_monthly_cost_gbp'])


def test_mail_delivery_signals_do_not_store_addresses(monkeypatch):
    from nova.db import MailDelivery
    monkeypatch.setattr(recovery,'smtp_message',lambda *a:None)
    recovery.send_message('private@example.test','Synthetic subject','Private token')
    monkeypatch.setattr(recovery,'smtp_message',lambda *a:(_ for _ in ()).throw(OSError('failure')))
    with pytest.raises(OSError):recovery.send_message('private@example.test','Synthetic subject','Private token')
    with SessionLocal() as db:
        rows=db.scalars(select(MailDelivery)).all()
        assert {'sent','failed'}.issubset({r.status for r in rows})
        assert set(MailDelivery.__table__.columns.keys())=={'id','status','created_at'}


def test_verification_gate_stops_before_provider_and_preserves_access(monkeypatch):
    from nova import billing
    client,uid,*_=account()
    monkeypatch.setenv('EMAIL_VERIFICATION_REQUIRED_FOR_CHECKOUT','true')
    monkeypatch.setattr(billing,'checkout_enabled',lambda:True)
    monkeypatch.setattr(billing,'plans',lambda:{'basic_monthly':'price_synthetic'})
    with SessionLocal() as db:
        with pytest.raises(ValueError,match='Verify your email'):billing.create_checkout(db,db.get(User,uid),'http://testserver','basic_monthly')
    assert client.get('/studio').status_code==200


def test_metrics_do_not_accept_client_claimed_publication(monkeypatch):
    client,*_=account()
    monkeypatch.setenv('PRODUCT_METRICS_ENABLED','true')
    assert client.post('/api/events',json={'kind':'published'}).status_code==404
    assert client.get('/internal/cohorts').status_code==401


def test_usefulness_cannot_cross_brand(monkeypatch):
    from nova.db import Brand
    client,uid,*_=account()
    monkeypatch.setenv('PRODUCT_METRICS_ENABLED','true')
    with SessionLocal() as db:
        brand=Brand(user_id=uid,name='Second');db.add(brand)
        draft=Draft(user_id=uid,brand_id=0,variants_json='{"x":{"posts":["Synthetic"]}}');db.add(draft)
        db.commit();bid=brand.id;did=draft.id
    assert client.post(f'/api/drafts/{did}/useful',headers={'X-Zova-Brand':str(bid)}).status_code==404


def test_shared_upload_erasure_fails_closed():
    from nova.data_lifecycle import erase_plan
    from nova.storage import UPLOAD_DIR
    _,uid,*_=account();_,other,*_=account()
    with SessionLocal() as db:
        for owner in [uid,other]:db.add(MediaAsset(user_id=owner,filename='same.png',mime_type='image/png',storage_key=str(UPLOAD_DIR/'same.png')))
        db.commit()
        assert any('shared' in reason for reason in erase_plan(db,uid)['blockers'])
