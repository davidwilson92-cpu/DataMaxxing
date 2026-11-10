import json
from datetime import timedelta
import pytest
from sqlalchemy import select
from nova import ai, allowances
from nova.campaign_review import campaign_results
from nova.db import Activity, Draft, SessionLocal, utcnow
from test_account_integrity import account
from test_campaigns import brief


@pytest.fixture
def plan(monkeypatch):
    client, uid, *_ = account()
    monkeypatch.setattr(allowances,'tier',lambda db,uid:'premium')
    row = client.post('/api/campaigns',json=brief()).json()
    monkeypatch.setattr(ai,'editorial_response',lambda *a,**kw:json.dumps({'posts':[{'caption':'First'},{'caption':'Second'}]}))
    base = '/api/campaigns/'+str(row['id'])
    generated = client.post('/api/ai/campaigns/'+str(row['id'])+'/plan',json={'revision':1}).json()
    return client,uid,base,generated


def test_edit_proposal_then_midflight_without_modifying_sent_post(plan):
    client,uid,base,generated=plan
    local=generated['dates'][0]['local'][:16]
    edit=dict(caption='First edit',platform='facebook',local_time=local,revision=2)
    assert client.post(base+'/posts/0',json=edit).json()['posts'][0]['platform']=='facebook'
    assert client.post(base+'/posts/0',json=edit).status_code==409
    accepted=client.post(base+'/accept',json={'revision':3}).json()
    sent,upcoming=accepted['draft_ids']
    with SessionLocal() as db:
        db.get(Draft,sent).status='published'; db.commit()
    view=client.get(base).json()
    assert not view['posts'][0]['editable']
    next_post=view['posts'][1]
    edit.update(caption='Friday offer',revision=view['revision'],draft_revision=next_post['draft_revision'],
                series_revision=next_post['series_revision'],local_time=(utcnow()+timedelta(days=6)).strftime('%Y-%m-%dT11:00'))
    assert client.post(base+'/posts/0',json=edit).status_code==409
    assert client.post(base+'/posts/1',json=dict(edit,draft_revision=999)).status_code==409
    response=client.post(base+'/posts/1',json=edit)
    assert response.status_code==200,response.text
    assert response.json()['dates'][1]['local'][:16]==edit['local_time']
    with SessionLocal() as db:
        assert json.loads(db.get(Draft,upcoming).variants_json)=={'facebook':{'posts':['Friday offer']}}
        assert db.get(Draft,sent).status=='published'
    other,*_=account()
    assert other.get(base).status_code==404
    assert other.post(base+'/posts/1',json=edit).status_code==404


def test_campaign_metrics_require_exact_platform_and_provider_id(plan):
    client,uid,base,_=plan
    ids=client.post(base+'/accept',json={'revision':2}).json()['draft_ids']
    with SessionLocal() as db:
        for did,platform in zip(ids,['instagram','x']):
            db.add(Activity(user_id=uid,draft_id=did,platform=platform,platform_post_id='123',status='published'))
        db.commit()
        post=dict(id='123',platform='x',text='Same caption',views=0,likes=2,comments=0,shares=None)
        view=dict(window_start=(utcnow()-timedelta(days=7)).isoformat(),sample_posts=[post,dict(post,id='456')])
        row=campaign_results(db,uid,view)[0]
        assert (row['published'],row['measured'],row['likes'])==(2,1,None)
        view['sample_posts'].append(dict(post,platform='instagram'))
        row=campaign_results(db,uid,view)[0]
        assert (row['likes'],row['views'],row['shares'])==(4,0,None)


def test_scheduled_time_edit_retains_delivery_and_rejects_stale_or_started_job(plan):
    from nova.db import ScheduledPost
    client,uid,base,_=plan
    did=client.post(base+'/accept',json={'revision':2}).json()['draft_ids'][0]
    with SessionLocal() as db:
        db.get(Draft,did).status='scheduled'
        db.add(ScheduledPost(user_id=uid,draft_id=did,platform='instagram',content_json='{}',
                             scheduled_at=utcnow()+timedelta(days=3)))
        db.commit()
    post=client.get(base).json()['posts'][0]
    assert not post['editable'] and post['status']=='scheduled'
    endpoint='/api/schedules/'+str(post['schedule']['id'])+'/reschedule'
    payload=dict(timezone='America/New_York',scheduled_local=(utcnow()+timedelta(days=5)).strftime('%Y-%m-%dT09:30'),
                 expected_updated_at=post['schedule']['updated_at'])
    assert client.post(endpoint,json=payload).status_code==200
    assert client.post(endpoint,json=payload).status_code==409
    with SessionLocal() as db:
        assert db.get(Draft,did).status=='scheduled'
        job=db.get(ScheduledPost,post['schedule']['id']);job.status='publishing';db.commit()
    assert client.post('/api/schedules/drafts/'+str(did)+'/edit',json={'revision':post['draft_revision']}).status_code==409


def test_tiktok_receipt_is_never_a_measured_post_id(plan):
    client,uid,base,_=plan
    did=client.post(base+'/accept',json={'revision':2}).json()['draft_ids'][0]
    with SessionLocal() as db:
        log=Activity(user_id=uid,draft_id=did,platform='tiktok',platform_post_id='receipt',status='published')
        db.add(log);db.commit()
        view=dict(window_start=(utcnow()-timedelta(days=7)).isoformat(),
                  sample_posts=[dict(platform='tiktok',id='receipt',views=999),dict(platform='tiktok',id='732',views=2)])
        assert campaign_results(db,uid,view)[0]['views'] is None
        log.url='https://www.tiktok.com/@test/video/732';db.commit()
        assert campaign_results(db,uid,view)[0]['views']==2
