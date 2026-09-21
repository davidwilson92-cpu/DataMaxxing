import json
from datetime import timedelta
from types import SimpleNamespace
import pytest
from sqlalchemy import select
from nova import social
from nova.db import SessionLocal,SocialConnection,MediaAsset,ScheduledPost,utcnow
from test_reviewed_publication import prepared


def story_draft(monkeypatch,placement='story'):
    client,uid,_,body=prepared(('instagram',))
    with SessionLocal() as db:
        conn=db.scalar(select(SocialConnection).where(SocialConnection.user_id==uid))
        conn.scope='instagram_business_content_publish'
        asset=MediaAsset(user_id=uid,filename='story.jpg',mime_type='image/jpeg',storage_key='synthetic.jpg',public_url='https://example.test/story.jpg',size_bytes=100)
        db.add(asset);db.commit();body['media_asset_ids']=[asset.id]
    body['publish_options']={'instagram':{'format':placement}}
    response=client.patch(f"/api/drafts/{body['draft_id']}",json={'platforms':['instagram'],'variants':body['variants'],'workspace':{'instagram_format':placement,'media_asset_ids':body['media_asset_ids']}})
    assert response.status_code==200,response.text
    monkeypatch.setattr(social,'instagram_story_eligibility',lambda *a:None)
    return client,body


def test_story_saved_review_immutable_and_dispatch(monkeypatch):
    import nova.app as app
    client,body=story_draft(monkeypatch);calls=[]
    assert client.get(f"/api/drafts/{body['draft_id']}").json()['workspace']['instagram_format']=='story'
    reviewed=client.post('/api/publish-review',json=body)
    assert reviewed.status_code==200,reviewed.text
    snapshot=reviewed.json()['snapshot']
    assert snapshot['targets']['instagram']['posts']==[]
    assert snapshot['targets']['instagram']['format_label']=='Story'
    approved={**body,'review_token':reviewed.json()['review_token']}
    monkeypatch.setattr(app,'publish_platform',lambda *a,**kw:calls.append(kw) or {'post_id':'mock','format':'story'})
    assert client.post('/api/publish',json={**approved,'publish_options':{'instagram':{'format':'post'}}}).status_code==409
    assert not calls
    assert client.post('/api/publish',json=approved).status_code==200
    assert calls[0]['options']=={'format':'story'} and calls[0]['posts']==[]
    client.post('/api/publish',json=approved)
    assert len(calls)==1


def test_story_schedule_keeps_reviewed_format(monkeypatch):
    import nova.scheduler as worker
    client,body=story_draft(monkeypatch);calls=[]
    body['scheduled_local']=(utcnow()+timedelta(days=1)).isoformat()
    review=client.post('/api/publish-review',json=body).json()
    assert client.post('/api/schedule',json={**body,'review_token':review['review_token']}).status_code==200
    with SessionLocal() as db:
        job=db.scalar(select(ScheduledPost).where(ScheduledPost.draft_id==body['draft_id']))
        job.scheduled_at=utcnow()-timedelta(seconds=1);db.commit()
    monkeypatch.setattr(worker,'publish_platform',lambda *a,**kw:calls.append(kw) or {'post_id':'mock'})
    worker.process_due()
    assert calls[0]['options']['format']=='story' and calls[0]['posts']==[]


def test_format_mismatch_ineligible_account_and_invalid_format(monkeypatch):
    client,body=story_draft(monkeypatch)
    assert client.post('/api/publish-review',json={**body,'publish_options':{'instagram':{'format':'post'}}}).status_code==409
    def no(*args):raise RuntimeError('Business account required')
    monkeypatch.setattr(social,'instagram_story_eligibility',no)
    assert client.post('/api/publish-review',json=body).status_code==400
    assert client.patch(f"/api/drafts/{body['draft_id']}",json={'workspace':{'instagram_format':'bogus'}}).status_code==400


@pytest.mark.parametrize('provider',['instagram_login','facebook'])
@pytest.mark.parametrize('mime',['image/jpeg','video/mp4'])
def test_story_adapter_uses_stories_no_caption_or_feed(monkeypatch,provider,mime):
    conn=SimpleNamespace(account_id='account',meta_json=json.dumps({'auth_provider':provider}))
    # json_meta reads metadata_json on persisted connections.
    conn.metadata_json=conn.meta_json
    monkeypatch.setattr(social,'json_meta',lambda c:{'auth_provider':provider})
    monkeypatch.setattr(social,'access_token',lambda *a:'synthetic')
    monkeypatch.setattr(social,'get_public_url',lambda *a:'https://example.test/visual')
    calls=[]
    def get(url,**kw):
        fields=kw['params']['fields']
        return SimpleNamespace(status_code=200,json=lambda:{'account_type':'BUSINESS'} if fields=='account_type' else {'status_code':'FINISHED'} if 'status_code' in fields else {})
    def post(url,**kw):
        calls.append((url,kw['data']));return SimpleNamespace(status_code=200,json=lambda:{'id':'mock'})
    monkeypatch.setattr(social.httpx,'get',get);monkeypatch.setattr(social.httpx,'post',post)
    result=social.publish_instagram(None,conn,[],[SimpleNamespace(mime_type=mime,storage_key='x',public_url='x')],options={'format':'story'})
    data=calls[0][1]
    assert data['media_type']=='STORIES' and 'caption' not in data and 'share_to_feed' not in data
    assert ('video_url' if mime.startswith('video') else 'image_url') in data
    assert ('graph.instagram.com' if provider=='instagram_login' else 'graph.facebook.com') in calls[0][0]
    assert result['format']=='story' and result['url'] is None


def test_legacy_post_default_keeps_caption(monkeypatch):
    client,body=story_draft(monkeypatch,'post')
    body['publish_options']={}
    response=client.post('/api/publish-review',json=body)
    assert response.status_code==200,response.text
    target=response.json()['snapshot']['targets']['instagram']
    assert target['format']=='post' and target['posts']==body['variants']['instagram']['posts']


def test_saved_format_change_invalidates_existing_review(monkeypatch):
    client,body=story_draft(monkeypatch)
    review=client.post('/api/publish-review',json=body).json()
    client.patch(f"/api/drafts/{body['draft_id']}",json={'platforms':['instagram'],'variants':body['variants'],'workspace':{'instagram_format':'post','media_asset_ids':body['media_asset_ids']}})
    assert client.post('/api/publish',json={**body,'review_token':review['review_token']}).status_code==409


def test_story_counts_as_one_publication(monkeypatch):
    import nova.app as app
    from nova import allowances
    client,body=story_draft(monkeypatch);units=[]
    original=allowances.reserve
    def reserve(db,uid,kind,key,amount):
        units.append(amount);return original(db,uid,kind,key,amount)
    monkeypatch.setattr(allowances,'reserve',reserve)
    monkeypatch.setattr(app,'publish_platform',lambda *a,**kw:{'post_id':'mock'})
    reviewed=client.post('/api/publish-review',json=body).json()
    assert client.post('/api/publish',json={**body,'review_token':reviewed['review_token']}).status_code==200
    assert units==[1]


@pytest.mark.parametrize('account_type',['MEDIA_CREATOR','PERSONAL',None])
def test_ineligible_story_account_never_creates_container(monkeypatch,account_type):
    monkeypatch.setattr(social,'access_token',lambda *a:'synthetic')
    monkeypatch.setattr(social,'json_meta',lambda c:{'auth_provider':'instagram_login'})
    monkeypatch.setattr(social.httpx,'get',lambda *a,**kw:SimpleNamespace(status_code=200,json=lambda:{'account_type':account_type}))
    with pytest.raises(RuntimeError,match='Business account'):
        social.publish_instagram(None,SimpleNamespace(account_id='mock'),[],[SimpleNamespace(mime_type='image/jpeg')],options={'format':'story'})
