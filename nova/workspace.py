"""Versioned workspace persistence; browser metadata is never authoritative for assets."""
import json
import math
from fastapi import HTTPException
from sqlalchemy import update, select, delete
from .db import Draft, MediaAsset, utcnow

EDITABLE={'draft','failed','partial','cancelled'}
PLATFORMS={'x','instagram','facebook','tiktok'}


def delete_unsubmitted_draft(db,row):
    from .db import Publication,PublishReview,ScheduledPost,Activity
    if row.status not in EDITABLE or any(db.scalar(select(model.id).where(model.draft_id==row.id).limit(1)) for model in (Publication,ScheduledPost,Activity)):
        raise HTTPException(409,'This draft has delivery records and is retained in your history.')
    db.execute(delete(PublishReview).where(PublishReview.draft_id==row.id))
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


def clean_workspace(value, db, user_id):
    if not isinstance(value,dict): raise HTTPException(400,'Invalid workspace')
    instagram_format=value.get('instagram_format','post')
    if instagram_format not in ('post','story'): raise HTTPException(400,'Choose Instagram Post or Story.')
    ids=value.get('media_asset_ids',[])
    if not isinstance(ids,list) or len(ids)>10 or any(type(i)!=int for i in ids):
        raise HTTPException(400,'Invalid attachment selection')
    assets=[]
    for aid in dict.fromkeys(ids):
        row=db.get(MediaAsset,aid)
        if not row or row.user_id!=user_id: raise HTTPException(404,'Attachment not found')
        assets.append({'id':row.id,'filename':row.filename,'url':row.public_url or f'/media/preview/{row.id}','kind':'video' if row.mime_type.startswith('video/') else 'image'})
    messages=value.get('conversation',[])
    if not isinstance(messages,list) or len(messages)>200: raise HTTPException(400,'Conversation is too long; start a new chat.')
    messages=[{'role':m['role'],'content':str(m.get('content',''))[:12000]} for m in messages if isinstance(m,dict) and m.get('role') in {'assistant','user'}]
    link=str(value.get('link_url',''))[:2048]
    if link and not link.startswith(('https://','http://')): raise HTTPException(400,'Use an http or https source link.')
    selected=value.get('selected_platforms',[])
    if not isinstance(selected,list) or any(not isinstance(p,str) for p in selected): raise HTTPException(400,'Invalid platforms')
    try: duration=float(value.get('video_duration') or 0)
    except (TypeError,ValueError): raise HTTPException(400,'Invalid video duration')
    if not math.isfinite(duration): raise HTTPException(400,'Invalid video duration')
    return {'media_asset_ids':[a['id'] for a in assets],'media':assets,'media_kind':('video' if any(a['kind']=='video' for a in assets) else 'image') if assets else None,
            'instagram_format':instagram_format, 'video_duration':max(0,min(duration,36000)), 'link_url':link,'conversation':messages,
            'text_history':clean_text_history(value.get('text_history',[])), 'composer':str(value.get('composer',''))[:12000], 'selected_platforms':[p for p in selected if p in PLATFORMS][:4],
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
    workspace=clean_workspace(body.workspace,db,user_id) if body.workspace is not None else json.loads(row.workspace_json or '{}')
    claimed=db.execute(update(Draft).where(Draft.id==row.id,Draft.user_id==user_id,Draft.revision==revision,Draft.status.in_(EDITABLE)).values(
        brief=body.brief,instruction=body.instruction,platforms_json=json.dumps(platforms),variants_json=json.dumps(variants,ensure_ascii=False),
        workspace_json=json.dumps(workspace,ensure_ascii=False),thread_length=body.thread_length if body.thread_length in {1,3,5} else 1,
        revision=Draft.revision+1,updated_at=utcnow()).execution_options(synchronize_session=False))
    if claimed.rowcount!=1:
        db.rollback(); raise HTTPException(409,'This draft changed in another tab. Your local changes are still visible; open the latest saved version before retrying.')
    db.commit()
    return {'id':row.id,'saved':True,'revision':revision+1}
