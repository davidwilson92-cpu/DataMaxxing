"""Versioned workspace persistence; browser metadata is never authoritative for assets."""
import json
import math
from fastapi import HTTPException
from sqlalchemy import update, select, delete
from .db import Draft, MediaAsset, utcnow

EDITABLE={'draft','failed','partial','cancelled'}
PLATFORMS={'x','instagram','facebook','tiktok'}
MAX_WORKSPACE_MEDIA=200


def delete_unsubmitted_draft(db,row):
    from .db import Publication,PublishReview,ScheduledPost,Activity
    if row.status not in EDITABLE or any(db.scalar(select(model.id).where(model.draft_id==row.id).limit(1)) for model in (Publication,ScheduledPost,Activity)):
        raise HTTPException(409,'This draft has delivery records and is retained in your history.')
    db.execute(delete(PublishReview).where(PublishReview.draft_id==row.id))
    from .db import StrategyAction, SeriesOccurrence
    db.execute(update(StrategyAction).where(StrategyAction.draft_id==row.id).values(draft_id=None,status="dismissed"))
    db.execute(update(SeriesOccurrence).where(SeriesOccurrence.draft_id==row.id).values(draft_id=None,status="cancelled"))
    db.delete(row);db.commit()


def clean_text_history(value):
    if not isinstance(value,list): raise HTTPException(400,'Invalid text history')
    result=[]
    for snapshot in value[-3:]:
        if not isinstance(snapshot,dict): raise HTTPException(400,'Invalid text revision')
        clean={}
        for platform,variant in snapshot.items():
            if platform not in PLATFORMS: continue
            if not isinstance(variant,dict) or not isinstance(variant.get('posts'),list): raise HTTPException(400,'Invalid text revision')
            clean[platform]={'posts':[str(post)[:5000] for post in variant['posts'][:5]]}
        if clean: result.append(clean)
    return result


def _message_media_ids(value):
    """Only IDs persisted on user turns establish a historical attachment."""
    messages=value.get('conversation',[]) if isinstance(value,dict) else []
    if not isinstance(messages,list):return set()
    return {aid for message in messages[:200] if isinstance(message,dict) and message.get('role')=='user'
            for aid in (message.get('media_asset_ids',[]) if isinstance(message.get('media_asset_ids',[]),list) else [])[:10]
            if type(aid) is int}


def _workspace_media(value, db, user_id, *, previous_workspace=None, strict=True):
    """Resolve active and historical media from records, never browser URLs.

    Historical references can outlive removal from the current post or deletion
    of the upload. A missing ID may be saved only if it was previously recorded
    on a user turn; an existing foreign asset is never accepted as missing.
    """
    def selection(ids):
        valid=lambda aid:type(aid) is int and 0<aid<=2**63-1
        if not isinstance(ids,list) or len(ids)>10 or any(not valid(aid) for aid in ids):
            if strict:raise HTTPException(400,'Invalid attachment selection')
            ids=[aid for aid in ids[:10] if valid(aid)] if isinstance(ids,list) else []
        return list(dict.fromkeys(ids))

    active_ids=selection(value.get('media_asset_ids',[]))
    pending_ids=selection(value.get('pending_media_asset_ids',[])) if value.get('pending_message') else []
    raw_messages=value.get('conversation',[])
    if not isinstance(raw_messages,list) or len(raw_messages)>200:
        if strict:raise HTTPException(400,'Conversation is too long; start a new chat.')
        raw_messages=raw_messages[:200] if isinstance(raw_messages,list) else []
    messages=[]
    all_ids=set(active_ids+pending_ids)
    for raw in raw_messages:
        if not isinstance(raw,dict) or raw.get('role') not in {'assistant','user'}:continue
        message={'role':raw['role'],'content':str(raw.get('content',''))[:12000]}
        if raw['role']=='user' and 'media_asset_ids' in raw:
            message['media_asset_ids']=selection(raw['media_asset_ids'])
            all_ids.update(message['media_asset_ids'])
        messages.append(message)
    if len(all_ids)>MAX_WORKSPACE_MEDIA:
        if strict:raise HTTPException(400,'This chat has too many attachments; start a new chat.')
        all_ids=set(sorted(all_ids)[:MAX_WORKSPACE_MEDIA])
    # Inspect only the required nonsecret columns. Explicit owner/brand checks
    # also protect against identity-map objects and distinguish foreign records
    # from uploads which were actually deleted.
    rows={row.id:row for row in db.execute(select(MediaAsset.id,MediaAsset.user_id,MediaAsset.brand_id,
        MediaAsset.filename,MediaAsset.mime_type).where(MediaAsset.id.in_(all_ids))
        .execution_options(all_brands=True)).all()} if all_ids else {}
    historical_ids=_message_media_ids(previous_workspace)
    if isinstance(previous_workspace,dict) and previous_workspace.get('pending_message'):
        previous_ids=previous_workspace.get('pending_media_asset_ids',[])
        if isinstance(previous_ids,list):historical_ids.update(aid for aid in previous_ids[:10] if type(aid) is int)
    brand_id=db.info.get('brand_id',0)

    def preview(aid, historical=False):
        row=rows.get(aid)
        if row and row.user_id==user_id and row.brand_id==brand_id:
            return {'id':row.id,'filename':row.filename,'url':f'/media/preview/{row.id}',
                    'kind':'video' if row.mime_type.startswith('video/') else 'image'}
        if strict and (row is not None or not historical or aid not in historical_ids):
            raise HTTPException(404,'Attachment not found')
        return {'id':aid,'filename':'Attachment unavailable','url':'','kind':'file','unavailable':True}

    assets=[preview(aid) for aid in active_ids]
    # An inaccessible active upload cannot be a publishable attachment on read.
    if not strict:assets=[asset for asset in assets if not asset.get('unavailable')]
    for message in messages:
        if 'media_asset_ids' in message:
            message['media']=[preview(aid,historical=True) for aid in message['media_asset_ids']]
    for aid in pending_ids:preview(aid,historical=True)
    return assets,messages


def hydrate_workspace_media(value, db, user_id):
    """Read-time canonical previews without rewriting saved draft state."""
    if not isinstance(value,dict):return {}
    assets,messages=_workspace_media(value,db,user_id,strict=False)
    return {**value,'media_asset_ids':[asset['id'] for asset in assets],'media':assets,
            'media_kind':('video' if any(asset['kind']=='video' for asset in assets) else 'image') if assets else None,
            'conversation':messages}


def clean_workspace(value, db, user_id, *, previous_workspace=None):
    if not isinstance(value,dict): raise HTTPException(400,'Invalid workspace')
    instagram_format=value.get('instagram_format','post')
    if instagram_format not in ('post','story'): raise HTTPException(400,'Choose Instagram Post or Story.')
    audio=value.get('instagram_audio')
    if audio is not None:
        # A saved choice is not approval: eligibility and canonical track details
        # are rechecked against Meta when the immutable review is created.
        import re
        if (not isinstance(audio,dict) or not isinstance(audio.get('audio_id'),str)
                or not re.fullmatch(r'\d{1,40}',audio['audio_id'])
                or type(audio.get('connection_id')) is not int or audio['connection_id']<=0
                or any(type(audio.get(k)) is not int or not 1<=audio[k]<=100 for k in ('audio_volume','video_volume'))):
            raise HTTPException(400,'Choose a valid Instagram music track and volume.')
        audio={k:audio[k] for k in ('audio_id','connection_id','audio_volume','video_volume')}
        audio.update(title=str(value['instagram_audio'].get('title',''))[:160],artist=str(value['instagram_audio'].get('artist',''))[:160])
    assets,messages=_workspace_media(value,db,user_id,previous_workspace=previous_workspace)
    pending=str(value.get('pending_message') or '')[:12000]
    if pending and not any(m['role']=='user' and m['content']==pending for m in messages):
        raise HTTPException(400,'Retry message must belong to this conversation.')
    link=str(value.get('link_url',''))[:2048]
    if link and not link.startswith(('https://','http://')): raise HTTPException(400,'Use an http or https source link.')
    selected=value.get('selected_platforms',[])
    if not isinstance(selected,list) or any(not isinstance(p,str) for p in selected): raise HTTPException(400,'Invalid platforms')
    explicit=value.get('platform_selection_explicit',False)
    if type(explicit) is not bool: raise HTTPException(400,'Invalid platform selection state')
    try: duration=float(value.get('video_duration') or 0)
    except (TypeError,ValueError): raise HTTPException(400,'Invalid video duration')
    if not math.isfinite(duration): raise HTTPException(400,'Invalid video duration')
    retry_context={}
    if pending:
        if 'pending_media_asset_ids' in value:
            retry_context['pending_media_asset_ids']=list(dict.fromkeys(value['pending_media_asset_ids']))
        if 'pending_link_url' in value:
            pending_link=str(value['pending_link_url'] or '')[:2048]
            if pending_link and not pending_link.startswith(('https://','http://')):raise HTTPException(400,'Use an http or https source link.')
            retry_context['pending_link_url']=pending_link
    return {'media_asset_ids':[a['id'] for a in assets],'media':assets,'media_kind':('video' if any(a['kind']=='video' for a in assets) else 'image') if assets else None,
            'instagram_format':instagram_format, 'instagram_audio':audio, 'video_duration':max(0,min(duration,36000)), 'link_url':link,'conversation':messages,
            'text_history':clean_text_history(value.get('text_history',[])), 'composer':str(value.get('composer',''))[:12000], 'selected_platforms':[p for p in selected if p in PLATFORMS][:4],
            'platform_selection_explicit':explicit, 'pending_message':pending, **retry_context,
            'active_platform':value.get('active_platform') if value.get('active_platform') in PLATFORMS else 'x'}


def save_workspace(db, row, body, user_id):
    if not row or row.user_id!=user_id: raise HTTPException(404,'Draft not found')
    if row.status not in EDITABLE: raise HTTPException(409,'This draft is already submitted. Start a new chat to create another post.')
    revision=row.revision if body.revision is None else body.revision
    platforms=list(dict.fromkeys(p for p in body.platforms if p in PLATFORMS))
    variants={}
    for p in platforms:
        value=body.variants.get(p)
        if not isinstance(value,dict) or not isinstance(value.get('posts'),list): raise HTTPException(400,'Invalid draft content')
        variants[p]={'posts':[str(v)[:5000] for v in value['posts'][:5]]}
    previous=json.loads(row.workspace_json or '{}')
    workspace=clean_workspace(body.workspace,db,user_id,previous_workspace=previous) if body.workspace is not None else previous
    claimed=db.execute(update(Draft).where(Draft.id==row.id,Draft.user_id==user_id,Draft.revision==revision,Draft.status.in_(EDITABLE)).values(
        brief=body.brief,instruction=body.instruction,platforms_json=json.dumps(platforms),variants_json=json.dumps(variants,ensure_ascii=False),
        workspace_json=json.dumps(workspace,ensure_ascii=False),thread_length=body.thread_length if body.thread_length in {1,3,5} else 1,
        revision=Draft.revision+1,updated_at=utcnow()).execution_options(synchronize_session=False))
    if claimed.rowcount!=1:
        db.rollback(); raise HTTPException(409,'This draft changed in another tab. Your local changes are still visible; open the latest saved version before retrying.')
    db.commit()
    return {'id':row.id,'saved':True,'revision':revision+1}


def draft_media_previews(db, rows, user_id):
    """One bounded lookup, rechecking ownership; never trust stored media URLs."""
    selections={}
    for row in rows:
        try:
            workspace=json.loads(row.workspace_json or '{}')
            ids=workspace.get('media_asset_ids', []) if isinstance(workspace,dict) else []
            selections[row.id]=[i for i in ids[:10] if type(i) is int] if isinstance(ids,list) else []
        except (TypeError,ValueError):
            selections[row.id]=[]
    ids={i for values in selections.values() for i in values}
    if not ids:return {}
    assets={a.id:a for a in db.scalars(select(MediaAsset).where(MediaAsset.user_id==user_id,MediaAsset.id.in_(ids))).all()}
    result={}
    for row in rows:
        for aid in selections[row.id]:
            asset=assets.get(aid)
            if not asset or asset.brand_id!=row.brand_id:continue
            if asset.mime_type.startswith('image/'):
                result[row.id]={'kind':'image','url':f'/media/preview/{asset.id}'}
                break
            if asset.mime_type.startswith('video/'):
                result.setdefault(row.id,{'kind':'video'})
    return result
