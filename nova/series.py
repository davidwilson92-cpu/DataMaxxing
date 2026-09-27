"""Finite recurring draft plans. Only the existing review path can authorise delivery."""
import json
from datetime import datetime, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from .db import ContentSeries, SeriesOccurrence, Draft, ScheduledPost, Publication, PublishReview, get_db, utcnow
from .strategy import owned, require_active_access
from .publishing_workflow import schedule_time

router=APIRouter(prefix='/api/series')


class SeriesSpec(BaseModel):
    draft_id: int
    request_key: str = Field(min_length=8,max_length=80)
    start: str
    timezone: str = Field(max_length=80)
    frequency: Literal['daily','weekly'] = 'weekly'
    weekdays: list[int] = Field(default_factory=list,max_length=7)
    count: int = Field(default=4,ge=1,le=26)
    mode: Literal['fresh','repeat'] = 'fresh'


def times(body):
    try:
        zone=ZoneInfo(body.timezone)
        start=datetime.fromisoformat(body.start)
        if start.tzinfo is not None or any(type(d)!=int or d<0 or d>6 for d in body.weekdays):raise ValueError()
    except (ValueError,TypeError,ZoneInfoNotFoundError):raise HTTPException(400,'Choose a valid local start time, weekdays and IANA timezone.')
    days=set(body.weekdays or [start.weekday()])
    result=[]
    for offset in range(366):
        local=start+timedelta(days=offset)
        if body.frequency=='weekly' and local.weekday() not in days:continue
        value=schedule_time(local.isoformat(),body.timezone)
        result.append({'utc':value.isoformat(),'local':value.astimezone(zone).isoformat()})
        if len(result)==body.count:return result
    raise HTTPException(400,'Choose a shorter series.')


@router.post('/preview')
def preview(body:SeriesSpec,request:Request,db=Depends(get_db)):
    from .security import current_user
    owned(db,Draft,current_user(request).id,body.draft_id)
    return {'times':times(body),'timezone':body.timezone,'note':'These are planned draft dates, not publishing approval. Each occurrence needs final review.'}


@router.post('')
def create(body:SeriesSpec,request:Request,db=Depends(get_db)):
    from .security import current_user
    uid=current_user(request).id
    existing=db.scalar(select(ContentSeries).where(ContentSeries.user_id==uid,ContentSeries.request_key==body.request_key))
    if existing:
        if {k:v for k,v in json.loads(existing.spec_json).items() if k!='source'}!=body.model_dump():raise HTTPException(409,'This request was already used with different settings.')
        return {'id':existing.id}
    source=owned(db,Draft,uid,body.draft_id)
    if not source.brief.strip():raise HTTPException(400,'Add a brief to your draft first.')
    dates=times(body)
    spec=body.model_dump()
    spec['source']={k:getattr(source,k) for k in ['brief','instruction','platforms_json','workspace_json','variants_json','thread_length']}
    row=ContentSeries(user_id=uid,spec_json=json.dumps(spec))
    row.request_key=body.request_key
    db.add(row);db.flush()
    for i,item in enumerate(dates):
        db.add(SeriesOccurrence(user_id=uid,series_id=row.id,position=i,due_at=datetime.fromisoformat(item['utc'])))
    try:db.commit()
    except IntegrityError:
        db.rollback()
        existing=db.scalar(select(ContentSeries).where(ContentSeries.user_id==uid,ContentSeries.request_key==body.request_key))
        if not existing:raise
        return {'id':existing.id}
    return {'id':row.id}


@router.get('')
def listing(request:Request,db=Depends(get_db)):
    from .security import current_user
    uid=current_user(request).id
    result=[]
    for row in db.scalars(select(ContentSeries).where(ContentSeries.user_id==uid).order_by(ContentSeries.id.desc()).limit(30)):
        spec=json.loads(row.spec_json)
        items=[]
        for o in db.scalars(select(SeriesOccurrence).where(SeriesOccurrence.series_id==row.id).order_by(SeriesOccurrence.position)):
            d=db.get(Draft,o.draft_id) if o.draft_id else None
            items.append({'id':o.id,'position':o.position,'due_at':o.due_at.replace(tzinfo=timezone.utc).isoformat(),'draft_id':o.draft_id,'status':o.status if o.status=='cancelled' else d.status if d else o.status})
        result.append({'id':row.id,'status':row.status,'revision':row.revision,'spec':spec,'occurrences':items})
    return result


@router.post('/occurrences/{occurrence_id}/draft', dependencies=[Depends(require_active_access)])
def open_occurrence(occurrence_id:int,request:Request,db=Depends(get_db)):
    from .security import current_user
    uid=current_user(request).id
    o=owned(db,SeriesOccurrence,uid,occurrence_id)
    series=owned(db,ContentSeries,uid,o.series_id)
    if series.status!='active' or o.status=='cancelled':raise HTTPException(409,'This series or occurrence is paused or cancelled.')
    if o.draft_id:return {'draft_id':owned(db,Draft,uid,o.draft_id).id}
    spec=json.loads(series.spec_json)
    generated=None
    if spec['mode']=='fresh':
        from . import ai, allowances
        from .db import get_preferences
        from .strategy import strategy_context
        try:
            with allowances.ai_action(db,uid):
                generated=ai.generate_variants(brief=spec['source']['brief'],instruction=spec['source']['instruction']+strategy_context(db,uid)+'\nCreate a fresh variation for this recurring draft. Do not invent new events or results. '+('Story planning notes only; not a caption or overlay.' if json.loads(spec['source']['workspace_json'] or '{}').get('instagram_format')=='story' else ''),platforms=json.loads(spec['source']['platforms_json']),thread_length=spec['source']['thread_length'],preferences=get_preferences(db,uid))
        except HTTPException:raise
        except Exception:raise HTTPException(502,'This occurrence could not be drafted. Retry; its plan is still saved.')
    claim=db.execute(update(ContentSeries).where(ContentSeries.id==series.id,ContentSeries.status=='active',ContentSeries.revision==series.revision).values(revision=ContentSeries.revision))
    if claim.rowcount!=1:db.rollback();raise HTTPException(409,'Series is paused or cancelled.')
    from types import SimpleNamespace
    spec=json.loads(series.spec_json);source=SimpleNamespace(**spec['source'])
    workspace=json.loads(source.workspace_json or '{}')
    workspace.update(conversation=[{'role':'assistant','content':'Recurring '+spec['mode']+' draft. Planned for '+o.due_at.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(spec['timezone'])).isoformat()+'. Not scheduled: review each occurrence before publishing.'}],composer='',text_history=[])
    d=Draft(user_id=uid,brief=source.brief,instruction=source.instruction,platforms_json=source.platforms_json,thread_length=source.thread_length,workspace_json=json.dumps(workspace),variants_json=source.variants_json if spec['mode']=='repeat' else json.dumps(generated))
    db.add(d);db.flush()
    claim=db.execute(update(SeriesOccurrence).where(SeriesOccurrence.id==o.id,SeriesOccurrence.draft_id.is_(None),SeriesOccurrence.status=='planned').values(draft_id=d.id))
    if claim.rowcount!=1:
        db.rollback();db.expire_all();o=owned(db,SeriesOccurrence,uid,occurrence_id)
        if o.draft_id:return {'draft_id':o.draft_id}
        raise HTTPException(409,'Occurrence changed. Refresh the series.')
    db.commit();return {'draft_id':d.id}


class SeriesChange(BaseModel):
    action: Literal['pause','resume','cancel']
    revision: int


def revoke_jobs(db, uid, ids):
    if not ids:return
    # Claim all scheduled jobs in this transaction before invalidating their approvals.
    for job in db.scalars(select(ScheduledPost).where(ScheduledPost.draft_id.in_(ids),ScheduledPost.user_id==uid, ScheduledPost.status.in_(['scheduled','publishing','unknown','pending']))):
        claim=db.execute(update(ScheduledPost).where(ScheduledPost.id==job.id,ScheduledPost.status=='scheduled').values(status='cancelled',updated_at=utcnow()).execution_options(synchronize_session=False))
        if claim.rowcount!=1:db.rollback();raise HTTPException(409,'An occurrence is sending or unresolved. Check its results before changing this series.')
        from . import allowances
        for publication in db.scalars(select(Publication).where(Publication.draft_id==job.draft_id,Publication.platform==job.platform,Publication.status=='scheduled')):
            allowances.finish(db,f'publication:{publication.id}',False)
        db.execute(update(Publication).where(Publication.draft_id==job.draft_id,Publication.platform==job.platform,Publication.status=='scheduled').values(status='cancelled'))
        db.execute(update(Draft).where(Draft.id==job.draft_id,Draft.status=='scheduled').values(status='cancelled'))
    db.execute(update(PublishReview).where(PublishReview.draft_id.in_(ids),PublishReview.status=='review').values(status='invalidated'))


@router.post('/{series_id}/state')
def change_state(series_id:int,body:SeriesChange,request:Request,db=Depends(get_db)):
    from .security import current_user
    uid=current_user(request).id;row=owned(db,ContentSeries,uid,series_id)
    target={'pause':'paused','resume':'active','cancel':'cancelled'}[body.action]
    claim=db.execute(update(ContentSeries).where(ContentSeries.id==row.id,ContentSeries.revision==body.revision,ContentSeries.status!='cancelled').values(status=target,revision=body.revision+1))
    if claim.rowcount!=1:db.rollback();raise HTTPException(409,'Series changed or was cancelled. Refresh before editing.')
    items=db.scalars(select(SeriesOccurrence).where(SeriesOccurrence.series_id==row.id)).all()
    if body.action!='resume':revoke_jobs(db,uid,[o.draft_id for o in items if o.draft_id])
    if body.action=='cancel':
        for o in items:
            d=db.get(Draft,o.draft_id) if o.draft_id else None
            if not d or d.status not in {'published','partial','pending','publishing','needs_review'}:o.status='cancelled'
    db.commit();return {'status':target,'note':'Previously scheduled occurrences need a new final review before sending.'}


class OccurrenceEdit(BaseModel):
    local_time: str
    scope: Literal['one','future'] = 'one'
    revision: int


class CancelOccurrence(BaseModel):
    revision: int


@router.post('/occurrences/{occurrence_id}/cancel')
def cancel_occurrence(occurrence_id:int,body:CancelOccurrence,request:Request,db=Depends(get_db)):
    from .security import current_user
    uid=current_user(request).id;o=owned(db,SeriesOccurrence,uid,occurrence_id)
    claim=db.execute(update(ContentSeries).where(ContentSeries.id==o.series_id,ContentSeries.revision==body.revision,ContentSeries.status!='cancelled').values(revision=body.revision+1))
    if claim.rowcount!=1:db.rollback();raise HTTPException(409,'Series changed. Refresh before cancelling.')
    if o.draft_id:
        draft=owned(db,Draft,uid,o.draft_id)
        if draft.status in {'published','partial','pending','publishing','needs_review'}:db.rollback();raise HTTPException(409,'This occurrence is already submitted. Check its results.')
        revoke_jobs(db,uid,[o.draft_id])
    o.status='cancelled';db.commit();return {'status':'cancelled'}


@router.post('/occurrences/{occurrence_id}/time')
def edit_time(occurrence_id:int,body:OccurrenceEdit,request:Request,db=Depends(get_db)):
    from .security import current_user
    uid=current_user(request).id;o=owned(db,SeriesOccurrence,uid,occurrence_id);s=owned(db,ContentSeries,uid,o.series_id)
    spec=json.loads(s.spec_json)
    due=schedule_time(body.local_time,spec['timezone'])
    claim=db.execute(update(ContentSeries).where(ContentSeries.id==s.id,ContentSeries.revision==body.revision,ContentSeries.status!='cancelled').values(revision=body.revision+1))
    if claim.rowcount!=1:db.rollback();raise HTTPException(409,'Series changed. Refresh before editing.')
    items=db.scalars(select(SeriesOccurrence).where(SeriesOccurrence.series_id==s.id,SeriesOccurrence.position>=o.position if body.scope=='future' else SeriesOccurrence.id==o.id)).all()
    revoke_jobs(db,uid,[v.draft_id for v in items if v.draft_id])
    zone=ZoneInfo(spec['timezone'])
    delta=due.astimezone(zone).replace(tzinfo=None)-o.due_at.replace(tzinfo=timezone.utc).astimezone(zone).replace(tzinfo=None)
    for item in items:
        if item.status=='cancelled':continue
        draft=db.get(Draft,item.draft_id) if item.draft_id else None
        if draft and draft.status in {'published','partial','pending','publishing','needs_review'}:db.rollback();raise HTTPException(409,'Submitted occurrences cannot be moved. Choose a later occurrence.')
        local=item.due_at.replace(tzinfo=timezone.utc).astimezone(zone).replace(tzinfo=None)+delta
        item.due_at=schedule_time(local.isoformat(),spec['timezone'])
    db.commit();return {'status':'updated','note':'Review changed occurrences before scheduling.'}


def approval_guard(db, draft_id):
    occurrence=db.scalar(select(SeriesOccurrence).where(SeriesOccurrence.draft_id==draft_id))
    if occurrence:
        series=db.get(ContentSeries,occurrence.series_id)
        lock=db.execute(update(ContentSeries).where(ContentSeries.id==series.id,ContentSeries.status=='active').values(revision=ContentSeries.revision))
        if lock.rowcount!=1 or series.status!='active' or occurrence.status=='cancelled':raise HTTPException(409,'Resume the series before reviewing this occurrence.')


def planned_context(db, draft_id):
    o=db.scalar(select(SeriesOccurrence).where(SeriesOccurrence.draft_id==draft_id))
    if not o:return None
    s=db.get(ContentSeries,o.series_id);spec=json.loads(s.spec_json)
    return {'series_id':s.id,'timezone':spec['timezone'],'local_time':o.due_at.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(spec['timezone'])).replace(tzinfo=None).isoformat(timespec='minutes'),'status':s.status}


class RepeatReview(BaseModel):
    revision: int
    connection_ids: dict[str,int] = Field(default_factory=dict)
    publish_options: dict = Field(default_factory=dict)


@router.post('/{series_id}/review', dependencies=[Depends(require_active_access)])
def review_repeat(series_id:int,body:RepeatReview,request:Request,db=Depends(get_db)):
    import secrets
    from types import SimpleNamespace
    from .security import current_user
    from .db import SeriesApproval
    from .publishing_workflow import prepare_review
    uid=current_user(request).id;s=owned(db,ContentSeries,uid,series_id)
    spec=json.loads(s.spec_json)
    if spec['mode']!='repeat' or s.status!='active' or s.revision!=body.revision:raise HTTPException(409,'Only an active, unchanged repeat series can be reviewed together. Fresh drafts need individual review.')
    snapshots=[]
    for o in db.scalars(select(SeriesOccurrence).where(SeriesOccurrence.series_id==s.id,SeriesOccurrence.status!='cancelled').order_by(SeriesOccurrence.position)).all():
        result=open_occurrence(o.id,request,db)
        draft=owned(db,Draft,uid,result['draft_id'])
        if draft.status not in {'draft','failed','cancelled'}:continue
        ws=json.loads(draft.workspace_json or '{}');variants=json.loads(draft.variants_json or '{}')
        options=dict(body.publish_options)
        if 'instagram' in variants:options['instagram']={**options.get('instagram',{}),'format':ws.get('instagram_format','post')}
        args=SimpleNamespace(draft_id=draft.id,platforms=list(variants),variants=variants,media_asset_ids=ws.get('media_asset_ids',[]),link_url=ws.get('link_url',''),publish_options=options,connection_ids=body.connection_ids,scheduled_local=o.due_at.replace(tzinfo=timezone.utc).isoformat())
        review=prepare_review(db,uid,args);snapshots.append(review)
    if not snapshots:raise HTTPException(409,'No unscheduled occurrences to review.')
    row=SeriesApproval(user_id=uid,series_id=s.id,revision=body.revision,token=secrets.token_urlsafe(32),payload_json=json.dumps(snapshots),expires_at=utcnow()+timedelta(minutes=15))
    db.add(row);db.commit()
    return {'token':row.token,'occurrences':snapshots,'note':'Confirm only the exact content, accounts and dates listed. No future generated content is included.'}


class RepeatConfirm(BaseModel):
    token: str = Field(min_length=20,max_length=80)


@router.post('/{series_id}/confirm', dependencies=[Depends(require_active_access)])
def confirm_repeat(series_id:int,body:RepeatConfirm,request:Request,db=Depends(get_db)):
    from types import SimpleNamespace
    from .security import current_user
    from .db import SeriesApproval
    from .publishing_workflow import confirm_review
    uid=current_user(request).id;s=owned(db,ContentSeries,uid,series_id)
    approval=db.scalar(select(SeriesApproval).where(SeriesApproval.series_id==s.id,SeriesApproval.token==body.token,SeriesApproval.user_id==uid))
    if not approval or approval.expires_at.replace(tzinfo=timezone.utc)<=utcnow():raise HTTPException(409,'Review expired. Review the repeat schedule again.')
    results=[]
    for item in json.loads(approval.payload_json):
        lock=db.execute(update(ContentSeries).where(ContentSeries.id==s.id,ContentSeries.status=='active',ContentSeries.revision==approval.revision).values(revision=ContentSeries.revision))
        if lock.rowcount!=1:db.rollback();raise HTTPException(409,'Series changed. Check existing results before reviewing remaining occurrences.')
        snapshot=item['snapshot']
        try:
            result=confirm_review(db,uid,SimpleNamespace(**{k:snapshot[k] for k in ['draft_id','platforms','variants','media_asset_ids','link_url','publish_options']},review_token=item['review_token']),'schedule')
            results.append({'draft_id':snapshot['draft_id'],'status':result['draft_status']})
        except HTTPException as e:
            db.rollback();results.append({'draft_id':snapshot['draft_id'],'status':'not_scheduled','error':str(e.detail)})
    return {'results':results,'note':'Check each result. Only successfully confirmed occurrences are scheduled.'}
