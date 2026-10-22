"""Sent attachments belong to their turn without becoming publishing authority."""
import json

import pytest
from fastapi import HTTPException

from nova.db import Brand, Draft, MediaAsset, SessionLocal
from nova.workspace import clean_workspace
from test_account_integrity import account


def asset_for(uid, *, brand_id=0, filename='synthetic-video.mp4'):
    with SessionLocal() as db:
        row=MediaAsset(user_id=uid,brand_id=brand_id,filename=filename,mime_type='video/mp4',
            storage_key='synthetic-not-uploaded',public_url='https://example.test/private-upload',size_bytes=20)
        db.add(row);db.commit()
        return row.id


def save(client,draft,workspace):
    return client.patch(f"/api/drafts/{draft['id']}",json={'revision':draft['revision'],
        'platforms':['tiktok'],'variants':{'tiktok':{'posts':['Caption']}},'workspace':workspace})


def load(client,draft):
    response=client.get(f"/api/drafts/{draft['id']}")
    assert response.status_code==200,response.text
    return response.json()


def test_sent_media_is_canonical_and_survives_removal_from_active_post_and_reload():
    client,uid,*_=account()
    aid=asset_for(uid)
    draft=client.post('/api/drafts',json={}).json()
    poison={'id':aid,'filename':'fake','kind':'image','url':'https://attacker.test/tracker'}
    state={'media_asset_ids':[aid], 'media':[poison], 'pending_message':'Draft my video',
        'conversation':[{'role':'user','content':'Draft my video','media_asset_ids':[aid,aid],'media':[poison]},
                        {'role':'assistant','content':'Caption','media_asset_ids':[aid],'media':[poison]}]}
    assert save(client,draft,state).status_code==200
    draft=load(client,draft)
    preview={'id':aid,'filename':'synthetic-video.mp4','kind':'video','url':f'/media/preview/{aid}'}
    message=draft['workspace']['conversation'][0]
    assert message['media_asset_ids']==[aid] and message['media']==[preview]
    assert draft['workspace']['media']==[preview]
    assert draft['workspace']['conversation'][1]=={'role':'assistant','content':'Caption'}
    assert 'attacker' not in json.dumps(draft)
    # Removing the upload from publishing leaves a historical preview on its turn.
    state={**draft['workspace'],'media_asset_ids':[]}
    assert save(client,draft,state).status_code==200
    saved=load(client,draft)['workspace']
    assert saved['media_asset_ids']==[] and saved['media']==[] and saved['media_kind'] is None
    assert saved['conversation'][0]==message
    assert saved['pending_message']=='Draft my video'


@pytest.mark.parametrize('location',['active','message'])
@pytest.mark.parametrize('foreign',['user','brand'])
def test_existing_foreign_media_is_rejected_even_when_listed_in_previous_history(location,foreign):
    client,uid,*_=account()
    _,other_uid,*_=account()
    with SessionLocal() as db:
        brand=Brand(user_id=uid,name='Separate brand');db.add(brand);db.commit();brand_id=brand.id
    aid=asset_for(other_uid if foreign=='user' else uid,brand_id=brand_id if foreign=='brand' else 0,
        filename='private-other-video.mp4')
    draft=client.post('/api/drafts',json={}).json()
    state={'media_asset_ids':[aid] if location=='active' else [],
           'conversation':[{'role':'user','content':'Test','media_asset_ids':[aid]}]}
    # Even poisoned historical data is not a grant to another owner or brand.
    with SessionLocal() as db:
        row=db.get(Draft,draft['id']);row.workspace_json=json.dumps(state);db.commit()
    response=save(client,draft,state)
    assert response.status_code==404,response.text
    assert 'private-other' not in response.text


def test_same_brand_media_can_be_saved_but_default_workspace_cannot_access_it():
    client,uid,*_=account()
    with SessionLocal() as db:
        brand=Brand(user_id=uid,name='Second brand');db.add(brand);db.commit();brand_id=brand.id
    aid=asset_for(uid,brand_id=brand_id)
    client.headers['X-Zova-Brand']=str(brand_id)
    draft=client.post('/api/drafts',json={}).json()
    assert save(client,draft,{'conversation':[{'role':'user','content':'Video','media_asset_ids':[aid]}]}).status_code==200
    assert load(client,draft)['workspace']['conversation'][0]['media'][0]['id']==aid
    del client.headers['X-Zova-Brand']
    assert client.get(f"/api/drafts/{draft['id']}").status_code==404


def test_reload_rehydrates_stored_urls_and_hides_foreign_metadata_without_mutating_record():
    client,uid,*_=account()
    _,other_uid,*_=account()
    own=asset_for(uid);foreign=asset_for(other_uid,filename='private-secret.mp4')
    draft=client.post('/api/drafts',json={}).json()
    poison={'id':foreign,'url':'https://attacker.test/collect','filename':'private-secret.mp4','kind':'video'}
    stored={'future_metadata':{'preserve':'yes'},'media_asset_ids':[own,foreign],'media':[poison],
        'conversation':[{'role':'user','content':'A video','media_asset_ids':[own,foreign],'media':[poison]}]}
    with SessionLocal() as db:
        row=db.get(Draft,draft['id']);row.workspace_json=json.dumps(stored);db.commit()
    result=load(client,draft)['workspace']
    assert result['media_asset_ids']==[own]
    assert result['media'][0]['url']==f'/media/preview/{own}'
    assert result['conversation'][0]['media'][1]=={'id':foreign,'filename':'Attachment unavailable',
        'url':'','kind':'file','unavailable':True}
    assert result['future_metadata']==stored['future_metadata']
    assert 'private-secret' not in json.dumps(result) and 'attacker' not in json.dumps(result)
    with SessionLocal() as db:
        assert json.loads(db.get(Draft,draft['id']).workspace_json)==stored


def test_deleted_sent_attachment_can_be_saved_and_forked_but_new_missing_ids_are_rejected(monkeypatch):
    import nova.app as module
    client,uid,*_=account();aid=asset_for(uid)
    draft=client.post('/api/drafts',json={}).json()
    state={'conversation':[{'role':'user','content':'Draft another caption','media_asset_ids':[aid]}],
        'pending_message':'Draft another caption','selected_platforms':['tiktok']}
    assert save(client,draft,state).status_code==200
    with SessionLocal() as db:
        db.delete(db.get(MediaAsset,aid));db.commit()
    draft=load(client,draft)
    assert draft['workspace']['conversation'][0]['media'][0]['unavailable'] is True
    assert save(client,draft,draft['workspace']).status_code==200
    draft=load(client,draft)
    monkeypatch.setattr(module.ai,'generate_variants',lambda **kwargs:{'tiktok':{'posts':['New caption']}})
    result=client.post('/api/ai/generate',json={'brief':'Draft another caption','platforms':['tiktok'],
        'source_draft_id':draft['id'],'source_revision':draft['revision']})
    assert result.status_code==200,result.text
    target=load(client,{'id':result.json()['draft_id']})
    assert target['workspace']['conversation']==draft['workspace']['conversation']
    assert target['workspace']['pending_message']=='' and target['workspace']['media_asset_ids']==[]
    assert load(client,draft)['workspace']['pending_message']==''
    new=client.post('/api/drafts',json={}).json()
    assert save(client,new,state).status_code==404
    # A formerly sent upload cannot be made active again after deletion.
    target['workspace']['media_asset_ids']=[aid]
    assert save(client,target,target['workspace']).status_code==404


def test_new_draft_fork_preserves_sent_media_independent_of_active_selection(monkeypatch):
    import nova.app as module
    client,uid,*_=account();sent=asset_for(uid);current=asset_for(uid,filename='next.mp4')
    draft=client.post('/api/drafts',json={}).json()
    state={'conversation':[{'role':'user','content':'First video','media_asset_ids':[sent]},
        {'role':'user','content':'Draft the next video','media_asset_ids':[current]}],
        'media_asset_ids':[current],'pending_message':'Draft the next video'}
    assert save(client,draft,state).status_code==200
    draft=load(client,draft)
    monkeypatch.setattr(module.ai,'generate_variants',lambda **kwargs:{'tiktok':{'posts':['New caption']}})
    result=client.post('/api/ai/generate',json={'brief':'Draft the next video','platforms':['tiktok'],
        'source_draft_id':draft['id'],'source_revision':draft['revision']})
    assert result.status_code==200,result.text
    target=load(client,{'id':result.json()['draft_id']})
    assert target['workspace']['conversation']==draft['workspace']['conversation']
    assert target['workspace']['media_asset_ids']==[current]
    assert target['workspace']['conversation'][0]['media'][0]['id']==sent


@pytest.mark.parametrize('ids',[None,'1',[True],['1'],[1.0],[0],[-1],[2**64],list(range(1,12))])
def test_message_attachment_selection_is_bounded_and_strict(ids):
    with SessionLocal() as db,pytest.raises(HTTPException) as error:
        clean_workspace({'conversation':[{'role':'user','content':'Test','media_asset_ids':ids}]},db,1)
    assert error.value.status_code==400


def test_conversation_and_unique_attachment_limits_precede_asset_queries():
    with SessionLocal() as db:
        with pytest.raises(HTTPException) as error:
            clean_workspace({'conversation':[{'role':'user','content':'Test'}]*201},db,1)
        assert error.value.status_code==400
        with pytest.raises(HTTPException) as error:
            clean_workspace({'conversation':[{'role':'user','content':'Test','media_asset_ids':list(range(n,n+10))}
                for n in range(1,211,10)]},db,1)
        assert error.value.status_code==400


def test_supplied_metadata_without_ids_never_creates_a_message_attachment():
    with SessionLocal() as db:
        result=clean_workspace({'conversation':[{'role':'user','content':'Test',
            'media':[{'id':1,'url':'https://attacker.test','filename':'fake','kind':'image'}]}]},db,1)
    assert result['conversation']==[{'role':'user','content':'Test'}]


@pytest.mark.parametrize('fork',[False,True])
def test_retry_media_and_link_snapshot_survive_reload_and_clear_atomically_on_generation(monkeypatch,fork):
    import nova.app as module
    client,uid,*_=account();aid=asset_for(uid)
    draft=client.post('/api/drafts',json={}).json()
    state={'conversation':[{'role':'user','content':'Draft this video','media_asset_ids':[aid]}],
        'media_asset_ids':[aid],'pending_message':'Draft this video','pending_media_asset_ids':[aid],
        'pending_link_url':'https://example.test/original','link_url':'https://example.test/changed'}
    assert save(client,draft,state).status_code==200
    draft=load(client,draft)
    assert draft['workspace']['pending_media_asset_ids']==[aid]
    assert draft['workspace']['pending_link_url']=='https://example.test/original'
    assert draft['workspace']['link_url']=='https://example.test/changed'
    monkeypatch.setattr(module.ai,'generate_variants',lambda **kwargs:{'tiktok':{'posts':['Caption']}})
    payload={'brief':'Draft this video','platforms':['tiktok']}
    payload.update({'source_draft_id':draft['id'],'source_revision':draft['revision']} if fork else {'draft_id':draft['id']})
    response=client.post('/api/ai/generate',json=payload)
    assert response.status_code==200,response.text
    for did in {draft['id'],response.json()['draft_id']}:
        state=load(client,{'id':did})['workspace']
        assert state['pending_message']==''
        assert 'pending_media_asset_ids' not in state and 'pending_link_url' not in state
        assert state['conversation'][0]['media_asset_ids']==[aid]


def test_deleted_pending_media_is_retained_as_retry_context_until_resolved():
    client,uid,*_=account();aid=asset_for(uid)
    draft=client.post('/api/drafts',json={}).json()
    state={'conversation':[{'role':'user','content':'Draft video'}],'pending_message':'Draft video',
        'pending_media_asset_ids':[aid],'pending_link_url':''}
    assert save(client,draft,state).status_code==200
    with SessionLocal() as db:
        db.delete(db.get(MediaAsset,aid));db.commit()
    draft=load(client,draft)
    assert save(client,draft,draft['workspace']).status_code==200
    saved=load(client,draft)['workspace']
    assert saved['pending_media_asset_ids']==[aid] and saved['media_asset_ids']==[]
    saved['pending_message']=''
    assert save(client,load(client,draft),saved).status_code==200
    assert 'pending_media_asset_ids' not in load(client,draft)['workspace']


@pytest.mark.parametrize('snapshot',[
    {'pending_media_asset_ids':[True]}, {'pending_media_asset_ids':'1'},
    {'pending_media_asset_ids':list(range(11))}, {'pending_link_url':'javascript:alert(1)'},
])
def test_retry_context_requires_bounded_ids_and_web_link(snapshot):
    client,*_=account();draft=client.post('/api/drafts',json={}).json()
    response=save(client,draft,{'conversation':[{'role':'user','content':'Draft video'}],
        'pending_message':'Draft video',**snapshot})
    assert response.status_code==400,response.text


def test_foreign_retry_attachment_is_rejected_before_save():
    client,*_=account();_,other,*_=account();aid=asset_for(other)
    draft=client.post('/api/drafts',json={}).json()
    response=save(client,draft,{'conversation':[{'role':'user','content':'Draft video'}],
        'pending_message':'Draft video','pending_media_asset_ids':[aid]})
    assert response.status_code==404,response.text
