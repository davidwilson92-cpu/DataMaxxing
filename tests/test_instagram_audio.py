"""Current Meta Audio API contracts, synthetic grants/media; no real publishing."""
import json
from datetime import timedelta
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import select

from nova import instagram_audio, social
from nova.db import SessionLocal, Brand, MediaAsset, SocialConnection, PublishReview, utcnow
from nova.security import encrypt,decrypt
from test_account_integrity import account
from test_reviewed_publication import prepared,review,synthetic_storage
from test_social_login_routes import signed_in,state_from

TRACK={'audio_id':'123456','title':'Synthetic song','display_artist':'Test artist','audio_type':'music','duration_in_ms':90000}
CHOICE={'audio_id':'123456','title':'Synthetic song','artist':'Test artist','audio_volume':80,'video_volume':30}


def connection(uid,**changes):
    values={'user_id':uid,'platform':'instagram','account_id':'synthetic-ig','username':'creator','display_name':'Creator',
        'encrypted_access_token':encrypt('synthetic-page-token'),'scope':'instagram_basic,instagram_content_publish',
        'encrypted_audio_user_token':encrypt('synthetic-audio-user-token'),'audio_user_token_expires_at':utcnow()+timedelta(days=30),
        'metadata_json':'{"auth_provider":"facebook_login","facebook_page_id":"synthetic-page"}'}
    with SessionLocal() as db:
        row=SocialConnection(**{**values,**changes});db.add(row);db.commit();return row.id


def audio_draft():
    client,uid,_,body=prepared(('instagram',))
    with SessionLocal() as db:
        conn=db.scalar(select(SocialConnection).where(SocialConnection.user_id==uid))
        conn.scope='instagram_basic,instagram_content_publish';conn.metadata_json='{"auth_provider":"facebook_login"}'
        conn.encrypted_audio_user_token=encrypt('synthetic-audio-user-token');conn.audio_user_token_expires_at=utcnow()+timedelta(days=30)
        asset=MediaAsset(user_id=uid,filename='synthetic.mp4',mime_type='video/mp4',storage_key=synthetic_storage(),public_url='https://example.test/synthetic.mp4',size_bytes=20)
        db.add(asset);db.commit();mid=asset.id;cid=conn.id
    saved=client.get('/api/drafts/'+str(body['draft_id'])).json()
    assert client.patch('/api/drafts/'+str(body['draft_id']),json={'revision':saved['revision'],'platforms':['instagram'],'variants':body['variants'],'workspace':{'media_asset_ids':[mid],'instagram_format':'post'}}).status_code==200
    body={**body,'media_asset_ids':[mid],'publish_options':{'instagram':{'format':'post','audio':dict(CHOICE)}}}
    return client,uid,cid,body


def test_search_uses_separate_user_token_and_sanitizes_provider_fields(monkeypatch):
    client,uid,*_=account();cid=connection(uid);calls=[]
    def get(url,**kwargs):
        calls.append((url,kwargs))
        return httpx.Response(200,json={'audio':[{**TRACK,'download_url':'https://secret.invalid/audio?access_token=private',
            'on_platform_audio_preview_link':'https://www.instagram.com/reels/audio/123456/','access_token':'do-not-return'},
            {**TRACK,'audio_id':'../unsafe'},'malformed']})
    monkeypatch.setattr(instagram_audio.httpx,'get',get)
    response=client.get('/api/instagram/audio',params={'connection_id':cid,'q':'dance'})
    assert response.status_code==200 and response.json()['eligible']
    assert len(response.json()['tracks'])==1
    assert response.json()['tracks'][0]['preview_url']=='https://www.instagram.com/reels/audio/123456/'
    assert calls[0][0].endswith('/ig_audio') and calls[0][1]['params']['search_query']=='dance'
    assert calls[0][1]['params']['access_token']=='synthetic-audio-user-token'
    assert 'token' not in response.text and 'download_url' not in response.text


@pytest.mark.parametrize('changes,reason',[
    ({'metadata_json':'{"auth_provider":"instagram_login"}'},'Instagram Login'),
    ({'encrypted_audio_user_token':None},'predates'),
    ({'audio_user_token_expires_at':utcnow()-timedelta(minutes=1)},'expired'),
    ({'audio_user_token_expires_at':None},'expired'),
    ({'scope':'instagram_basic'},'permission'),
])
def test_ineligible_existing_connections_are_honest_without_provider_call(changes,reason):
    client,uid,*_=account();cid=connection(uid,**changes)
    response=client.get('/api/instagram/audio',params={'connection_id':cid})
    assert response.status_code==200 and not response.json()['eligible']
    assert reason in response.json()['reason'] and response.json()['tracks']==[]


def test_search_cannot_cross_owner_or_brand_boundary():
    client,uid,*_=account();other,other_id,*_=account();cid=connection(uid)
    assert other.get('/api/instagram/audio',params={'connection_id':cid}).status_code==404
    with SessionLocal() as db:brand=Brand(user_id=uid,name='Second');db.add(brand);db.commit();bid=brand.id
    assert client.get('/api/instagram/audio',params={'connection_id':cid,'workspace':bid}).status_code==404


def test_audio_account_choices_are_human_names_and_owner_workspace_scoped():
    client,uid,*_=account();other,other_id,*_=account()
    cid=connection(uid,encrypted_audio_user_token=None,display_name='Pottery studio')
    unnamed=connection(uid,account_id='secret-provider-id',encrypted_audio_user_token=None,username='',display_name='')
    connection(uid,account_id='inactive',active=False)
    connection(uid,account_id='facebook',platform='facebook')
    connection(other_id,account_id='foreign-owner')
    with SessionLocal() as db:
        brand=Brand(user_id=uid,name='Other brand');db.add(brand);db.commit();bid=brand.id
    other_brand=connection(uid,account_id='other-brand',brand_id=bid,display_name='Other studio',encrypted_audio_user_token=None)
    response=client.get('/api/instagram/audio',params={'connection_id':cid}).json()
    assert response['connection_id']==cid and response['eligible'] is False
    assert response['accounts']==[{'id':unnamed,'name':'Instagram account'},{'id':cid,'name':'Pottery studio'}]
    assert 'secret-provider-id' not in json.dumps(response)
    second=client.get('/api/instagram/audio',params={'workspace':bid}).json()
    assert second['connection_id']==other_brand and second['accounts']==[{'id':other_brand,'name':'Other studio'}]
    no_connections,empty_uid,*_=account()
    empty=no_connections.get('/api/instagram/audio').json()
    assert empty['accounts']==[] and empty['connection_id'] is None


def test_upsert_encrypts_optional_grant_and_preserves_primary_page_token():
    _,uid,*_=account()
    with SessionLocal() as db:
        conn=social.upsert_connection(db,user_id=uid,platform='instagram',account_id='synthetic',username='creator',display_name='Creator',access='page-secret',
            metadata={'auth_provider':'facebook_login'},scope='instagram_basic,instagram_content_publish',audio_user_token='user-secret',audio_user_token_expires_in=7200)
        assert decrypt(conn.encrypted_access_token)=='page-secret'
        assert decrypt(conn.encrypted_audio_user_token)=='user-secret'
        assert 'user-secret' not in conn.metadata_json and 'user-secret' not in conn.encrypted_audio_user_token
        assert conn.audio_user_token_expires_at is not None
        conn=social.upsert_connection(db,user_id=uid,platform='instagram',account_id='synthetic',username='creator',display_name='Creator',access='direct-secret',metadata={'auth_provider':'instagram_login'})
        assert conn.encrypted_audio_user_token is None and conn.audio_user_token_expires_at is None
        assert decrypt(conn.encrypted_access_token)=='direct-secret'


@pytest.mark.parametrize('change',[{'audio_id':'../token'},{'audio_volume':0},{'video_volume':101},{'audio_volume':True},{'title':'Fake title'},{'artist':'Fake artist'}])
def test_review_rejects_invalid_track_or_forged_metadata(monkeypatch,change):
    client,uid,cid,body=audio_draft()
    monkeypatch.setattr(instagram_audio.httpx,'get',lambda *a,**k:httpx.Response(200,json=TRACK))
    body['publish_options']['instagram']['audio'].update(change)
    response=client.post('/api/publish-review',json=body)
    assert response.status_code==400


def test_review_binds_audio_and_provider_payload_uses_user_token(monkeypatch):
    client,uid,cid,body=audio_draft();requests=[]
    def get(url,**kwargs):
        if url.endswith('/123456'):return httpx.Response(200,json=TRACK)
        if url.endswith('/container'):return httpx.Response(200,json={'status_code':'FINISHED'})
        return httpx.Response(200,json={'permalink':'https://www.instagram.com/p/synthetic/'})
    def post(url,**kwargs):
        requests.append((url,kwargs['data']))
        return httpx.Response(200,json={'id':'container' if url.endswith('/media') else 'synthetic-post'})
    monkeypatch.setattr(instagram_audio.httpx,'get',get);monkeypatch.setattr(social.httpx,'post',post)
    monkeypatch.setattr(social,'get_public_url',lambda *a:'https://example.test/synthetic.mp4')
    approved=review(client,body)
    tampered={**approved,'publish_options':{'instagram':{'format':'post','audio':{**CHOICE,'audio_volume':20}}}}
    assert client.post('/api/publish',json=tampered).status_code==409 and not requests
    result=client.post('/api/publish',json=approved)
    assert result.status_code==200 and result.json()['results']['instagram']['status']=='published'
    assert requests[0][1]['media_type']=='REELS'
    assert json.loads(requests[0][1]['audio_configuration'])=={'audio_id':'123456','audio_volume':80,'video_volume':30}
    assert all(data['access_token']=='synthetic-audio-user-token' for _,data in requests)
    with SessionLocal() as db:assert decrypt(db.get(SocialConnection,cid).encrypted_access_token)=='synthetic'


def test_audio_access_expiring_after_review_fails_before_media_creation(monkeypatch):
    client,uid,cid,body=audio_draft()
    monkeypatch.setattr(instagram_audio.httpx,'get',lambda *a,**k:httpx.Response(200,json=TRACK))
    approved=review(client,body)
    with SessionLocal() as db:db.get(SocialConnection,cid).audio_user_token_expires_at=utcnow()-timedelta(seconds=1);db.commit()
    result=client.post('/api/publish',json=approved)
    assert result.status_code==200 and result.json()['results']['instagram']['status']=='failed'
    with SessionLocal() as db:
        snapshot=json.loads(db.get(PublishReview,approved['review_token']).payload_json)
        assert snapshot['publish_options']['instagram']['audio']==CHOICE


@pytest.mark.parametrize('mime,placement',[('image/jpeg','post'),('video/mp4','story')])
def test_photo_and_story_audio_are_rejected_without_false_support(mime,placement):
    with pytest.raises(ValueError,match='video Reels only'):
        instagram_audio.validate_selection(None,CHOICE,[SimpleNamespace(mime_type=mime)],placement)


def test_preview_url_never_exposes_tokens_or_navigates_untrusted_origin():
    for url in ['https://evil.example/audio','javascript:alert(1)','https://www.instagram.com/?access_token=secret','https://user:pass@instagram.com/audio']:
        assert instagram_audio.safe_preview(url) is None


def test_confirmed_facebook_audio_grant_preserves_existing_direct_account(signed_in,monkeypatch):
    from nova import app as module
    from nova.db import PendingConnection
    client,uid=signed_in
    cid=connection(uid,scope='instagram_business_basic,instagram_business_content_publish',
        metadata_json='{"auth_provider":"instagram_login"}',encrypted_audio_user_token=None,audio_user_token_expires_at=None)
    monkeypatch.setattr(module,'meta_exchange',lambda code,**kw:[{'id':'page','access_token':'new-page-token',
        'granted_scope':'instagram_basic,instagram_content_publish','_audio_user_token':'private-audio-token','_audio_user_token_expires_in':7200,
        'instagram_business_account':{'id':'synthetic-ig','username':'creator'}}])
    start=client.get('/oauth/instagram/facebook/start',follow_redirects=False)
    pending=client.get('/oauth/meta/callback',params={'code':'synthetic','state':state_from(start)},follow_redirects=False)
    page=client.get(pending.headers['location'])
    assert page.status_code==200 and 'private-audio-token' not in page.text
    with SessionLocal() as db:
        staged=db.scalar(select(PendingConnection).where(PendingConnection.user_id==uid,PendingConnection.used.is_(False)))
        assert 'private-audio-token' not in staged.encrypted_payload
        assert 'private-audio-token' in decrypt(staged.encrypted_payload)
        assert db.get(SocialConnection,cid).encrypted_audio_user_token is None
    assert client.post(pending.headers['location'],data={'choice':0,'action':'connect'}).status_code==200
    with SessionLocal() as db:
        conn=db.get(SocialConnection,cid)
        assert decrypt(conn.encrypted_access_token)=='synthetic-page-token' # Original synthetic primary value, never replaced.
        assert json.loads(conn.metadata_json)['auth_provider']=='instagram_login'
        assert conn.scope=='instagram_business_basic,instagram_business_content_publish'
        assert decrypt(conn.encrypted_audio_user_token)=='private-audio-token'
        assert instagram_audio.eligibility(conn) is None
        assert db.scalar(select(PendingConnection).where(PendingConnection.user_id==uid)).encrypted_payload==''


def test_preserved_direct_primary_uses_facebook_graph_only_for_selected_music(monkeypatch):
    _,uid,*_=account();cid=connection(uid,metadata_json=json.dumps({'auth_provider':'instagram_login',
        'audio_auth_provider':'facebook_login','audio_scope':'instagram_basic,instagram_content_publish'}))
    calls=[]
    monkeypatch.setattr(social,'access_token',lambda *a:(_ for _ in ()).throw(AssertionError('Secondary audio must not refresh or substitute the primary token')))
    monkeypatch.setattr(social,'get_public_url',lambda *a:'https://example.test/synthetic.mp4')
    def get(url,**kwargs):
        calls.append(url)
        if url.endswith('/123456'):return httpx.Response(200,json=TRACK)
        if url.endswith('/container'):return httpx.Response(200,json={'status_code':'FINISHED'})
        return httpx.Response(200,json={})
    def post(url,**kwargs):
        calls.append(url)
        assert kwargs['data']['access_token']=='synthetic-audio-user-token'
        return httpx.Response(200,json={'id':'container' if url.endswith('/media') else 'published'})
    monkeypatch.setattr(social.httpx,'get',get);monkeypatch.setattr(social.httpx,'post',post)
    with SessionLocal() as db:
        conn=db.get(SocialConnection,cid)
        result=social.publish_instagram(db,conn,['caption'],[SimpleNamespace(mime_type='video/mp4',storage_key='synthetic',public_url='')],options={'audio':CHOICE})
        assert result['post_id']=='published'
        assert all(url.startswith('https://graph.facebook.com/') for url in calls)
        assert social.instagram_graph_base(conn)=='https://graph.instagram.com'


def test_meta_audio_token_is_private_and_does_not_expand_requested_scopes(monkeypatch):
    calls=[]
    def get(url,**kwargs):
        calls.append((url,kwargs))
        if url.endswith('/oauth/access_token'):return httpx.Response(200,json={'access_token':'private-user-token','expires_in':7200})
        if url.endswith('/me/accounts'):return httpx.Response(200,json={'data':[{'id':'page','access_token':'primary-page-token'}]})
        return httpx.Response(200,json={'data':[{'permission':'instagram_basic','status':'granted'},{'permission':'instagram_content_publish','status':'granted'}]})
    monkeypatch.setattr(social.httpx,'get',get)
    result=social.meta_exchange('synthetic',include_instagram=True)
    assert result[0]['access_token']=='primary-page-token'
    assert result[0]['_audio_user_token']=='private-user-token'
    assert result[0]['_audio_user_token_expires_in']==7200
    assert not any('scope' in kwargs.get('params',{}) for _,kwargs in calls)
