import json
from fastapi import APIRouter,Request,HTTPException
from pydantic import BaseModel
from sqlalchemy import select,update
from .db import ScheduledPost,SessionLocal,Publication,Draft,get_preferences,utcnow
from .security import current_user
from .publishing_workflow import schedule_time,update_draft_status,results_for

router=APIRouter()

class Reschedule(BaseModel):
    scheduled_local:str


@router.get('/api/schedules')
def schedules(request:Request):
    uid=current_user(request).id
    with SessionLocal() as db:
        return [{'id':r.id,'draft_id':r.draft_id,'platform':r.platform,'scheduled_at':r.scheduled_at.isoformat()+('Z' if r.scheduled_at.tzinfo is None else ''),'status':r.status,'error':r.error} for r in db.scalars(select(ScheduledPost).where(ScheduledPost.user_id==uid).order_by(ScheduledPost.scheduled_at.desc()).limit(100))]


@router.post('/api/schedules/{schedule_id}/cancel')
def cancel(schedule_id:int,request:Request):
    uid=current_user(request).id
    with SessionLocal() as db:
        row=db.get(ScheduledPost,schedule_id)
        if not row or row.user_id!=uid:raise HTTPException(404,'Schedule not found')
        claimed=db.execute(update(ScheduledPost).where(ScheduledPost.id==row.id,ScheduledPost.status=='scheduled').values(status='cancelled',updated_at=utcnow()).execution_options(synchronize_session=False))
        if claimed.rowcount!=1:db.rollback();raise HTTPException(409,'This job has started or finished. It cannot be cancelled.')
        db.execute(update(Publication).where(Publication.draft_id==row.draft_id,Publication.platform==row.platform,Publication.status=='scheduled').values(status='cancelled'))
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
        row=db.get(ScheduledPost,schedule_id)
        if not row or row.user_id!=uid:raise HTTPException(404,'Schedule not found')
        value=schedule_time(body.scheduled_local,get_preferences(db,uid).timezone)
        claimed=db.execute(update(ScheduledPost).where(ScheduledPost.id==row.id,ScheduledPost.status=='scheduled').values(scheduled_at=value,updated_at=utcnow()).execution_options(synchronize_session=False))
        if claimed.rowcount!=1:db.rollback();raise HTTPException(409,'This job has started or finished. Its time cannot be changed.')
        db.commit();return {'status':'scheduled','scheduled_at':value.isoformat()}


@router.get('/api/publications/{draft_id}')
def publication_results(draft_id:int,request:Request):
    uid=current_user(request).id
    with SessionLocal() as db:return results_for(db,uid,draft_id)
