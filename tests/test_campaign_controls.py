import json
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from nova import ai, allowances
from nova.db import (Brand, Campaign, ContentSeries, Draft, Publication, ScheduledPost,
                     SeriesOccurrence, SessionLocal, utcnow)
from test_account_integrity import account
from test_campaign_refinement import plan


def view(client, base):
    response = client.get(base)
    assert response.status_code == 200, response.text
    return response.json()


def control(client, base, action, **kwargs):
    current = view(client, base)
    return client.post(base+'/control', json=dict(revision=current['revision'], snapshot=current['control_snapshot'],
                                                 action=action, **kwargs))


def improve(client, base, **kwargs):
    return client.post(base.replace('/api/campaigns/', '/api/ai/campaigns/')+'/improve',
                       json=dict(revision=view(client, base)['revision'], **kwargs))


def apply(client, base, action='apply'):
    return client.post(base+'/suggestion', json=dict(revision=view(client, base)['revision'], action=action))


def future(days=8):
    return (utcnow()+timedelta(days=days)).strftime('%Y-%m-%dT12:00')


def test_pause_resume_keeps_drafts_and_does_not_reschedule(plan):
    client, uid, base, _ = plan
    ids = client.post(base+'/accept', json={'revision':2}).json()['draft_ids']
    with SessionLocal() as db:
        db.get(Draft, ids[0]).status = 'scheduled'
        db.add(ScheduledPost(user_id=uid, draft_id=ids[0], platform='instagram', content_json='{}', scheduled_at=utcnow()+timedelta(days=3)))
        db.commit()
    paused = control(client, base, 'pause')
    assert paused.status_code == 200, paused.text
    assert paused.json()['state'] == 'paused'
    assert all(p['status'] == 'draft' for p in paused.json()['posts'])
    assert all(p['editable'] for p in paused.json()['posts'])
    assert control(client, base, 'resume').json()['state'] == 'active'
    with SessionLocal() as db:
        assert not db.scalar(select(ScheduledPost.id).where(ScheduledPost.draft_id.in_(ids),ScheduledPost.status=='scheduled'))
        assert all(db.get(Draft,i).status == 'draft' for i in ids)


@pytest.mark.parametrize('status', ['publishing', 'unknown', 'pending', 'partial', 'needs_review'])
def test_unresolved_campaign_cannot_pause_or_move(plan, status):
    client, uid, base, _ = plan
    ids = client.post(base+'/accept', json={'revision':2}).json()['draft_ids']
    with SessionLocal() as db:
        db.get(Draft,ids[1]).status=status;db.commit()
    before = view(client,base)
    assert control(client,base,'pause').status_code == 409
    assert control(client,base,'move',start=future()).status_code == 409
    assert view(client,base) == before


def test_atomic_pause_rolls_back_when_job_started_without_draft_update(plan):
    client,uid,base,_=plan
    ids=client.post(base+'/accept',json={'revision':2}).json()['draft_ids']
    with SessionLocal() as db:
        for did,status in zip(ids,['scheduled','publishing']):
            db.get(Draft,did).status='scheduled'
            db.add(ScheduledPost(user_id=uid,draft_id=did,platform='x',content_json='{}',status=status,scheduled_at=utcnow()+timedelta(days=3)))
        db.commit()
    before=view(client,base)
    assert control(client,base,'pause').status_code==409
    assert view(client,base)==before
    with SessionLocal() as db:
        assert db.scalar(select(ScheduledPost.status).where(ScheduledPost.draft_id==ids[0]))=='scheduled'


def test_move_remaining_preserves_sent_and_warns_date_sensitive_caption(plan):
    client,uid,base,_=plan
    ids=client.post(base+'/accept',json={'revision':2}).json()['draft_ids']
    with SessionLocal() as db:
        db.get(Draft,ids[0]).status='published'
        db.get(Draft,ids[1]).variants_json=json.dumps({'x':{'posts':['Friday offer, tonight only.']}})
        db.commit()
    before=view(client,base)
    moved=control(client,base,'move',start=future())
    assert moved.status_code==200,moved.text
    after=moved.json()
    assert after['dates'][0]==before['dates'][0]
    assert after['dates'][1]['local'][:16]==future()
    assert 'timing_warning' in after['posts'][1]
    assert after['posts'][0]['status']=='published'


def test_reuse_is_separate_idempotent_and_retains_original(plan):
    client,uid,base,_=plan
    ids=client.post(base+'/accept',json={'revision':2}).json()['draft_ids']
    before=view(client,base)
    payload=dict(revision=before['revision'],name='Next launch',start=future(),request_key=str(uuid4()))
    copied=client.post(base+'/reuse',json=payload)
    assert copied.status_code==200,copied.text
    copy=copied.json()
    assert copy['id']!=before['id'] and copy['draft_ids']==[] and copy['name']=='Next launch'
    assert copy['dates'][0]['local'][:16]==future()
    assert [p['caption'] for p in copy['posts']]==[p['caption'] for p in before['posts']]
    assert client.post(base+'/reuse',json=payload).json()['id']==copy['id']
    assert view(client,base)['draft_ids']==ids
    assert not copy.get('suggestion')
    with SessionLocal() as db:
        assert len(db.scalars(select(Campaign).where(Campaign.user_id==uid)).all())==2


def test_reuse_rejects_removed_or_multi_platform_posts(plan):
    client,uid,base,_=plan
    ids=client.post(base+'/accept',json={'revision':2}).json()['draft_ids']
    with SessionLocal() as db:
        db.get(Draft,ids[0]).platforms_json='["instagram","facebook"]';db.commit()
    row=view(client,base)
    response=client.post(base+'/reuse',json=dict(revision=row['revision'],name='Copy',start=future(),request_key=str(uuid4())))
    assert response.status_code==409


def test_improvement_is_saved_preview_then_applies_once(plan,monkeypatch):
    client,uid,base,_=plan
    ids=client.post(base+'/accept',json={'revision':2}).json()['draft_ids']
    captured=[]
    def generated(prompt,**kw):
        captured.append(prompt)
        return json.dumps({'posts':[{'caption':'A hands-on demo.'},{'caption':'What would you try first?'}]})
    monkeypatch.setattr(ai,'editorial_response',generated)
    before=view(client,base)
    proposed=improve(client,base)
    assert proposed.status_code==200,proposed.text
    row=proposed.json()
    assert [p['caption'] for p in row['posts']]==[p['caption'] for p in before['posts']]
    assert 'No usable performance' in row['suggestion']['basis']
    assert all(word in captured[0] for word in ['strategy','voice','performance','creator','Launch Zova'])
    assert view(client,base)['suggestion']==row['suggestion']
    accepted=apply(client,base)
    assert accepted.status_code==200,accepted.text
    assert accepted.json()['posts'][0]['caption']=='A hands-on demo.'
    assert not accepted.json().get('suggestion')
    assert apply(client,base).status_code==409
    with SessionLocal() as db:
        assert db.get(Draft,ids[0]).status=='draft'
        assert not db.scalar(select(ScheduledPost.id).where(ScheduledPost.user_id==uid))


@pytest.mark.parametrize('change',['caption','status','series'])
def test_suggestions_cannot_overwrite_concurrent_changes(plan,change):
    client,uid,base,_=plan
    ids=client.post(base+'/accept',json={'revision':2}).json()['draft_ids']
    assert improve(client,base).status_code==200
    with SessionLocal() as db:
        d=db.get(Draft,ids[0])
        if change=='caption':d.revision+=1;d.variants_json=json.dumps({'instagram':{'posts':['Owner edit']}})
        elif change=='status':d.status='published'
        else:
            s=db.scalar(select(ContentSeries).where(ContentSeries.user_id==uid));s.revision+=1
        db.commit()
    assert apply(client,base).status_code==409
    assert apply(client,base,'discard').status_code==200


def test_improvement_during_model_call_conflicts_and_consent_blocks_before_model(plan,monkeypatch):
    client,uid,base,_=plan
    ids=client.post(base+'/accept',json={'revision':2}).json()['draft_ids']
    def generated(*a,**k):
        with SessionLocal() as db:
            db.get(Draft,ids[0]).revision+=1;db.commit()
        return json.dumps({'posts':[{'caption':'New first'},{'caption':'Other second'}]})
    monkeypatch.setattr(ai,'editorial_response',generated)
    assert improve(client,base).status_code==409
    assert not view(client,base).get('suggestion')
    monkeypatch.setenv('ZOVA_AI_CONSENT_REQUIRED','true')
    monkeypatch.setattr(ai,'editorial_response',lambda *a,**k:pytest.fail('Model called without consent'))
    assert improve(client,base).status_code==403


def test_extend_review_saves_new_canonical_drafts_without_publishing(plan,monkeypatch):
    client,uid,base,_=plan
    monkeypatch.setattr(ai,'editorial_response',lambda *a,**k:json.dumps({'posts':[{'caption':'Watch a demonstration.'},{'caption':'Your next step starts here.'}]}))
    ids=client.post(base+'/accept',json={'revision':2}).json()['draft_ids']
    assert improve(client,base,mode='extend',count=2,start=future()).status_code==200
    row=apply(client,base).json()
    assert len(row['posts'])==len(row['draft_ids'])==4,row
    assert row['draft_ids'][:2]==ids
    with SessionLocal() as db:
        assert all(db.get(Draft,i).status=='draft' for i in row['draft_ids'])
        assert not db.scalar(select(ScheduledPost.id).where(ScheduledPost.user_id==uid))
    assert improve(client,base,mode='extend',count=2,start=future(1)).status_code==400


def test_controls_reject_stale_snapshot_and_cross_workspace(plan,monkeypatch):
    client,uid,base,_=plan
    row=view(client,base)
    body=dict(revision=row['revision'],snapshot=row['control_snapshot'],action='pause')
    assert client.post(base+'/control',json=body).status_code==200
    assert client.post(base+'/control',json=body).status_code==409
    other,*_=account()
    assert other.post(base+'/control',json=body).status_code==404
    assert other.post(base.replace('/api/campaigns/','/api/ai/campaigns/')+'/improve',json={'revision':row['revision']}).status_code==404
    with SessionLocal() as db:
        brand=Brand(user_id=uid,name='Other');db.add(brand);db.commit();bid=brand.id
    assert client.post(base+'/control',headers={'X-Zova-Brand':str(bid)},json=body).status_code==404
    monkeypatch.setattr(allowances,'tier',lambda db,u:None)
    assert client.post(base+'/control',json=body).status_code==402


def test_improve_scheduled_draft_only_unschedules_on_apply(plan):
    client,uid,base,_=plan
    did=client.post(base+'/accept',json={'revision':2}).json()['draft_ids'][0]
    with SessionLocal() as db:
        db.get(Draft,did).status='scheduled'
        db.add(ScheduledPost(user_id=uid,draft_id=did,platform='instagram',content_json='{}',scheduled_at=utcnow()+timedelta(days=3)))
        db.commit()
    assert improve(client,base).status_code==200
    assert view(client,base)['posts'][0]['status']=='scheduled'
    assert apply(client,base,'discard').status_code==200
    assert view(client,base)['posts'][0]['status']=='scheduled'
    assert improve(client,base).status_code==200
    result=apply(client,base)
    assert result.status_code==200,result.text
    assert result.json()['posts'][0]['status']=='draft'


def test_model_failure_and_repetition_preserve_originals_and_prior_preview(plan,monkeypatch):
    client,uid,base,_=plan
    assert improve(client,base).status_code==200
    before=view(client,base)
    calls=[]
    def repeat(*args,**kwargs):
        calls.append(1)
        return json.dumps({'posts':[{'caption':'The same caption twice.'}]*2})
    monkeypatch.setattr(ai,'editorial_response',repeat)
    assert improve(client,base).status_code==502
    assert len(calls)==2
    assert view(client,base)==before
    assert improve(client,base,mode='extend',count=2,start=future()).status_code==502


def test_move_rejects_bad_dst_and_preserves_wall_clock_across_dst(plan):
    client,uid,base,_=plan
    before=view(client,base)
    assert control(client,base,'move',start='2027-03-28T01:30').status_code==400
    assert view(client,base)==before
    # Explicitly future winter-to-summer boundary; both local noon slots stay noon.
    moved=control(client,base,'move',start='2027-03-27T12:00')
    assert moved.status_code==200,moved.text
    assert [d['local'][11:16] for d in moved.json()['dates']]==['12:00','12:00']
    assert [d['utc'][11:16] for d in moved.json()['dates']]==['12:00','11:00']


def test_pause_before_accept_keeps_series_paused_and_blocks_publish_review(plan):
    from nova.series import approval_guard
    from fastapi import HTTPException
    client,uid,base,_=plan
    paused=control(client,base,'pause').json()
    ids=client.post(base+'/accept',json={'revision':paused['revision']}).json()['draft_ids']
    assert view(client,base)['state']=='paused'
    with SessionLocal() as db:
        with pytest.raises(HTTPException):approval_guard(db,ids[0])


def test_reuse_changed_retry_body_does_not_silently_return_wrong_copy(plan):
    client,uid,base,_=plan
    row=view(client,base)
    body=dict(revision=row['revision'],name='Copy',start=future(),request_key=str(uuid4()))
    assert client.post(base+'/reuse',json=body).status_code==200
    assert client.post(base+'/reuse',json=dict(body,name='Different copy')).status_code==409
