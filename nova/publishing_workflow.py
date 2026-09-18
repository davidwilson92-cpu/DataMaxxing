"""Durable reviewed snapshots and one publication ledger entry per draft/platform."""
import json
import os
import secrets
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from sqlalchemy import select,update
from sqlalchemy.exc import IntegrityError
from .db import Draft,MediaAsset,SocialConnection,PublishReview,Publication,ScheduledPost,Activity,get_preferences,utcnow
from .workspace import EDITABLE,PLATFORMS
from .social import selected_connection,publishing_context,publish_platform
from . import allowances

TERMINAL={'published','pending','publishing','unknown','scheduled','queued'}


def owned_draft(db,uid,draft_id):
    row=db.get(Draft,draft_id) if draft_id else None
    if not row or row.user_id!=uid:raise HTTPException(404,'Draft not found')
    return row


def capability_error(conn,media):
    scopes=set((conn.scope or '').replace(' ',',').split(','))
    if conn.platform=='x' and 'tweet.write' not in scopes:
        return 'This X connection does not have publishing permission.'
    if conn.platform=='facebook' and 'pages_manage_posts' not in scopes:
        return 'Facebook publishing permission is not present on this connection. Existing access is preserved; publishing needs separately approved permissions.'
    if conn.platform=='instagram' and not scopes.intersection({'instagram_business_content_publish','instagram_content_publish'}):
        return 'This Instagram connection does not have publishing permission. Review its connection settings.'
    if conn.platform=='tiktok':
        inbox=os.environ.get('TIKTOK_SEND_TO_INBOX','false').lower() in {'1','true','yes'}
        required='video.upload' if inbox else 'video.publish'
        if required not in scopes:return 'This TikTok connection supports a different publishing mode. Reconcile the approved mode before publishing.'
        if inbox and (len(media)!=1 or not media[0].mime_type.startswith('video/')):
            return 'The current TikTok mode sends one video for completion in TikTok.'
    return None


def schedule_time(value,tz):
    try:
        local=datetime.fromisoformat(value)
        if local.tzinfo is None:
            zone=ZoneInfo(tz)
            first=local.replace(tzinfo=zone,fold=0);second=local.replace(tzinfo=zone,fold=1)
            if first.utcoffset()!=second.utcoffset():raise ValueError('ambiguous')
            local=first
            if local.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None)!=local.replace(tzinfo=None):raise ValueError('nonexistent')
        result=local.astimezone(timezone.utc)
        if result<=utcnow()+timedelta(minutes=1):raise ValueError('past')
        return result
    except (ValueError,TypeError):raise HTTPException(400,'Choose a future time with an explicit timezone offset. Avoid ambiguous daylight-saving times.')


def prepare_review(db,uid,body):
    draft=owned_draft(db,uid,body.draft_id)
    if draft.status not in EDITABLE:raise HTTPException(409,'This draft is already submitted. Check its results.')
    variants=json.loads(draft.variants_json or '{}');workspace=json.loads(draft.workspace_json or '{}')
    platforms=list(dict.fromkeys(body.platforms))
    if not platforms or any(p not in PLATFORMS for p in platforms):raise HTTPException(400,'Choose supported platforms.')
    if any(body.variants.get(p)!=variants.get(p) for p in platforms):raise HTTPException(409,'Save your latest text before reviewing.')
    media=[]
    for mid in list(dict.fromkeys(body.media_asset_ids)):
        asset=db.get(MediaAsset,mid)
        if not asset or asset.user_id!=uid:raise HTTPException(404,'Attachment not found')
        media.append(asset)
    if len(media)>10:raise HTTPException(400,'Choose at most ten images.')
    videos=[a for a in media if a.mime_type.startswith('video/')]
    if videos and (len(media)!=1 or any(p not in {'instagram','tiktok'} for p in platforms)):
        raise HTTPException(400,'Use one video with Instagram or TikTok only.')
    if workspace and (workspace.get('media_asset_ids',[])!=body.media_asset_ids or workspace.get('link_url','')!=body.link_url):
        raise HTTPException(409,'Save your current media and source link before reviewing.')
    targets={};options=body.publish_options or {}
    for p in platforms:
        previous=db.scalar(select(Publication).where(Publication.draft_id==draft.id,Publication.platform==p))
        history=db.scalar(select(Activity).where(Activity.draft_id==draft.id,Activity.user_id==uid,Activity.platform==p,Activity.status.in_(TERMINAL)))
        if (previous and previous.status in TERMINAL) or history:raise HTTPException(409,f'{p}: already submitted or awaiting confirmation. Retry only failed destinations.')
        posts=(variants.get(p) or {}).get('posts',[])
        if not posts or any(not isinstance(t,str) or not t.strip() for t in posts):raise HTTPException(400,f'{p}: add finished draft text.')
        if p in {'instagram','facebook'} and len(media)>1:raise HTTPException(400,f'{p}: this publishing route supports one image or video. Select one attachment; multiple images will not be silently dropped.')
        if p=='x' and len(media)>4:raise HTTPException(400,'X supports at most four images per post.')
        posts=[text.strip() for text in posts]
        # Finalise link insertion before review, then prevent adapter mutations.
        if body.link_url and p in {'x','instagram','tiktok'} and body.link_url not in posts[0]:
            posts[0]+= ('\n\n' if p=='instagram' else ' ') + body.link_url
        if p in {'instagram','tiktok'} and len(posts[0])>2200:raise HTTPException(400,f'{p}: shorten the caption and source link to 2,200 characters.')
        if p=='x' and (len(posts)>5 or any(len(t)>280 for t in posts)):raise HTTPException(400,'An X post exceeds its limit.')
        if p!='x' and len(posts)!=1:raise HTTPException(400,'Use one caption per platform.')
        if p in {'instagram','tiktok'} and not media:raise HTTPException(400,f'{p}: attach an image or video first.')
        try:
            conn=selected_connection(db,uid,p,(body.connection_ids or {}).get(p))
            problem=capability_error(conn,media)
            if problem:raise HTTPException(400,problem)
            context=publishing_context(db,uid,p,conn.id)
        except RuntimeError:raise HTTPException(400,f'Connect or reconnect {p} before publishing.')
        if p=='tiktok':
            settings=options.get(p,{})
            if settings.get('privacy_level') not in context.get('privacy_options',[]):raise HTTPException(400,'Choose an available TikTok privacy setting.')
            for key,disabled in [('allow_comment','comment_disabled'),('allow_duet','duet_disabled'),('allow_stitch','stitch_disabled')]:
                if settings.get(key) and context.get(disabled):raise HTTPException(400,'A selected TikTok interaction is unavailable.')
            if videos:
                duration=float(settings.get('video_duration_sec') or 0)
                if duration<=0 or (context.get('max_video_duration_sec') and duration>context['max_video_duration_sec']):raise HTTPException(400,'Check the video duration for this TikTok account.')
        targets[p]={'connection_id':conn.id,'account_id':conn.account_id,'username':context.get('username'),'display_name':context.get('display_name'),'posts':posts,'link':body.link_url if p=='facebook' and not media else ''}
    tz=get_preferences(db,uid).timezone
    scheduled=getattr(body,'scheduled_local',None)
    if scheduled:scheduled=schedule_time(scheduled,tz).isoformat()
    payload={'draft_id':draft.id,'platforms':platforms,'variants':{p:variants[p] for p in platforms},'media_asset_ids':body.media_asset_ids,'media':[{'filename':a.filename,'kind':'video' if a.mime_type.startswith('video/') else 'image','url':a.public_url or f'/media/preview/{a.id}'} for a in media],
             'link_url':body.link_url,'publish_options':options,'targets':targets,'scheduled_utc':scheduled,'timezone':tz}
    row=PublishReview(code=secrets.token_urlsafe(24),user_id=uid,draft_id=draft.id,revision=draft.revision,payload_json=json.dumps(payload,ensure_ascii=False),expires_at=utcnow()+timedelta(minutes=15))
    db.add(row);db.commit()
    return {'review_token':row.code,'snapshot':payload,'expires_in':900}


def results_for(db,uid,draft_id):
    rows=db.scalars(select(Publication).where(Publication.user_id==uid,Publication.draft_id==draft_id)).all()
    results={r.platform:{**json.loads(r.result_json or '{}'),'status':r.status} for r in rows}
    draft=owned_draft(db,uid,draft_id)
    return {'draft_status':draft.status,'results':results,'summary':' '.join(f"{'X' if p=='x' else p.title()}: {r['status'].replace('_',' ')}." for p,r in results.items())}


def update_draft_status(db,draft_id):
    rows=db.scalars(select(Publication).where(Publication.draft_id==draft_id)).all()
    statuses={r.status for r in rows}
    status='needs_review' if statuses.intersection({'unknown','publishing','queued'}) else 'scheduled' if 'scheduled' in statuses else 'pending' if 'pending' in statuses else 'partial' if 'failed' in statuses and 'published' in statuses else 'failed' if 'failed' in statuses else 'published' if 'published' in statuses else 'cancelled'
    db.execute(update(Draft).where(Draft.id==draft_id).values(status=status));db.commit()


def dispatch(db,publication,payload,publisher=publish_platform):
    target=payload['targets'][publication.platform]
    claimed=db.execute(update(Publication).where(Publication.id==publication.id,Publication.status.in_(['queued','scheduled'])).values(status='publishing',updated_at=utcnow()).execution_options(synchronize_session=False))
    if claimed.rowcount!=1:db.rollback();return
    db.commit();db.refresh(publication)
    # Fail before the provider call if the exact reviewed connection/media no longer exists.
    try:
        conn=selected_connection(db,publication.user_id,publication.platform,target['connection_id'])
        if conn.account_id!=target['account_id']:raise RuntimeError('Account changed')
        media=[db.get(MediaAsset,i) for i in payload['media_asset_ids']]
        if any(not a or a.user_id!=publication.user_id for a in media):raise RuntimeError('Media unavailable')
        if capability_error(conn,media):raise RuntimeError('Permission changed')
    except RuntimeError:
        publication.status='failed';publication.result_json=json.dumps({'error':'The reviewed account, media or permissions are unavailable. Reconnect/review before retrying.'});allowances.finish(db,f'publication:{publication.id}',False);db.commit();return
    try:
        result=publisher(db,user_id=publication.user_id,platform=publication.platform,posts=target['posts'],assets=media,link_url=target.get('link',''),options=payload['publish_options'].get(publication.platform,{}),connection_id=target['connection_id'])
        publication.status='pending' if result.get('pending') else 'published';publication.result_json=json.dumps(result)
    except Exception:
        db.rollback();db.refresh(publication)
        publication.status='unknown';publication.result_json=json.dumps({'error':'The provider outcome is unconfirmed. Check your social account before retrying; Zova will not resend automatically.'})
    result=json.loads(publication.result_json)
    allowances.finish(db,f'publication:{publication.id}')
    db.add(Activity(user_id=publication.user_id,brand_id=publication.brand_id,draft_id=publication.draft_id,platform=publication.platform,action='publish',status=publication.status,text='\n\n'.join(target['posts']),platform_post_id=result.get('post_id'),url=result.get('url'),error=result.get('error')))
    db.commit()


def confirm_review(db,uid,body,mode,publisher=publish_platform):
    review=db.get(PublishReview,body.review_token) if body.review_token else None
    if not review or review.user_id!=uid or review.draft_id!=body.draft_id:raise HTTPException(400,'Review this draft before confirming publication.')
    if review.status!='review':return results_for(db,uid,review.draft_id)
    payload=json.loads(review.payload_json)
    if bool(payload['scheduled_utc'])!=(mode=='schedule'):raise HTTPException(400,'Review the selected publication mode again.')
    if body.platforms!=payload['platforms'] or body.variants!=payload['variants'] or body.media_asset_ids!=payload['media_asset_ids'] or body.link_url!=payload['link_url'] or body.publish_options!=payload['publish_options']:
        raise HTTPException(409,'The submission differs from the reviewed content. Review again.')
    draft=owned_draft(db,uid,review.draft_id)
    current=json.loads(draft.variants_json or '{}');ws=json.loads(draft.workspace_json or '{}')
    if any(current.get(p)!=payload['variants'][p] for p in payload['platforms']) or (ws and (ws.get('media_asset_ids',[])!=payload['media_asset_ids'] or ws.get('link_url','')!=payload['link_url'])):
        raise HTTPException(409,'The draft changed after review. Review the latest version.')
    claimed=db.execute(update(PublishReview).where(PublishReview.code==review.code,PublishReview.status=='review',PublishReview.expires_at>utcnow()).values(status='submitted').execution_options(synchronize_session=False))
    locked=db.execute(update(Draft).where(Draft.id==draft.id,Draft.revision==draft.revision,Draft.status.in_(EDITABLE)).values(status='scheduled' if mode=='schedule' else 'publishing').execution_options(synchronize_session=False))
    if claimed.rowcount!=1 or locked.rowcount!=1:db.rollback();raise HTTPException(409,'Review expired or this draft is already being submitted.')
    if mode=='schedule':schedule_time(payload['scheduled_utc'],payload['timezone'])
    jobs=[]
    try:
        for platform,target in payload['targets'].items():
            row=db.scalar(select(Publication).where(Publication.draft_id==draft.id,Publication.platform==platform))
            if row and row.status not in {'failed','cancelled'}:raise HTTPException(409,'A destination is already submitted.')
            if not row:row=Publication(user_id=uid,draft_id=draft.id,platform=platform,connection_id=target['connection_id'],review_code=review.code);db.add(row)
            row.status='scheduled' if mode=='schedule' else 'queued';row.connection_id=target['connection_id'];row.review_code=review.code;row.result_json='{}';db.flush();jobs.append(row)
            allowances.reserve(db,uid,'publications',f'publication:{row.id}',len(target['posts']))
            if mode=='schedule':db.add(ScheduledPost(user_id=uid,draft_id=draft.id,platform=platform,connection_id=target['connection_id'],content_json=json.dumps({'review_code':review.code,'publication_id':row.id,'posts':target['posts']}),media_asset_ids_json=json.dumps(payload['media_asset_ids']),scheduled_at=datetime.fromisoformat(payload['scheduled_utc']),status='scheduled'))
        db.commit()
    except HTTPException:
        db.rollback();raise
    except IntegrityError:db.rollback();raise HTTPException(409,'This destination already has a submission. Check its results.')
    if mode=='publish':
        for job in jobs:dispatch(db,job,payload,publisher)
        update_draft_status(db,draft.id)
    return results_for(db,uid,draft.id)
