"""Provider contracts with synthetic tokens/media; external HTTP stays blocked."""
from types import SimpleNamespace
import httpx
import pytest
from nova import social
from nova.publishing_workflow import capability_error


def test_requested_permissions_do_not_change_instagram(monkeypatch):
    assert social.INSTAGRAM_FACEBOOK_SCOPES == 'pages_show_list,pages_read_engagement,business_management,instagram_basic,instagram_content_publish'
    assert social.META_SCOPES == 'pages_show_list,pages_read_engagement,pages_manage_posts'
    assert 'media.write' in social.X_SCOPES.split()
    monkeypatch.setenv('TIKTOK_SEND_TO_INBOX', 'true')
    assert social.tiktok_scopes() == 'user.info.basic,video.upload'
    monkeypatch.setenv('TIKTOK_SEND_TO_INBOX', 'false')
    assert social.tiktok_scopes() == 'user.info.basic,video.publish'


@pytest.mark.parametrize('include_instagram', [False, True])
def test_meta_reads_actual_grants_only_for_facebook(monkeypatch, include_instagram):
    calls=[]
    def get(url, **kwargs):
        calls.append(url)
        if url.endswith('/oauth/access_token'):
            return httpx.Response(200,json={'access_token':'synthetic'})
        if url.endswith('/me/accounts'):
            return httpx.Response(200,json={'data':[{'id':'page','access_token':'synthetic-page'}]})
        assert url.endswith('/me/permissions')
        return httpx.Response(200,json={'data':[
            {'permission':'pages_show_list','status':'granted'},
            {'permission':'pages_manage_posts','status':'declined'}]})
    monkeypatch.setattr(social.httpx,'get',get)
    rows=social.meta_exchange('synthetic',include_instagram=include_instagram)
    assert len(calls)==(3 if include_instagram else 4)
    if not include_instagram:
        assert rows[0]['granted_scope']=='pages_show_list'


def test_x_text_remains_available_without_media_grant():
    conn=SimpleNamespace(platform='x',scope='tweet.read tweet.write')
    assert capability_error(conn,[]) is None
    assert 'Reconnect X' in capability_error(conn,[object()])
    conn.scope+=' media.write'
    assert capability_error(conn,[object()]) is None


def test_inbox_context_does_not_call_direct_post_api(monkeypatch):
    monkeypatch.setenv('TIKTOK_SEND_TO_INBOX','true')
    conn=SimpleNamespace(id=1,account_id='synthetic-id',scope='user.info.basic,video.upload',username='tester',display_name='Test')
    monkeypatch.setattr(social,'selected_connection',lambda *args:conn)
    result=social.publishing_context(None,1,'tiktok')
    assert result['posting_mode']=='inbox'
    assert result['requires_tiktok_completion'] is True
    assert 'privacy_options' not in result


@pytest.mark.parametrize('size',[1024,32*1024*1024+1,64*1024*1024+1])
def test_inbox_upload_chunks_and_pending_result(monkeypatch,size):
    monkeypatch.setenv('TIKTOK_SEND_TO_INBOX','true')
    monkeypatch.setattr(social,'access_token',lambda *args:'synthetic')
    monkeypatch.setattr(social,'get_bytes',lambda key:b'x'*size)
    calls=[];uploads=[]
    def post(url,**kwargs):
        assert url.endswith('/inbox/video/init/')
        calls.append(kwargs['json'])
        return httpx.Response(200,json={'data':{'publish_id':'receipt','upload_url':'https://upload.example.test/video'},'error':{'code':'ok'}})
    def put(url,**kwargs):
        uploads.append((len(kwargs['content']),kwargs['headers']['Content-Range']))
        return httpx.Response(201)
    monkeypatch.setattr(social.httpx,'post',post)
    monkeypatch.setattr(social.httpx,'put',put)
    asset=SimpleNamespace(mime_type='video/mp4',storage_key='synthetic-video')
    result=social.publish_tiktok(None,None,['Reference caption'],[asset],options={'posting_mode':'inbox'})
    assert len(calls)==1 and 'post_info' not in calls[0]
    source=calls[0]['source_info']
    assert source['total_chunk_count']==len(uploads)==max(1,size//(32*1024*1024))
    assert sum(n for n,_ in uploads)==size
    assert uploads[-1][1].endswith(f'-{size-1}/{size}')
    assert result['pending'] is True and result['requires_tiktok_completion'] is True


def test_reviewed_delivery_mode_cannot_change(monkeypatch):
    monkeypatch.setenv('TIKTOK_SEND_TO_INBOX','true')
    monkeypatch.setattr(social,'access_token',lambda *args:'synthetic')
    with pytest.raises(RuntimeError,match='mode changed'):
        social.publish_tiktok(None,None,['caption'],[object()],options={'posting_mode':'direct'})


def test_direct_creator_api_error_is_not_an_empty_success(monkeypatch):
    monkeypatch.setattr(social.httpx,'post',lambda *a,**k:httpx.Response(200,json={'error':{'code':'scope_not_authorized'}}))
    with pytest.raises(RuntimeError):
        social._tiktok_creator_info('synthetic')


def test_inbox_review_upload_status_and_duplicate_protection(monkeypatch):
    from sqlalchemy import select
    from nova.db import SessionLocal, SocialConnection, MediaAsset
    from test_reviewed_publication import prepared
    monkeypatch.setenv('TIKTOK_SEND_TO_INBOX','true')
    client,uid,_,body=prepared(('tiktok',))
    with SessionLocal() as db:
        conn=db.scalar(select(SocialConnection).where(SocialConnection.user_id==uid))
        conn.scope='user.info.basic,video.upload'
        asset=MediaAsset(user_id=uid,filename='test.mp4',mime_type='video/mp4',storage_key='synthetic',size_bytes=100)
        db.add(asset);db.commit();body['media_asset_ids']=[asset.id]
    body['publish_options']={'tiktok':{'posting_mode':'inbox'}}
    saved=client.patch(f"/api/drafts/{body['draft_id']}",json={'platforms':['tiktok'],'variants':body['variants'],'workspace':{'media_asset_ids':body['media_asset_ids']}})
    assert saved.status_code==200
    reviewed=client.post('/api/publish-review',json=body)
    assert reviewed.status_code==200,reviewed.text
    assert reviewed.json()['snapshot']['targets']['tiktok']['requires_tiktok_completion']
    approved={**body,'review_token':reviewed.json()['review_token']}
    changed={**approved,'publish_options':{'tiktok':{'posting_mode':'direct'}}}
    assert client.post('/api/publish',json=changed).status_code==409
    monkeypatch.setattr(social,'get_bytes',lambda *args:b'synthetic-video')
    calls=[]
    def post(url,**kwargs):
        assert url.endswith('/inbox/video/init/')
        calls.append(url)
        return httpx.Response(200,json={'data':{'publish_id':'synthetic-receipt','upload_url':'https://upload.example.test/video'}})
    monkeypatch.setattr(social.httpx,'post',post)
    monkeypatch.setattr(social.httpx,'put',lambda *a,**kw:httpx.Response(201))
    result=client.post('/api/publish',json=approved)
    assert result.status_code==200,result.text
    assert result.json()['results']['tiktok']['status']=='pending'
    assert result.json()['results']['tiktok']['requires_tiktok_completion']
    client.post('/api/publish',json=approved)
    assert len(calls)==1
    import nova.scheduler as worker
    monkeypatch.setattr(worker,'resolve_tiktok_post',lambda *a:{'status':'SEND_TO_USER_INBOX'})
    worker.process_due()
    result=client.get(f"/api/publications/{body['draft_id']}").json()['results']['tiktok']
    assert result['status']=='pending' and result['delivered_to_inbox']
    monkeypatch.setattr(worker,'resolve_tiktok_post',lambda *a:{'status':'PUBLISH_COMPLETE','public_ids':['public-test-id']})
    worker.process_due()
    result=client.get(f"/api/publications/{body['draft_id']}").json()['results']['tiktok']
    assert result['status']=='published' and not result['requires_tiktok_completion']
    assert len(calls)==1


def test_unapproved_tiktok_analytics_are_unavailable(monkeypatch):
    conn=SimpleNamespace(platform='tiktok',scope='user.info.basic,video.upload')
    monkeypatch.setattr(social,'access_token',lambda *args:'synthetic')
    assert social.follower_count(None,conn) is None
    assert social.recent_content_for_connection(None,conn)==[]
    with pytest.raises(RuntimeError,match='separately approved'):
        social.analytics_tiktok(None,conn,[])


@pytest.mark.parametrize('platform',['x','facebook'])
def test_review_to_provider_adapter_receipt_and_no_duplicate(monkeypatch,platform):
    from test_reviewed_publication import prepared,review
    client,_,_,body=prepared((platform,))
    approved=review(client,body);calls=[]
    def post(url,**kwargs):
        calls.append((url,kwargs))
        if platform=='x':
            assert kwargs['json']['text']==body['variants'][platform]['posts'][0]
            return httpx.Response(201,json={'data':{'id':'synthetic-x'}})
        assert url.endswith('/original-facebook/feed')
        assert kwargs['data']['message']==body['variants'][platform]['posts'][0]
        return httpx.Response(200,json={'id':'synthetic-fb'})
    monkeypatch.setattr(social.httpx,'post',post)
    result=client.post('/api/publish',json=approved)
    assert result.status_code==200,result.text
    assert result.json()['results'][platform]['status']=='published'
    client.post('/api/publish',json=approved)
    assert len(calls)==1


def test_partial_x_thread_is_not_resent(monkeypatch):
    from test_reviewed_publication import prepared,review
    client,_,_,body=prepared(('x',))
    body['variants']['x']['posts']=['First part','Second part']
    client.patch(f"/api/drafts/{body['draft_id']}",json={'platforms':['x'],'variants':body['variants']})
    approved=review(client,body);calls=[]
    def post(url,**kwargs):
        calls.append(kwargs['json'])
        if len(calls)==1:return httpx.Response(201,json={'data':{'id':'first-receipt'}})
        assert kwargs['json']['reply']['in_reply_to_tweet_id']=='first-receipt'
        raise httpx.ReadTimeout('synthetic timeout')
    monkeypatch.setattr(social.httpx,'post',post)
    result=client.post('/api/publish',json=approved)
    assert result.json()['results']['x']['status']=='unknown'
    client.post('/api/publish',json=approved)
    assert len(calls)==2


def test_facebook_missing_receipt_is_not_success(monkeypatch):
    monkeypatch.setattr(social,'access_token',lambda *a:'synthetic')
    monkeypatch.setattr(social.httpx,'post',lambda *a,**k:httpx.Response(200,json={}))
    with pytest.raises(RuntimeError):
        social.publish_facebook(None,SimpleNamespace(account_id='page'),['caption'],[])
