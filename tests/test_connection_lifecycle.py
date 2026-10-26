import json
from datetime import timedelta
from sqlalchemy import select
from test_account_integrity import account
from nova.db import SessionLocal, SocialConnection, Draft, Publication, PublishReview, ScheduledPost, utcnow
from nova.security import encrypt


def test_unlink_cancels_unsent_work_and_approvals_but_preserves_outcomes():
    client, uid, *_ = account()
    other, other_uid, *_ = account()
    with SessionLocal() as db:
        conn=SocialConnection(user_id=uid, platform='instagram', account_id='synthetic',
                              encrypted_access_token=encrypt('synthetic'), encrypted_refresh_token=encrypt('synthetic'))
        db.add(conn);db.flush();cid=conn.id
        draft_ids={}
        for state in ['scheduled','queued','publishing','pending','unknown','published']:
            draft=Draft(user_id=uid, brief='synthetic', status=state)
            db.add(draft);db.flush();draft_ids[state]=draft.id
            db.add(Publication(user_id=uid,draft_id=draft.id,platform='instagram',connection_id=cid,
                               review_code='synthetic-'+state,status=state,result_json='{"receipt":"keep"}'))
        db.add(ScheduledPost(user_id=uid,draft_id=draft_ids['scheduled'],platform='instagram',
                             connection_id=cid,content_json='{}',scheduled_at=utcnow()+timedelta(days=1)))
        review=PublishReview(code='unlink-review-'+str(cid),user_id=uid,draft_id=draft_ids['scheduled'],
                             revision=1,payload_json=json.dumps({'targets':{'instagram':{'connection_id':cid}}}),
                             expires_at=utcnow()+timedelta(minutes=10))
        db.add(review);db.commit();review_code=review.code
    assert other.post(f'/account/connections/{cid}/unlink').status_code==404
    response=client.post(f'/account/connections/{cid}/unlink',follow_redirects=False)
    assert response.status_code==303 and 'unlinked=1' in response.headers['location']
    with SessionLocal() as db:
        conn=db.get(SocialConnection,cid)
        assert not conn.active and not conn.encrypted_access_token and conn.encrypted_refresh_token is None
        assert db.get(PublishReview,review_code).status=='cancelled'
        job=db.scalar(select(ScheduledPost).where(ScheduledPost.connection_id==cid))
        assert job.status=='cancelled'
        for original,did in draft_ids.items():
            publication=db.scalar(select(Publication).where(Publication.draft_id==did))
            assert publication.status==('cancelled' if original in {'queued','scheduled'} else original)
            assert json.loads(publication.result_json)=={'receipt':'keep'}
        assert db.get(Draft,draft_ids['scheduled']).status=='cancelled'
    # Repeat clicks do not replay work or rewrite the provider receipts.
    assert client.post(f'/account/connections/{cid}/unlink',follow_redirects=False).status_code==303


def test_reconnection_cannot_revive_unused_publication_approval(monkeypatch):
    from test_reviewed_publication import prepared, review
    import nova.app as module
    client,uid,_,body=prepared()
    approved=review(client,body)
    with SessionLocal() as db:
        cid=db.scalar(select(SocialConnection.id).where(SocialConnection.user_id==uid))
    assert client.post(f'/account/connections/{cid}/unlink',follow_redirects=False).status_code==303
    with SessionLocal() as db:
        conn=db.get(SocialConnection,cid)
        conn.active=True;conn.encrypted_access_token=encrypt('replacement-synthetic');db.commit()
    calls=[]
    monkeypatch.setattr(module,'publish_platform',lambda *a,**k:calls.append(1))
    assert client.post('/api/publish',json=approved).status_code==409
    assert not calls
