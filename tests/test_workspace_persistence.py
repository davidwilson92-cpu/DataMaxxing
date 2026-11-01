from test_account_integrity import account
from nova.db import SessionLocal, MediaAsset


def test_generation_can_return_the_same_owned_revision_as_reopening(monkeypatch):
    from nova import ai
    client, *_ = account()
    other, *_ = account()
    monkeypatch.setattr(ai, 'generate_variants', lambda **kw: {'instagram': {'posts': ['Saved caption']}})
    result = client.post('/api/ai/generate', json={'brief':'A new class', 'platforms':['instagram'],
                         'include_saved_draft':True})
    assert result.status_code == 200, result.text
    saved = result.json()
    path = f"/api/drafts/{saved['draft_id']}"
    assert saved['draft'] == client.get(path).json()
    assert saved['revision'] == saved['draft']['revision']
    assert other.get(path).status_code == 404


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


def test_recent_post_titles_are_bounded_persistent_and_account_owned():
    client,*_=account();other,*_=account()
    row=client.post('/api/drafts',json={}).json()
    title='A private saved conversation '+('x'*150)
    saved=client.patch(f"/api/drafts/{row['id']}",json={'workspace':{'composer':'Unsent continuation','conversation':[{'role':'user','content':title}]}})
    assert saved.status_code==200
    recent=client.get('/api/drafts').json()
    assert recent[0]['id']==row['id'] and recent[0]['title'].startswith('A private saved conversation')
    assert len(recent[0]['title'])<=72
    assert all(r['id']!=row['id'] for r in other.get('/api/drafts').json())
    assert client.get(f"/api/drafts/{row['id']}").json()['workspace']['conversation'][0]['content']==title


def test_history_previews_recheck_user_and_brand_and_ignore_stored_urls():
    import json
    from nova.db import Draft
    client,uid,_,_=account();other,oid,_,_=account()
    draft=client.post('/api/drafts',json={}).json()
    with SessionLocal() as db:
        own=MediaAsset(user_id=uid,filename='own.png',mime_type='image/png',storage_key='synthetic')
        foreign=MediaAsset(user_id=oid,filename='other.png',mime_type='image/png',storage_key='synthetic')
        other_brand=MediaAsset(user_id=uid,brand_id=98765,filename='brand.png',mime_type='image/png',storage_key='synthetic')
        db.add_all([own,foreign,other_brand]);db.flush();own_id=own.id
        row=db.get(Draft,draft['id'])
        row.workspace_json=json.dumps({'media_asset_ids':[foreign.id,other_brand.id,own.id], 'media':[{'kind':'image','url':'https://untrusted.example/track'}]})
        db.commit()
    rows=client.get('/api/drafts').json()
    assert rows[0]['thumbnail']=={'id':own_id,'filename':'own.png','kind':'image',
        'url':f'/media/preview/{own_id}', 'thumbnail_url':f'/media/thumbnail/{own_id}'}
    assert all(r['id']!=draft['id'] for r in other.get('/api/drafts').json())
    assert other.get(f'/media/preview/{own_id}').status_code==404
    with SessionLocal() as db:
        row=db.get(Draft,draft['id']);row.workspace_json='{"media_asset_ids": "invalid"}';db.commit()
    assert client.get('/api/drafts').json()[0]['thumbnail'] is None


def test_history_video_has_lightweight_marker_not_remote_media_url():
    import json
    from nova.db import Draft
    client,uid,_,_=account()
    draft=client.post('/api/drafts',json={}).json()
    with SessionLocal() as db:
        video=MediaAsset(user_id=uid,filename='video.mp4',mime_type='video/mp4',storage_key='synthetic',public_url='https://example.test/video')
        db.add(video);db.flush();video_id=video.id
        db.get(Draft,draft['id']).workspace_json=json.dumps({'media_asset_ids':[video.id]});db.commit()
    assert client.get('/api/drafts').json()[0]['thumbnail']=={'id':video_id,'filename':'video.mp4','kind':'video'}


def test_reported_result_requires_owned_published_post_and_detects_conflicts():
    from nova.db import Draft
    owner, *_ = account()
    other, *_ = account()
    post = owner.post('/api/drafts', json={}).json()['id']
    url = f'/api/drafts/{post}/reported-outcome'
    note = {'previous':'','note':'3 enquiries from Friday bouquets'}
    assert owner.put(url,json=note).status_code == 404
    with SessionLocal() as db:
        row=db.get(Draft,post); row.status='published'; db.commit()
    assert other.get(url).status_code == 404
    assert other.put(url,json=note).status_code == 404
    assert owner.put(url,json=note).json() == {'note':note['note']}
    assert owner.put(url,json=note).status_code == 200
    assert owner.put(url,json={'previous':'','note':'different'}).status_code == 409
    assert owner.get(url).json() == {'note':note['note']}
