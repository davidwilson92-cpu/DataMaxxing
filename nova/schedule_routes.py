import json
from datetime import datetime, timedelta
from fastapi import APIRouter,Request,HTTPException,Response,Query
from pydantic import BaseModel
from sqlalchemy import select,update
from .db import ScheduledPost,SessionLocal,Publication,PublishReview,Draft,SocialConnection,get_preferences,utcnow
from .security import current_user
from .brands import bind_request
from . import allowances
from .publishing_workflow import schedule_time,update_draft_status,results_for

router=APIRouter()

class Reschedule(BaseModel):
    scheduled_local:str
    expected_updated_at:str|None=None


class ScheduleChange(BaseModel):
    expected_updated_at:str|None=None


class EditSchedule(BaseModel):
    revision:int


def stamp(value):
    return value.isoformat()+('Z' if value.tzinfo is None else '')


def record_object(raw):
    try:
        value=json.loads(raw or '{}')
        return value if isinstance(value,dict) else {}
    except (ValueError,TypeError):return {}


def check_version(row, expected):
    if expected is None:return  # Compatible with existing web/native clients.
    try:
        value=datetime.fromisoformat(expected.replace('Z','+00:00'))
        actual=datetime.fromisoformat(stamp(row.updated_at))
        if value!=actual:raise ValueError()
    except (ValueError,TypeError):
        raise HTTPException(409,'This schedule changed. Refresh it before making another change.')


def reviewed_publication(db,row):
    """Resolve the exact attempt; corrupt references never imply no attempt."""
    content=record_object(row.content_json)
    if not content and row.content_json not in ('{}','',None):
        raise HTTPException(409,'This schedule has incomplete records. Check its results before changing it.')
    publication_id=content.get('publication_id')
    review_code=content.get('review_code')
    if publication_id is not None or review_code is not None:
        if (type(publication_id) is not int or publication_id<=0 or not isinstance(review_code,str)
                or not review_code or len(review_code)>64):
            raise HTTPException(409,'This schedule has incomplete publication records. Check its results before changing it.')
    publication=db.get(Publication,publication_id) if publication_id else None
    if not publication:
        if content.get('publication_id'):raise HTTPException(409,'This schedule has a missing publication record. Check its results before changing it.')
        return
    if (publication.user_id!=row.user_id or publication.brand_id!=row.brand_id or publication.draft_id!=row.draft_id
            or publication.platform!=row.platform or publication.connection_id!=row.connection_id
            or publication.review_code!=content.get('review_code')):
        raise HTTPException(409,'This schedule no longer matches its reviewed post. Refresh its results.')
    return publication


def cancel_publication(db,row):
    """Cancel only the publication attempt referenced by this schedule."""
    publication=reviewed_publication(db,row)
    if not publication:return
    changed=db.execute(update(Publication).where(
        Publication.id==publication.id,Publication.review_code==publication.review_code,
        Publication.status=='scheduled',
    ).values(status='cancelled',updated_at=utcnow()).execution_options(synchronize_session=False))
    if changed.rowcount!=1:
        raise HTTPException(409,'This post has started or finished. Check its results before making changes.')
    allowances.finish(db,f'publication:{publication.id}',False)


@router.get('/api/schedules')
def schedules(request:Request, response:Response,
              window_from:str|None=Query(default=None,alias='from',max_length=40),
              window_to:str|None=Query(default=None,alias='to',max_length=40),
              draft_id:int|None=Query(default=None,gt=0)):
    uid=current_user(request).id
    start=end=None
    if window_from is not None or window_to is not None:
        try:
            if not window_from or not window_to:raise ValueError()
            start=datetime.fromisoformat(window_from.replace('Z','+00:00'))
            end=datetime.fromisoformat(window_to.replace('Z','+00:00'))
            if start.utcoffset()!=timedelta(0) or end.utcoffset()!=timedelta(0):raise ValueError()
            if not timedelta(0)<end-start<=timedelta(days=32):raise ValueError()
        except (ValueError,TypeError):
            raise HTTPException(400,'Use both from and to as UTC timestamps, with a window of up to 32 days.')
    with SessionLocal() as db:
        bind_request(db,request)
        query=select(ScheduledPost).where(ScheduledPost.user_id==uid)
        if draft_id is not None:query=query.where(ScheduledPost.draft_id==draft_id)
        if start is not None:
            query=query.where(ScheduledPost.scheduled_at>=start,ScheduledPost.scheduled_at<end)
        rows=db.scalars(query.order_by(ScheduledPost.scheduled_at.desc(),ScheduledPost.id.desc()).limit(101)).all()
        response.headers['X-Zova-Has-More']='true' if len(rows)>100 else 'false'
        # Load page context in batches; opening a full calendar must not make one
        # database round trip per post, account and approval.
        drafts={r.id:r for r in db.scalars(select(Draft).where(Draft.id.in_([r.draft_id for r in rows if r.draft_id])))}
        connections={r.id:r for r in db.scalars(select(SocialConnection).where(SocialConnection.id.in_([r.connection_id for r in rows if r.connection_id])))}
        contents={r.id:record_object(r.content_json) for r in rows}
        reviews={r.code:r for r in db.scalars(select(PublishReview).where(PublishReview.code.in_([c['review_code'] for c in contents.values() if isinstance(c.get('review_code'),str) and 0<len(c['review_code'])<=64])))}
        output=[]
        for row in rows[:100]:
            draft=drafts.get(row.draft_id)
            connection=connections.get(row.connection_id)
            content=contents[row.id]
            reviewed=reviews.get(content.get('review_code')) if isinstance(content.get('review_code'),str) else None
            options=record_object(reviewed.payload_json).get('publish_options',{}) if reviewed and reviewed.draft_id==row.draft_id else {}
            if not isinstance(options,dict):options={}
            instagram_options=options.get('instagram',{})
            if not isinstance(instagram_options,dict):instagram_options={}
            posts=content.get('posts',[])
            if not isinstance(posts,list):posts=[]
            excerpt=next((str(text) for text in posts if isinstance(text,str) and text.strip()),'')
            title=(draft.title or draft.brief or excerpt or 'Untitled post') if draft else excerpt or 'Scheduled post'
            output.append({'id':row.id,'draft_id':row.draft_id,'platform':row.platform,
                'title':' '.join(title.split())[:120],'excerpt':excerpt[:240],
                'account_name':(connection.username or connection.display_name or 'Connected account') if connection else '',
                'format':instagram_options.get('format','post') if row.platform=='instagram' else '',
                'draft_revision':draft.revision if draft else None,'scheduled_at':stamp(row.scheduled_at),
                'updated_at':stamp(row.updated_at),'status':row.status,'error':row.error})
        return output


@router.post('/api/schedules/{schedule_id}/cancel')
def cancel(schedule_id:int,request:Request,body:ScheduleChange|None=None):
    uid=current_user(request).id
    with SessionLocal() as db:
        bind_request(db,request)
        row=db.get(ScheduledPost,schedule_id)
        if not row or row.user_id!=uid:raise HTTPException(404,'Schedule not found')
        check_version(row,body.expected_updated_at if body else None)
        claimed=db.execute(update(ScheduledPost).where(ScheduledPost.id==row.id,ScheduledPost.status=='scheduled',ScheduledPost.updated_at==row.updated_at).values(status='cancelled',updated_at=utcnow()).execution_options(synchronize_session=False))
        if claimed.rowcount!=1:db.rollback();raise HTTPException(409,'This job has started or finished. It cannot be cancelled.')
        cancel_publication(db,row)
        db.commit()
        if db.scalar(select(Publication.id).where(Publication.draft_id==row.draft_id)):update_draft_status(db,row.draft_id)
        elif not db.scalar(select(ScheduledPost.id).where(ScheduledPost.draft_id==row.draft_id,ScheduledPost.status!='cancelled')):
            draft=db.get(Draft,row.draft_id)
            if draft and draft.status=='scheduled':draft.status='cancelled';db.commit()
        return {'status':'cancelled'}


@router.post('/api/schedules/{schedule_id}/reschedule')
def reschedule(schedule_id:int,body:Reschedule,request:Request):
    uid=current_user(request).id
    with SessionLocal() as db:
        bind_request(db,request)
        row=db.get(ScheduledPost,schedule_id)
        if not row or row.user_id!=uid:raise HTTPException(404,'Schedule not found')
        check_version(row,body.expected_updated_at)
        publication=reviewed_publication(db,row)
        if publication and publication.status!='scheduled':
            raise HTTPException(409,'This post has started or finished. Check its results before changing the time.')
        value=schedule_time(body.scheduled_local,get_preferences(db,uid).timezone)
        claimed=db.execute(update(ScheduledPost).where(ScheduledPost.id==row.id,ScheduledPost.status=='scheduled',ScheduledPost.updated_at==row.updated_at).values(scheduled_at=value,updated_at=utcnow()).execution_options(synchronize_session=False))
        if claimed.rowcount!=1:db.rollback();raise HTTPException(409,'This job has started or finished. Its time cannot be changed.')
        db.commit();return {'status':'scheduled','scheduled_at':value.isoformat()}


@router.post('/api/schedules/drafts/{draft_id}/edit')
def edit_scheduled_draft(draft_id:int,body:EditSchedule,request:Request):
    """Stop all unsent destinations atomically before opening content for editing."""
    uid=current_user(request).id
    with SessionLocal() as db:
        bind_request(db,request)
        draft=db.get(Draft,draft_id)
        if not draft or draft.user_id!=uid:raise HTTPException(404,'Post not found')
        locked=db.execute(update(Draft).where(Draft.id==draft_id,Draft.user_id==uid,
            Draft.revision==body.revision,Draft.status=='scheduled').values(
            status='draft',revision=Draft.revision+1,updated_at=utcnow()).execution_options(synchronize_session=False))
        if locked.rowcount!=1:raise HTTPException(409,'This post changed. Refresh its schedule before editing.')
        publications=db.scalars(select(Publication).where(Publication.draft_id==draft_id)).all()
        jobs=db.scalars(select(ScheduledPost).where(ScheduledPost.draft_id==draft_id)).all()
        if (any(p.status not in {'scheduled','cancelled','failed'} for p in publications)
                or any(j.status not in {'scheduled','cancelled','failed'} for j in jobs)):
            raise HTTPException(409,'A destination has already started or finished. Check its results; create a new post for different content.')
        pending=[job for job in jobs if job.status=='scheduled']
        if not pending:raise HTTPException(409,'No scheduled deliveries remain. Refresh this post.')
        for row in pending:
            changed=db.execute(update(ScheduledPost).where(ScheduledPost.id==row.id,
                ScheduledPost.status=='scheduled',ScheduledPost.updated_at==row.updated_at).values(
                status='cancelled',updated_at=utcnow()).execution_options(synchronize_session=False))
            if changed.rowcount!=1:raise HTTPException(409,'A scheduled delivery just started. Check its results before editing.')
            cancel_publication(db,row)
        # Submitted snapshots are retained unchanged; unused approvals cannot be reused.
        db.execute(update(PublishReview).where(PublishReview.draft_id==draft_id,
            PublishReview.status=='review').values(status='cancelled'))
        db.commit()
        return {'status':'draft','draft_id':draft_id,'revision':body.revision+1,'cancelled':len(pending)}


@router.get('/api/publications/{draft_id}')
def publication_results(draft_id:int,request:Request):
    uid=current_user(request).id
    with SessionLocal() as db:
        bind_request(db,request)
        return results_for(db,uid,draft_id,refresh=True)
