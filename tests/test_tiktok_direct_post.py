from types import SimpleNamespace
import copy
import httpx
import pytest
from nova import social, tiktok_policy as policy
from test_reviewed_publication import synthetic_storage


def setup(monkeypatch):
    monkeypatch.setenv('TIKTOK_SEND_TO_INBOX','false')
    monkeypatch.setenv('TIKTOK_VERIFIED_MEDIA_PREFIX','https://zova-social.com/media/raw/')
    monkeypatch.setattr(policy,'video_duration',lambda asset:6)
    monkeypatch.setattr(social,'access_token',lambda *a:'synthetic')
    monkeypatch.setattr(social,'get_bytes',lambda *a:b'synthetic')
    info={'creator_nickname':'Creator','privacy_level_options':['PUBLIC_TO_EVERYONE','SELF_ONLY'],'max_video_post_duration_sec':60,'comment_disabled':True}
    monkeypatch.setattr(social,'_tiktok_creator_info',lambda *a:info)
    asset=SimpleNamespace(mime_type='video/mp4',storage_key=synthetic_storage(),public_url='https://zova-social.com/media/raw/test.mp4')
    options={'posting_mode':'direct','privacy_level':'PUBLIC_TO_EVERYONE','consent':True}
    context={**info,'privacy_options':info['privacy_level_options'],'max_video_duration_sec':60}
    return asset,options,context,info


@pytest.mark.parametrize('change,message',[
    ({'consent':False},'Confirm TikTok'),
    ({'consent':'true'},'true or false'),
    ({'privacy_level':''},'privacy'),
    ({'commercial_content':True},'Select Your brand'),
    ({'your_brand':True},'Select Your brand'),
    ({'commercial_content':True,'brand_content':True,'privacy_level':'SELF_ONLY'},'Only me'),
    ({'allow_comment':True},'interaction'),
])
def test_reject_invalid_settings_before_any_delivery(monkeypatch,change,message):
    asset,options,context,_=setup(monkeypatch);options.update(change)
    with pytest.raises(ValueError,match=message):policy.validate_direct(options,context,['caption'],[asset])


def test_direct_video_uses_verified_pull_and_exact_options(monkeypatch):
    asset,options,_,_=setup(monkeypatch);options.update(commercial_content=True,brand_content=True,is_aigc=True)
    calls=[]
    def post(url,**kwargs):
        calls.append((url,kwargs['json']))
        return httpx.Response(200,json={'data':{'publish_id':'direct-receipt'},'error':{'code':'ok'}})
    monkeypatch.setattr(social.httpx,'post',post)
    result=social.publish_tiktok(None,None,['Reviewed caption'],[asset],options=options)
    assert calls[0][0].endswith('/video/init/') and '/inbox/' not in calls[0][0]
    body=calls[0][1]
    assert body['source_info']=={'source':'PULL_FROM_URL','video_url':asset.public_url}
    assert body['post_info']['title']=='Reviewed caption'
    assert body['post_info']['brand_content_toggle'] and body['post_info']['is_aigc']
    assert body['post_info']['disable_comment']
    assert result['pending'] and not result['requires_tiktok_completion']


@pytest.mark.parametrize('url',['https://zova-social.com.evil.test/media/raw/a.mp4','http://zova-social.com/media/raw/a.mp4','https://zova-social.com/media/rawish/a.mp4'])
def test_unverified_media_never_sent(monkeypatch,url):
    asset,options,context,_=setup(monkeypatch);asset.public_url=url
    with pytest.raises(ValueError,match='verified'):policy.validate_direct(options,context,['caption'],[asset])


def test_server_duration_and_utf16_limit(monkeypatch):
    asset,options,context,_=setup(monkeypatch)
    monkeypatch.setattr(policy,'video_duration',lambda asset:61)
    options['video_duration_sec']=1
    with pytest.raises(ValueError,match='duration'):policy.validate_direct(options,context,['caption'],[asset])
    monkeypatch.setattr(policy,'video_duration',lambda asset:6)
    with pytest.raises(ValueError,match='2,200'):policy.validate_direct(options,context,[chr(0x1f600)*1101],[asset])


def test_photo_disables_video_interactions_and_automatic_music(monkeypatch):
    asset,options,context,_=setup(monkeypatch);asset.mime_type='image/jpeg';options['is_aigc']=True
    with pytest.raises(ValueError,match='interaction'):policy.validate_direct({**options,'allow_duet':True},context,['photo'],[asset])
    calls=[]
    monkeypatch.setattr(social.httpx,'post',lambda url,**kw:(calls.append(kw['json']) or httpx.Response(200,json={'data':{'publish_id':'photo'}})))
    social.publish_tiktok(None,None,['photo'],[asset],options=options)
    assert calls[0]['post_mode']=='DIRECT_POST' and not calls[0]['post_info']['auto_add_music']
    assert calls[0]['is_aigc'] and 'is_aigc' not in calls[0]['post_info']


def test_direct_api_review_is_immutable_and_checks_creator_again(monkeypatch):
    from sqlalchemy import select
    from nova.db import SessionLocal,SocialConnection,MediaAsset
    from test_reviewed_publication import prepared
    asset,options,context,info=setup(monkeypatch)
    client,uid,_,body=prepared(('tiktok',))
    with SessionLocal() as db:
        conn=db.scalar(select(SocialConnection).where(SocialConnection.user_id==uid));conn.scope='user.info.basic,video.publish'
        media=MediaAsset(user_id=uid,filename='test.mp4',mime_type=asset.mime_type,storage_key=asset.storage_key,public_url=asset.public_url,size_bytes=20)
        db.add(media);db.commit();body['media_asset_ids']=[media.id]
    body['publish_options']={'tiktok':options}
    assert client.patch(f"/api/drafts/{body['draft_id']}",json={'platforms':['tiktok'],'variants':body['variants'],'workspace':{'media_asset_ids':body['media_asset_ids']}}).status_code==200
    reviewed=client.post('/api/publish-review',json=body)
    assert reviewed.status_code==200,reviewed.text
    approved={**body,'review_token':reviewed.json()['review_token']}
    changed=copy.deepcopy(approved);changed['publish_options']['tiktok']['is_aigc']=True
    assert client.post('/api/publish',json=changed).status_code==409
    calls=[]
    monkeypatch.setattr(social.httpx,'post',lambda url,**kw:(calls.append(url) or httpx.Response(200,json={'data':{'publish_id':'receipt'}})))
    result=client.post('/api/publish',json=approved)
    assert result.status_code==200,result.text
    assert result.json()['results']['tiktok']['status']=='pending'
    client.post('/api/publish',json=approved)
    assert len(calls)==1


def test_changed_creator_interactions_block_dispatch(monkeypatch):
    asset,options,context,info=setup(monkeypatch)
    options['allow_duet']=True
    policy.validate_direct(options,context,['caption'],[asset])
    info['duet_disabled']=True
    with pytest.raises(RuntimeError,match='interaction'):
        social.publish_tiktok(None,None,['caption'],[asset],options=options)


def test_corrupt_video_duration_fails_closed():
    with pytest.raises(ValueError,match='duration'):
        policy.video_duration(SimpleNamespace(storage_key='missing-synthetic-video'))
