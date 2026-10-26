"""Instagram's licensed Reel audio, using a separate encrypted Facebook User grant.

Meta's Audio API does not support Instagram Login, photos or Stories. Existing
Page tokens remain untouched and are never substituted for a required User token.
"""
import os
import re
from datetime import timezone
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select

from .db import SocialConnection, get_db, utcnow
from .request_security import allowed_request
from .security import current_user, decrypt
from .social import json_meta, selected_connection

router=APIRouter()
MAX_TRACKS=25


def eligibility(conn):
    if conn.platform!='instagram' or not conn.active:
        return 'Connect an Instagram account first.'
    metadata=json_meta(conn)
    if metadata.get('auth_provider')!='facebook_login' and metadata.get('audio_auth_provider')!='facebook_login':
        return 'Instagram Login does not support music search. Add music in Instagram, or connect through Facebook for Reel music.'
    if not getattr(conn,'encrypted_audio_user_token',None):
        return 'This connection predates Reel music. Reconnect Instagram through Facebook to enable it, or add music in Instagram.'
    expiry=conn.audio_user_token_expires_at
    if not expiry or (expiry if expiry.tzinfo else expiry.replace(tzinfo=timezone.utc))<=utcnow():
        return 'Reel music access has expired. Reconnect Instagram through Facebook, or add music in Instagram.'
    scopes=set((metadata.get('audio_scope',conn.scope) or '').replace(' ',',').split(','))
    if not {'instagram_basic','instagram_content_publish'}.issubset(scopes):
        return 'The Facebook connection does not include Instagram publishing permission.'
    return None


def provider_get(conn,path,**params):
    reason=eligibility(conn)
    if reason:raise ValueError(reason)
    try:
        token=decrypt(conn.encrypted_audio_user_token)
        response=httpx.get(f"https://graph.facebook.com/{os.environ.get('META_GRAPH_VERSION','v23.0')}/{path}",
            params={'access_token':token,'user_id':conn.account_id,**params},timeout=15.0)
        data=response.json()
        if response.status_code>=400 or not isinstance(data,dict) or data.get('error'):
            raise ValueError('Instagram music is unavailable for this account. Keep the original audio or add music in Instagram.')
        return data
    except (httpx.HTTPError,TypeError,KeyError,RuntimeError):
        raise ValueError('Instagram music could not be checked. Try again; your selection is retained.') from None
    except ValueError as exc:
        # Do not expose provider payloads, URLs or credentials from decoder errors.
        if str(exc).startswith('Instagram music'):raise
        raise ValueError('Instagram music could not be checked. Try again; your selection is retained.') from None


def text(value,limit=160):
    return ' '.join(str(value or '').split())[:limit]


def safe_preview(value):
    if not isinstance(value,str):return None
    try:
        url=urlsplit(value)
        if (url.scheme=='https' and not url.username and not url.password
                and url.hostname in {'www.instagram.com','instagram.com'}
                and not any(key in url.query.lower() for key in ('access_token','token='))):
            return value[:2000]
    except ValueError:pass
    return None


def clean_track(item):
    if not isinstance(item,dict) or not re.fullmatch(r'\d{1,40}',str(item.get('audio_id',''))):return None
    title=text(item.get('title'))
    if not title:return None
    duration=item.get('duration_in_ms')
    return {'audio_id':str(item['audio_id']),'title':title,
        'artist':text(item.get('display_artist') or item.get('ig_username')),
        'duration_in_ms':duration if isinstance(duration,int) and not isinstance(duration,bool) and duration>0 else None,
        'audio_type':item.get('audio_type') if item.get('audio_type') in {'music','original_sound'} else 'music',
        'preview_url':safe_preview(item.get('on_platform_audio_preview_link'))}


@router.get('/api/instagram/audio')
def search_audio(request:Request,connection_id:int|None=Query(None,gt=0),q:str=Query('',max_length=120),
                 audio_type:str=Query('music',pattern='^(music|original_sound)$'),db=Depends(get_db)):
    uid=current_user(request).id
    if not allowed_request(f'instagram-audio:{uid}',30,300):raise HTTPException(429,'Please wait before searching for more music.')
    accounts=[{'id':row.id,'name':row.display_name or row.username or 'Instagram account'} for row in db.scalars(
        select(SocialConnection).where(SocialConnection.user_id==uid,SocialConnection.platform=='instagram',
            SocialConnection.active.is_(True)).order_by(SocialConnection.id.desc()))]
    try:conn=selected_connection(db,uid,'instagram',connection_id)
    except RuntimeError:
        if connection_id:raise HTTPException(404,'Instagram connection not found')
        return {'eligible':False,'reason':'Connect Instagram to check music availability.','tracks':[],'format':'reel','preview_supported':False,'accounts':accounts,'connection_id':None}
    reason=eligibility(conn)
    if reason:return {'eligible':False,'reason':reason,'tracks':[],'format':'reel','preview_supported':False,'accounts':accounts,'connection_id':conn.id}
    params={'audio_type':audio_type}
    if q.strip():params['search_query']=q.strip()
    try:data=provider_get(conn,'ig_audio',**params)
    except ValueError as exc:raise HTTPException(502,str(exc)) from None
    raw=data.get('audio',[])
    if not isinstance(raw,list):raise HTTPException(502,'Instagram returned incomplete music results. Try again.')
    tracks=[track for item in raw[:MAX_TRACKS] if (track:=clean_track(item))]
    return {'eligible':True,'reason':'Music is added when the Reel publishes; a mixed preview is unavailable.',
        'tracks':tracks,'format':'reel','preview_supported':False,'connection_id':conn.id,'accounts':accounts}


def validate_selection(conn,selection,assets,placement='post'):
    if not isinstance(selection,dict):raise ValueError('Choose a valid Instagram track.')
    if placement!='post' or len(assets)!=1 or not assets[0].mime_type.startswith('video/'):
        raise ValueError('Music search supports video Reels only. Add music to photos or Stories in Instagram.')
    reason=eligibility(conn)
    if reason:raise ValueError(reason)
    audio_id=selection.get('audio_id')
    if not isinstance(audio_id,str) or not re.fullmatch(r'\d{1,40}',audio_id):raise ValueError('Choose a valid Instagram track.')
    volumes={}
    for key in ('audio_volume','video_volume'):
        value=selection.get(key,100)
        if type(value) is not int or not 1<=value<=100:raise ValueError('Choose audio volumes between 1 and 100.')
        volumes[key]=value
    track=clean_track(provider_get(conn,audio_id))
    if not track or track['audio_id']!=audio_id:raise ValueError('This track is no longer available. Choose another track.')
    if selection.get('title')!=track['title'] or selection.get('artist','')!=track['artist']:
        raise ValueError('The track details changed. Search and select the track again before reviewing.')
    return {'audio_id':audio_id,'title':track['title'],'artist':track['artist'],**volumes}
