import hashlib
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import delete, select
from fastapi.testclient import TestClient
from nova import app as app_module, data_lifecycle
from nova.account_deletion import initiate
from nova.deletion_operator import execute_receipt, plan_receipt, resolve_receipt
from nova.deletion_policy import timing
from nova.db import (AICall, BillingAccount, DeletionRequest, Draft, MediaAsset, Publication,
                     ScheduledPost, SessionLocal, SocialConnection, User, WorkerHeartbeat, utcnow)
from nova.security import encrypt, hash_api_key
from nova.storage import UPLOAD_DIR
from test_account_integrity import account


@pytest.fixture(autouse=True)
def isolate_operator_global_state():
    """These tests commit deliberately; restore process-wide worker/queue state.

    The shared test database may already contain a worker heartbeat. It must not
    masquerade as a worker running during this test's synthetic maintenance
    window. Conversely, refusal cases must not leave deliverable jobs for later
    scheduler tests or synthetic failures in the operations counters.
    """
    observed = (ScheduledPost, Publication, AICall, DeletionRequest)
    with SessionLocal() as db:
        existing = {model: set(db.scalars(select(model.__mapper__.primary_key[0])))
                    for model in observed}
        heartbeat = db.get(WorkerHeartbeat, 'publishing')
        saved_heartbeat = ({column.key: getattr(heartbeat, column.key)
                            for column in WorkerHeartbeat.__table__.columns}
                           if heartbeat is not None else None)
        if heartbeat is not None:
            db.delete(heartbeat)
        db.commit()
    try:
        yield
    finally:
        with SessionLocal() as db:
            for model, keys in existing.items():
                primary_key = model.__mapper__.primary_key[0]
                new_keys = set(db.scalars(select(primary_key))) - keys
                if new_keys:
                    db.execute(delete(model).where(primary_key.in_(new_keys)))
            db.execute(delete(WorkerHeartbeat).where(WorkerHeartbeat.role == 'publishing'))
            if saved_heartbeat is not None:
                db.add(WorkerHeartbeat(**saved_heartbeat))
            db.commit()


def requested():
    client,uid,_,_=account()
    with SessionLocal() as db:code=initiate(db,uid,'old-password-123')
    return client,uid,code


def proof():
    return {'account_erasure_mode':True,'scheduler_mode':'disabled','started_at':(utcnow()-timedelta(minutes=6)).isoformat()}


def maintenance(monkeypatch):
    monkeypatch.setenv('ZOVA_MAINTENANCE_MODE','account-erasure')
    monkeypatch.setenv('ZOVA_SCHEDULER_MODE','disabled')


def execute(db,code,case='synthetic-delete-case'):
    return execute_receipt(db,code,case,proof(),services_drained=True,retention_reviewed=True)


def test_receipt_has_david_seven_day_target_overdue_and_no_false_completion(monkeypatch):
    _,uid,code=requested()
    with SessionLocal() as db:
        receipt=db.get(DeletionRequest,code);receipt.created_at=utcnow()-timedelta(days=8);db.commit()
        value=timing(receipt)
        assert value['owner']=='David' and value['target_days']==7 and value['overdue']
        assert value['completed_at'] is None
        plan=plan_receipt(db,code)
        assert plan['user_id']==uid and plan['mutation']=='none' and not plan['blockers']
    response=TestClient(app_module.app).get('/data-deletion/status/'+code)
    assert 'Managed by David' in response.text and 'target date has passed' in response.text
    assert 'not yet been erased' in response.text and 'Verified completion:' not in response.text
    monkeypatch.setenv('SCHEDULER_SECRET','operator-secret')
    result=TestClient(app_module.app).get('/internal/deletions',headers={'Authorization':'Bearer operator-secret'}).json()
    item=next(r for r in result['requests'] if r['code']==code)
    assert item['owner']=='David' and item['overdue'] and result['overdue_deletion_requests']>=1
    assert 'subject_hash' not in str(result) and 'email' not in str(result['requests'])


def test_maintenance_is_default_off_and_blocks_writers_not_receipts(monkeypatch):
    client,_,_,_=account();_,_,code=requested()
    monkeypatch.delenv('ZOVA_MAINTENANCE_MODE',raising=False)
    assert client.get('/studio').status_code==200
    maintenance(monkeypatch)
    for method,path in [('get','/studio'),('post','/signup'),('post','/billing/webhook'),('get','/callback/instagram'),('post','/internal/run')]:
        response=getattr(client,method)(path)
        assert response.status_code==503 and response.headers['Retry-After']=='300'
    assert client.get('/health').status_code==200
    assert client.get('/data-deletion/status/'+code).status_code==200
    monkeypatch.setenv('MONITOR_READ_TOKEN','monitor');monkeypatch.setenv('SCHEDULER_SECRET','operator')
    assert client.get('/internal/maintenance',headers={'Authorization':'Bearer monitor'}).status_code==401
    value=client.get('/internal/maintenance',headers={'Authorization':'Bearer operator'}).json()
    assert value['account_erasure_mode'] and value['scheduler_mode']=='disabled'
    monkeypatch.delenv('ZOVA_MAINTENANCE_MODE')
    assert client.get('/studio').status_code==200


def test_operator_rejects_unverified_receipts_and_missing_drain_proof(monkeypatch):
    _,uid,code=requested()
    with SessionLocal() as db:
        with pytest.raises(ValueError,match='maintenance'):execute(db,code)
        maintenance(monkeypatch)
        with pytest.raises(ValueError,match='confirmations'):execute_receipt(db,code,'synthetic-case',proof())
        with pytest.raises(ValueError,match='five minutes'):
            execute_receipt(db,code,'synthetic-case',{**proof(),'started_at':utcnow().isoformat()},services_drained=True,retention_reviewed=True)
        with pytest.raises(ValueError,match='Running service'):
            execute_receipt(db,code,'synthetic-case',{**proof(),'account_erasure_mode':False},services_drained=True,retention_reviewed=True)
        fake=DeletionRequest(code='0'*64,subject_hash='unknown',status='connection_removed');db.add(fake);db.commit()
        with pytest.raises(ValueError,match='verified'):resolve_receipt(db,fake.code)
        assert db.get(DeletionRequest,code).completed_at is None


@pytest.mark.parametrize('model',[Publication,ScheduledPost])
@pytest.mark.parametrize('status',['scheduled','queued','publishing','pending','unknown'])
def test_operator_refuses_all_unresolved_deliveries(monkeypatch,model,status):
    _,uid,code=requested();maintenance(monkeypatch)
    with SessionLocal() as db:
        draft=Draft(user_id=uid,brief='Private');conn=SocialConnection(user_id=uid,platform='x',account_id='private-id',encrypted_access_token=encrypt('secret'))
        db.add_all([draft,conn]);db.flush()
        fields=dict(user_id=uid,draft_id=draft.id,connection_id=conn.id,platform='x',status=status)
        row=model(**fields,**({'review_code':'synthetic'} if model is Publication else {'content_json':'{}','scheduled_at':utcnow()}))
        db.add(row);db.commit()
        with pytest.raises(ValueError,match='publishing outcomes'):execute(db,code)
        assert db.get(Draft,draft.id).brief=='Private'
        assert db.get(DeletionRequest,code).status=='access_revoked'


def test_operator_refuses_active_billing_remote_or_shared_storage(monkeypatch):
    _,uid,code=requested();_,other,_,_=account();maintenance(monkeypatch)
    with SessionLocal() as db:
        bill=BillingAccount(key=f'{uid}:test',user_id=uid,mode='test',status='active')
        asset=MediaAsset(user_id=uid,filename='secret.mp4',mime_type='video/mp4',storage_key='nova/remote-object')
        db.add_all([bill,asset]);db.commit()
        blockers=plan_receipt(db,code)['blockers']
        assert any('subscriptions' in b for b in blockers) and any('Remote' in b for b in blockers)
        with pytest.raises(ValueError):execute(db,code)
        bill.status='canceled'
        path=UPLOAD_DIR/f'erasure-shared-{uid}.mp4';path.write_bytes(b'private')
        asset.storage_key=str(path)
        foreign=MediaAsset(user_id=other,filename='other.mp4',mime_type='video/mp4',storage_key=str(UPLOAD_DIR/'alias'/'..'/path.name))
        db.add(foreign);db.commit()
        with pytest.raises(ValueError,match='shared'):execute(db,code)
        assert path.exists()


def test_file_failure_never_completes_and_retry_is_safe(monkeypatch):
    _,uid,code=requested();maintenance(monkeypatch)
    path=UPLOAD_DIR/f'erasure-failure-{uid}.png';path.write_bytes(b'private')
    with SessionLocal() as db:
        db.add(MediaAsset(user_id=uid,filename='private.png',mime_type='image/png',storage_key=str(path),size_bytes=7,analysis_json='{"private":"observation"}'));db.commit()
        original=Path.unlink
        def fail(target,*args,**kwargs):
            if target==path:raise OSError('synthetic file lock')
            return original(target,*args,**kwargs)
        monkeypatch.setattr(Path,'unlink',fail)
        with pytest.raises(OSError):execute(db,code)
        db.rollback();db.expire_all()
        assert db.get(DeletionRequest,code).status=='erasing' and db.get(DeletionRequest,code).completed_at is None
        assert path.exists()
        monkeypatch.setattr(Path,'unlink',original)
        result=execute(db,code,'different-case-after-file-failure')
        assert result['status']=='active_store_erased' and result['receipt']==code and not path.exists()


@pytest.mark.parametrize('failure',['commit','readback'])
def test_cleanup_failure_is_pending_then_changed_case_retry_completes_once(monkeypatch,failure):
    _,uid,code=requested();maintenance(monkeypatch)
    with SessionLocal() as db:
        draft=Draft(user_id=uid,brief='private caption');db.add(draft);db.commit()
        original_commit=db.commit;original_verify=data_lifecycle.verify_active_erasure
        calls=0
        def fail_commit():
            nonlocal calls
            calls+=1
            if calls==2:raise RuntimeError('synthetic cleanup commit failure')
            return original_commit()
        if failure=='commit':monkeypatch.setattr(db,'commit',fail_commit)
        else:monkeypatch.setattr(data_lifecycle,'verify_active_erasure',lambda *a,**k:(_ for _ in ()).throw(ValueError('synthetic verification failure')))
        with pytest.raises((RuntimeError,ValueError)):execute(db,code)
        db.rollback();db.expire_all()
        receipt=db.get(DeletionRequest,code)
        assert receipt.status=='erasing' and receipt.completed_at is None
        monkeypatch.setattr(db,'commit',original_commit);monkeypatch.setattr(data_lifecycle,'verify_active_erasure',original_verify)
        result=execute(db,code,'new-case-after-interruption')
        assert result['receipt']==code and result['completed_at']
        assert db.get(Draft,draft.id).brief==''
        receipts=db.scalars(select(DeletionRequest).where(DeletionRequest.subject_hash==hash_api_key(f'account:{uid}'))).all()
        assert len(receipts)==1 and receipts[0].status=='active_store_erased'
        result2=execute(db,code,'another-idempotent-case')
        assert result2['receipt']==code and result2['status']=='active_store_erased'


def test_recent_worker_heartbeat_refuses_erasure(monkeypatch):
    _,_,code=requested();maintenance(monkeypatch)
    with SessionLocal() as db:
        old=db.get(WorkerHeartbeat,'publishing')
        saved={key:getattr(old,key) for key in ['started_at','completed_at','status']} if old else None
        if old is None:old=WorkerHeartbeat(role='publishing');db.add(old)
        old.started_at=utcnow();old.status='running';db.commit()
        try:
            with pytest.raises(ValueError,match='worker ran'):execute(db,code)
        finally:
            if saved:
                for key,value in saved.items():setattr(old,key,value)
            else:db.delete(old)
            db.commit()


def test_success_and_returned_ai_calls_are_not_operational_failures(monkeypatch):
    monkeypatch.setenv('SCHEDULER_SECRET','ops')
    client=TestClient(app_module.app);headers={'Authorization':'Bearer ops'}
    before=client.get('/internal/status',headers=headers).json()['ai_failures_24h']
    import uuid
    with SessionLocal() as db:
        for status in ['returned','success','failed']:
            db.add(AICall(id=uuid.uuid4().hex,model='synthetic',status=status))
        db.commit()
    assert client.get('/internal/status',headers=headers).json()['ai_failures_24h']==before+1


def test_legacy_operator_receipt_is_completed_but_platform_receipt_not_touched(monkeypatch):
    _,uid,code=requested();maintenance(monkeypatch)
    with SessionLocal() as db:
        subject=hashlib.sha256(str(uid).encode()).hexdigest()
        legacy=DeletionRequest(code=hashlib.sha256(f'{uid}:prior-helper-case'.encode()).hexdigest(),subject_hash=subject,status='erasing')
        platform=DeletionRequest(code='legacy-platform-token-url-safe',subject_hash=subject,status='received')
        db.add_all([legacy,platform]);db.commit()
        assert execute(db,code)['receipt']==code
        assert db.get(DeletionRequest,legacy.code).status=='active_store_erased'
        assert db.get(DeletionRequest,platform.code).status=='received'


def test_operator_cli_requires_exact_confirmation_and_reports_same_receipt(monkeypatch,capsys):
    from scripts import process_deletion
    import os
    monkeypatch.setenv('ZOVA_SCHEMA_MODE',os.environ.get('ZOVA_SCHEMA_MODE','initialize'))
    _,_,code=requested();maintenance(monkeypatch)
    monkeypatch.setenv('UPLOAD_DIR',str(UPLOAD_DIR.resolve()))
    monkeypatch.setattr(process_deletion,'maintenance_proof',lambda host:proof())
    assert process_deletion.main(['plan','--receipt',code])==0
    assert '"mutation": "none"' in capsys.readouterr().out
    with pytest.raises(SystemExit):process_deletion.main(['execute','--receipt',code,'--confirm-receipt','wrong'])
    capsys.readouterr()
    assert process_deletion.main(['execute','--receipt',code,'--confirm-receipt',code,
        '--case','synthetic-cli-case','--expected-host','zova-social.com',
        '--confirm-services-drained','--confirm-retention-reviewed'])==0
    output=capsys.readouterr().out
    assert code in output and 'active_store_erased' in output and 'old-password' not in output


def test_cli_maintenance_proof_has_no_redirect_or_unexpected_host(monkeypatch):
    from scripts import process_deletion
    import httpx
    monkeypatch.setenv('PUBLIC_BASE_URL','https://zova.example')
    monkeypatch.setenv('SCHEDULER_SECRET','synthetic-secret')
    with pytest.raises(ValueError,match='expected'):process_deletion.maintenance_proof('other.example')
    def get(url,**kwargs):
        assert url=='https://zova.example/internal/maintenance'
        assert kwargs['follow_redirects'] is False
        assert kwargs['headers']['Authorization']=='Bearer synthetic-secret'
        return httpx.Response(302,headers={'Location':'https://foreign.example'})
    monkeypatch.setattr(httpx,'get',get)
    with pytest.raises(ValueError,match='no erasure was started'):process_deletion.maintenance_proof('zova.example')


def test_maintenance_cannot_start_with_enabled_scheduler(monkeypatch):
    from nova.runtime import validate_runtime
    monkeypatch.setenv('ZOVA_MAINTENANCE_MODE','account-erasure')
    monkeypatch.setenv('ZOVA_SCHEDULER_MODE','embedded')
    with pytest.raises(ValueError,match='disabled scheduling'):validate_runtime()
