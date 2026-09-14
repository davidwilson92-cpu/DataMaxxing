from test_account_integrity import account
from nova.db import SessionLocal, MediaAsset


def test_workspace_restores_context_and_rejects_stale_saves():
    client,uid,_,_=account()
    row=client.post('/api/drafts',json={}).json()
    body={'revision':row['revision'],'brief':'An idea','platforms':['x'],'variants':{'x':{'posts':['Hello']}},'workspace':{'composer':'Unsent thought','conversation':[{'role':'user','content':'My idea'}],'link_url':'https://example.test/article','selected_platforms':['x']}}
    assert client.patch(f"/api/drafts/{row['id']}",json=body).status_code==200
    loaded=client.get(f"/api/drafts/{row['id']}").json()
    assert loaded['workspace']['composer']=='Unsent thought'
    assert loaded['workspace']['conversation']==body['workspace']['conversation']
    assert client.patch(f"/api/drafts/{row['id']}",json=body).status_code==409
    assert client.get(f"/api/drafts/{row['id']}").json()['revision']==1


def test_workspace_asset_and_draft_ownership():
    client,uid,_,_=account();other,oid,_,_=account()
    row=client.post('/api/drafts',json={}).json()
    with SessionLocal() as db:
        asset=MediaAsset(user_id=oid,filename='other.png',mime_type='image/png',storage_key='synthetic')
        db.add(asset);db.commit();db.refresh(asset);aid=asset.id
    assert client.patch(f"/api/drafts/{row['id']}",json={'workspace':{'media_asset_ids':[aid]}}).status_code==404
    assert other.get(f"/api/drafts/{row['id']}").status_code==404


def test_library_search_finds_unsent_workspace_and_respects_ownership():
    client,_,_,_=account();other,*_=account()
    row=client.post('/api/drafts',json={}).json()
    client.patch(f"/api/drafts/{row['id']}",json={'workspace':{'composer':'UniquelyFindableNote'}})
    own=client.get('/drafts?q=UniquelyFindableNote')
    assert f'/studio?draft={row["id"]}' in own.text
    assert f'/studio?draft={row["id"]}' not in other.get('/drafts?q=UniquelyFindableNote').text
