"""Synthetic scheduling acceptance for tester BUG-02; no provider requests."""
import json
import pytest
from datetime import timedelta
from sqlalchemy import select
from nova.db import SessionLocal, Draft, Publication, PublishReview, ScheduledPost, utcnow
from test_account_integrity import account
from test_reviewed_publication import prepared, review


def scheduled(platforms=('x',)):
    client, uid, token, body=prepared(platforms)
    approved=review(client,{**body,'scheduled_local':(utcnow()+timedelta(days=3)).isoformat()})
    assert client.post('/api/schedule',json=approved).status_code==200
    return client,body,approved,client.get('/api/schedules').json()


def test_schedule_read_has_editable_context_and_does_not_expose_account_id():
    client,body,_,rows=scheduled()
    assert rows[0]['title']=='Approved text x'
    assert rows[0]['account_name']=='demo'
    assert rows[0]['updated_at'] and rows[0]['draft_revision'] is not None
    assert 'original-x' not in json.dumps(rows)
    assert client.get('/api/schedules',params={'draft_id':body['draft_id']}).json()==rows
    other,*_=account()
    assert other.get('/api/schedules',params={'draft_id':body['draft_id']}).json()==[]


def test_reschedule_changes_only_time_and_stale_cancel_cannot_overwrite():
    client,body,approved,rows=scheduled();row=rows[0]
    with SessionLocal() as db:original=db.get(PublishReview,approved['review_token']).payload_json
    changed=client.post(f"/api/schedules/{row['id']}/reschedule",json={
        'scheduled_local':(utcnow()+timedelta(days=4)).isoformat(),'expected_updated_at':row['updated_at']})
    assert changed.status_code==200
    assert client.post(f"/api/schedules/{row['id']}/cancel",json={'expected_updated_at':row['updated_at']}).status_code==409
    fresh=client.get('/api/schedules').json()[0]
    assert fresh['status']=='scheduled' and fresh['scheduled_at']!=row['scheduled_at']
    with SessionLocal() as db:assert db.get(PublishReview,approved['review_token']).payload_json==original
    assert client.post(f"/api/schedules/{row['id']}/cancel",json={'expected_updated_at':fresh['updated_at']}).status_code==200


def test_edit_stops_every_platform_and_requires_fresh_review(monkeypatch):
    from nova import scheduler
    client,body,approved,rows=scheduled(('x','facebook'))
    draft=client.get(f"/api/drafts/{body['draft_id']}").json()
    with SessionLocal() as db:original=db.get(PublishReview,approved['review_token']).payload_json
    response=client.post(f"/api/schedules/drafts/{body['draft_id']}/edit",json={'revision':draft['revision']})
    assert response.status_code==200 and response.json()['cancelled']==2
    current=client.get(f"/api/drafts/{body['draft_id']}").json()
    assert current['status']=='draft' and current['revision']==draft['revision']+1
    assert current['variants']==draft['variants'] and current['workspace']==draft['workspace']
    assert {r['status'] for r in client.get('/api/schedules').json()}=={'cancelled'}
    with SessionLocal() as db:
        assert db.get(PublishReview,approved['review_token']).payload_json==original
        assert {p.status for p in db.scalars(select(Publication).where(Publication.draft_id==body['draft_id']))}=={'cancelled'}
        for row in db.scalars(select(ScheduledPost).where(ScheduledPost.draft_id==body['draft_id'])):row.scheduled_at=utcnow()-timedelta(seconds=1)
        db.commit()
    monkeypatch.setattr(scheduler,'publish_platform',lambda *a,**k:(_ for _ in ()).throw(AssertionError('Old delivery must never send')))
    scheduler.process_due()
    # Old approval may only return its current result, never schedule again.
    assert client.post('/api/schedule',json=approved).status_code==200
    assert {r['status'] for r in client.get('/api/schedules').json()}=={'cancelled'}
    variants={'x':{'posts':['Edited caption']},'facebook':{'posts':['Edited caption']}}
    assert client.patch(f"/api/drafts/{body['draft_id']}",json={'revision':current['revision'],'variants':variants,'platforms':body['platforms']}).status_code==200
    new_review=review(client,{**body,'variants':variants,'scheduled_local':(utcnow()+timedelta(days=6)).isoformat()})
    assert new_review['review_token']!=approved['review_token']
    assert client.post('/api/schedule',json=new_review).status_code==200


def test_edit_rejects_foreign_owner_and_stale_revision_without_cancelling():
    client,body,_,rows=scheduled();other,*_=account()
    path=f"/api/schedules/drafts/{body['draft_id']}/edit"
    assert other.post(path,json={'revision':rows[0]['draft_revision']}).status_code==404
    assert client.post(path,json={'revision':rows[0]['draft_revision']-1}).status_code==409
    assert client.get('/api/schedules').json()[0]['status']=='scheduled'


def test_edit_cannot_cancel_or_rewrite_unknown_destination():
    client,body,_,rows=scheduled(('x','facebook'))
    with SessionLocal() as db:
        publication=db.scalar(select(Publication).where(Publication.draft_id==body['draft_id'],Publication.platform=='facebook'))
        publication.status='unknown';publication.result_json='{"support_reference":"synthetic-unknown"}';db.commit()
    response=client.post(f"/api/schedules/drafts/{body['draft_id']}/edit",json={'revision':rows[0]['draft_revision']})
    assert response.status_code==409
    assert {r['status'] for r in client.get('/api/schedules').json()}=={'scheduled'}
    assert client.get(f"/api/drafts/{body['draft_id']}").json()['status']=='scheduled'
    with SessionLocal() as db:
        publication=db.scalar(select(Publication).where(Publication.draft_id==body['draft_id'],Publication.platform=='facebook'))
        assert publication.status=='unknown' and 'synthetic-unknown' in publication.result_json


def test_edit_rolls_back_if_worker_already_claimed_one_destination():
    client,body,_,rows=scheduled(('x','facebook'))
    with SessionLocal() as db:job=db.get(ScheduledPost,rows[-1]['id']);job.status='publishing';db.commit()
    assert client.post(f"/api/schedules/drafts/{body['draft_id']}/edit",json={'revision':rows[0]['draft_revision']}).status_code==409
    assert {r['status'] for r in client.get('/api/schedules').json()}=={'scheduled','publishing'}
    assert client.get(f"/api/drafts/{body['draft_id']}").json()['revision']==rows[0]['draft_revision']


def test_cancelled_old_job_cannot_cancel_new_attempt():
    client,body,approved,rows=scheduled();old=rows[0]
    assert client.post(f"/api/schedules/{old['id']}/cancel").status_code==200
    fresh=review(client,{**body,'scheduled_local':(utcnow()+timedelta(days=5)).isoformat()})
    assert client.post('/api/schedule',json=fresh).status_code==200
    assert client.post(f"/api/schedules/{old['id']}/cancel").status_code==409
    with SessionLocal() as db:
        publication=db.scalar(select(Publication).where(Publication.draft_id==body['draft_id']))
        assert publication.status=='scheduled' and publication.review_code==fresh['review_token']


def test_schedule_page_exposes_manage_actions_without_native_js_confirmation():
    client,body,_,_=scheduled()
    html=client.get('/drafts').text
    assert '<h1>Schedule</h1>' in html and 'scheduleCalendar' in html
    assert 'Manage schedule' in html and 'schedule.css' in html
    assert 'onsubmit="return confirm' not in html


@pytest.mark.parametrize('content',['invalid','[]','{"review_code":{"bad":"type"}}','{"publication_id":[],"review_code":"bad"}','{"publication_id":true,"review_code":"bad"}'])
def test_malformed_legacy_record_does_not_hide_calendar_or_allow_cancellation(content):
    client,body,_,rows=scheduled()
    with SessionLocal() as db:
        row=db.get(ScheduledPost,rows[0]['id']);row.content_json=content;db.commit()
    response=client.get('/api/schedules')
    assert response.status_code==200 and len(response.json())==1
    assert client.post(f"/api/schedules/{rows[0]['id']}/cancel").status_code==409
    assert client.post(f"/api/schedules/{rows[0]['id']}/reschedule",json={'scheduled_local':(utcnow()+timedelta(days=5)).isoformat()}).status_code==409
    assert client.get('/api/schedules').json()[0]['status']=='scheduled'


def test_missing_ledger_reference_cannot_report_successful_cancel():
    client,body,_,rows=scheduled()
    with SessionLocal() as db:
        row=db.get(ScheduledPost,rows[0]['id']);content=json.loads(row.content_json)
        content['publication_id']=2147483647;row.content_json=json.dumps(content);db.commit()
    assert client.post(f"/api/schedules/{rows[0]['id']}/cancel").status_code==409
    assert client.get('/api/schedules').json()[0]['status']=='scheduled'
