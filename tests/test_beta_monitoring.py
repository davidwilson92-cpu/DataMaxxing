"""Operational regressions: no provider calls or production credentials."""
from datetime import timedelta

import pytest

from nova.db import SessionLocal, WorkerHeartbeat, utcnow
from scripts.check_service import check


def healthy():
    return {
        'status':'ok', 'database':'reachable', 'checked_at':utcnow().isoformat(),
        'overdue_jobs':0, 'uncertain_publications':0, 'stuck_publications':0,
        'stale_billing_accounts':0, 'old_usage_reservations':0,
        'mail_failures_24h':0, 'stuck_mail':0, 'ai_failures_24h':0,
        'ai_spend':{'threshold_exceeded':False,'unpriced_calls':0},
        'worker':{'mode':'embedded','status':'idle'}, 'recovery_email_configured':True,
    }


def test_monitor_accepts_complete_recent_report():
    assert check(healthy())=={'status':'ok','reasons':[]}


def test_monitor_credential_cannot_dispatch_or_read_customer_cohorts(monkeypatch):
    from test_account_integrity import account
    client,*_=account()
    monkeypatch.setenv('SCHEDULER_SECRET','synthetic-dispatch-secret')
    monkeypatch.setenv('MONITOR_READ_TOKEN','synthetic-read-only-secret')
    headers={'Authorization':'Bearer synthetic-read-only-secret'}
    assert client.get('/internal/ready',headers=headers).status_code==200
    assert client.get('/internal/status',headers=headers).status_code==200
    assert client.get('/internal/cohorts',headers=headers).status_code==401
    assert client.post('/internal/run-due',headers=headers).status_code==401
    assert client.get('/internal/status').status_code==401
    monkeypatch.delenv('MONITOR_READ_TOKEN')
    assert client.get('/internal/status',headers=headers).status_code==401
    assert client.get('/internal/status',headers={'Authorization':'Bearer synthetic-dispatch-secret'}).status_code==200


@pytest.mark.parametrize('url',['http://example.test','https://user:pass@example.test',
                              'https://example.test?secret=x','https://example.test/#token',
                              'https://example.test/not-the-root','file:///private','https://','https://[broken'])
def test_probe_never_sends_credentials_to_invalid_destination(url):
    from scripts.check_service import probe
    calls=[]
    assert probe(url,'synthetic-secret',get=lambda *a,**k:calls.append(a))['status']=='attention'
    assert calls==[]


def test_probe_uses_verified_https_bounded_time_and_no_redirects():
    from scripts.check_service import probe
    calls=[]
    class Response:
        def raise_for_status(self):pass
        def json(self):return healthy()
    def get(url,**kwargs):
        calls.append((url,kwargs));return Response()
    assert probe('https://example.test/','synthetic-secret',get=get)['status']=='ok'
    assert calls==[('https://example.test/internal/status',{
        'headers':{'Authorization':'Bearer synthetic-secret'},'timeout':20,'follow_redirects':False})]
    def fail(*a,**k):raise RuntimeError('private token and provider details')
    assert probe('https://example.test','synthetic-secret',get=fail)=={'status':'attention','reasons':['probe_failed']}


@pytest.mark.parametrize('state',['missing','stale','error','disabled','not_independently_monitored'])
def test_monitor_does_not_hide_worker_failure(state):
    payload=healthy();payload['worker']['status']=state
    assert 'publishing_worker_unhealthy' in check(payload)['reasons']


@pytest.mark.parametrize('payload',[None,[],{}, {'database':'reachable'}, {'worker':None}, {'ai_spend':[]}])
def test_incomplete_status_cannot_report_success(payload):
    assert check(payload)['status']=='attention'


def test_stale_malformed_and_reservation_reports_fail_closed():
    payload=healthy();payload['checked_at']=(utcnow()-timedelta(minutes=10)).isoformat()
    assert 'stale_status_document' in check(payload)['reasons']
    for stamp in ('bad',None,utcnow().replace(tzinfo=None).isoformat()):
        payload['checked_at']=stamp
        assert 'invalid_status_document' in check(payload)['reasons']
    payload=healthy();payload['old_usage_reservations']=1
    assert 'old_usage_reservations' in check(payload)['reasons']
    payload=healthy();payload['status']='attention'
    assert check(payload)['reasons']==['service_attention']
    payload=healthy();payload['overdue_jobs']='0'
    assert check(payload)['status']=='attention'
    payload=healthy();payload['recovery_email_configured']=False
    assert 'recovery_email_unavailable' in check(payload)['reasons']


def test_embedded_poll_records_success_failure_and_age(monkeypatch):
    from nova import scheduler
    from nova.operations import worker_status
    monkeypatch.setenv('ZOVA_SCHEDULER_MODE','embedded')
    monkeypatch.setattr(scheduler,'process_due',lambda:{'published':0,'failed':0})
    assert scheduler.monitored_poll()=={'published':0,'failed':0}
    with SessionLocal() as db:
        row=db.get(WorkerHeartbeat,'publishing')
        assert row.completed_at is not None
        assert worker_status(db)=={'mode':'embedded','status':'idle'}
        row.started_at=utcnow()-timedelta(hours=1);db.commit()
        assert worker_status(db)['status']=='stale'
    def fail():
        raise RuntimeError('synthetic failure')
    monkeypatch.setattr(scheduler,'process_due',fail)
    with pytest.raises(RuntimeError,match='synthetic failure'):
        scheduler.monitored_poll()
    with SessionLocal() as db:
        assert worker_status(db)['status']=='error'
