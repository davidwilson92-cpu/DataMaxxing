import json
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from nova.app import app
from nova.db import Brand, Draft, MediaAsset, Publication, PublishReview, ScheduledPost, SessionLocal, utcnow
from nova.recommendation_basis import evidence_basis
from nova.publication_status import summary, guidance
from test_account_integrity import account
from test_media_export import asset
from test_next_move_intelligence import connect


def library(client, **params):
    r=client.get('/api/media/library', params=params)
    assert r.status_code == 200, r.text
    assert r.headers['cache-control'] == 'no-store'
    return r.json()


def test_library_owner_workspace_keyset_search_and_no_mutation():
    c, uid, *_=account(); other, oid, *_=account()
    first=asset(uid); second=asset(uid); alien=asset(oid)
    with SessionLocal() as db:
        brand=Brand(user_id=uid,name='Other workspace');db.add(brand);db.commit();bid=brand.id
        db.get(MediaAsset,first).filename='bouquet_100%.mp4';db.commit()
    branded=asset(uid,bid)
    assert TestClient(app).get('/api/media/library').status_code==401
    assert [a['id'] for a in library(c,limit=1)['assets']]==[second]
    assert library(c,limit=1)['next_before']==second
    assert [a['id'] for a in library(c,before=second)['assets']]==[first]
    assert [a['id'] for a in library(c,q='100%')['assets']]==[first]
    assert library(c,kind='image')['assets']==[]
    assert [a['id'] for a in library(c,workspace=bid)['assets']]==[branded]
    assert [a['id'] for a in library(other)['assets']]==[alien]
    assert other.get('/api/media/library',params={'workspace':bid}).status_code in (403,404)
    item=library(c)['assets'][0]
    assert item['states']==['unused'] and not item['uses']
    assert not {'storage_key','public_url','analysis_json'} & item.keys()
    assert c.get('/api/media/library?limit=51').status_code==422
    assert c.get('/api/media/library?kind=unknown').status_code==422


def test_usage_uses_frozen_publication_and_schedule_snapshots_and_preserves_reuse():
    c,uid,*_=account(); original=asset(uid); replacement=asset(uid); conn=connect(uid)
    with SessionLocal() as db:
        draft=Draft(user_id=uid,title='Same title',status='published',workspace_json=json.dumps({'media_asset_ids':[replacement]}))
        later=Draft(user_id=uid,title='Same title',workspace_json=json.dumps({'media_asset_ids':[original]}))
        db.add_all([draft,later]);db.flush();did=draft.id;later_id=later.id
        code=uuid4().hex
        db.add(PublishReview(code=code,user_id=uid,draft_id=did,revision=0,payload_json=json.dumps({'media_asset_ids':[original]}),expires_at=utcnow()+timedelta(hours=1)))
        db.add(Publication(user_id=uid,draft_id=did,connection_id=conn,review_code=code,platform='instagram',status='published'))
        db.add(ScheduledPost(user_id=uid,draft_id=later_id,platform='instagram',content_json='{}',media_asset_ids_json=json.dumps([original]),scheduled_at=utcnow()+timedelta(days=1)))
        db.commit()
    items={a['id']:a for a in library(c)['assets']}
    assert set(items[original]['states'])=={'published','saved','planned'}
    assert items[replacement]['states']==['saved'], 'A new attachment is not historically published'
    assert len(items[original]['uses'])==2, 'One canonical reference per post, even with multiple states'
    with SessionLocal() as db:
        db.get(Draft,later_id).workspace_json='{}';db.commit()
    items={a['id']:a for a in library(c)['assets']}
    assert set(items[original]['states'])=={'published','planned'}
    assert c.get('/media/download/'+str(original)).status_code==200


@pytest.mark.parametrize('status', ['queued','pending','publishing','unknown','failed'])
def test_acceptance_or_failure_never_means_published(status):
    c,uid,*_=account(); mid=asset(uid); conn=connect(uid)
    with SessionLocal() as db:
        draft=Draft(user_id=uid);db.add(draft);db.flush();code=uuid4().hex
        db.add(PublishReview(code=code,user_id=uid,draft_id=draft.id,revision=0,payload_json=json.dumps({'media_asset_ids':[mid]}),expires_at=utcnow()+timedelta(hours=1)))
        db.add(Publication(user_id=uid,draft_id=draft.id,connection_id=conn,review_code=code,platform='instagram',status=status));db.commit()
    assert 'published' not in library(c)['assets'][0]['states']


def test_evidence_is_platform_scoped_honest_about_zero_and_missing_and_staleness():
    context={'available':True,'evidence':{'fetched_at':utcnow().isoformat(),'posts':[
        {'platform':'instagram','text':'Friday bouquets','likes':0,'comments':None,'shares':True,'views':-1},
        {'platform':'facebook','text':'Different audience','likes':10}]}}
    result=evidence_basis(context,'instagram')
    assert result['sample_size']==1
    assert result['examples'][0]['metrics']=={'likes':0,'comments':None,'shares':None,'views':None}
    assert 'not growth or sales' in result['note']
    assert evidence_basis(context,'tiktok')['sample_size']==0
    context['evidence']['fetched_at']=(utcnow()-timedelta(days=2)).isoformat()
    assert evidence_basis(context)['examples']==[]
    assert evidence_basis({'available':False})['summary'].startswith('A test')


def test_uncertain_summary_links_only_to_affected_drafts_without_resending():
    result=summary([{'draft_id':1,'status':'scheduled'},{'draft_id':2,'status':'unknown'},{'draft_id':3,'status':'published'}])
    assert result['attention']==1 and result['draft_ids']==[2]
    assert result['text']=='1 scheduled · 1 published · 1 needs attention'
    assert 'will not resend automatically' in guidance('unknown')
    assert 'do not resend' in guidance('pending')


def test_queued_and_reviewed_posts_are_not_missing_from_summary():
    assert summary([{'status':'queued'},{'status':'review'}])['text']=='1 awaiting approval · 1 preparing'


def test_summary_labels_one_draft_and_multiple_drafts():
    assert summary([{"status":"draft"}])["text"] == "1 draft"
    assert summary([{"status":"draft"},{"status":"draft"}])["text"] == "2 drafts"
