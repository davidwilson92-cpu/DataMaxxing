"""Durable, bounded AI queue. Interrupted jobs are never silently regenerated."""
import hashlib
import json
import re
import secrets
import os
from datetime import timedelta
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from .client_schemas import GenerateRequest
from .db import Brand, Draft, GenerationJob, SessionLocal, User, get_db, utcnow
from .mobile_auth import native_user

def require_queue():
    if os.environ.get('ZOVA_AI_JOBS_ENABLED','false')!='true':
        raise HTTPException(404,'Background drafting is not enabled')


router=APIRouter(prefix='/api/v1/generation-jobs',dependencies=[Depends(require_queue)])


def view(row):
    return {'id':row.id,'status':row.status,'result':json.loads(row.result_json),
            'created_at':row.created_at.isoformat(),'updated_at':row.updated_at.isoformat()}


@router.post('',status_code=202)
def submit(body:GenerateRequest,request:Request,idempotency_key:str=Header(...,min_length=16,max_length=80),db=Depends(get_db)):
    from .app import subscription_guard,_user_assets
    from .workspace import EDITABLE
    user=native_user(request);subscription_guard(user)
    if not re.fullmatch(r'[A-Za-z0-9_-]{16,80}',idempotency_key): raise HTTPException(400,'Use a unique request identifier')
    if body.draft_id is None or body.revision is None: raise HTTPException(428,'Save a draft and include its revision first')
    payload=json.dumps(body.model_dump(),sort_keys=True,separators=(',',':'))
    digest=hashlib.sha256(payload.encode()).hexdigest()
    def existing():
        return db.scalar(select(GenerationJob).where(GenerationJob.user_id==user.id,GenerationJob.request_key==idempotency_key))
    previous=existing()
    if previous:
        if previous.payload_hash!=digest: raise HTTPException(409,'Request identifier already used for different content')
        return view(previous)
    draft=db.get(Draft,body.draft_id)
    if not draft or draft.user_id!=user.id: raise HTTPException(404,'Draft not found')
    if draft.status not in EDITABLE or draft.revision!=body.revision: raise HTTPException(409,'Open the latest editable draft before generating')
    _user_assets(db,user.id,body.media_asset_ids)
    # Serialize per-account queue admission on PostgreSQL, including all brands.
    db.scalar(select(User).where(User.id==user.id).with_for_update())
    active=db.scalar(select(func.count()).select_from(GenerationJob).where(GenerationJob.user_id==user.id,GenerationJob.status.in_(['queued','running'])).execution_options(all_brands=True))
    if active>=3: raise HTTPException(429,'Wait for your current drafts to finish')
    row=GenerationJob(id=secrets.token_urlsafe(24),user_id=user.id,request_key=idempotency_key,payload_hash=digest,payload_json=payload,auth_version=user.auth_version)
    db.add(row)
    try: db.commit()
    except IntegrityError:
        db.rollback();row=existing()
        if not row: raise
        if row.payload_hash!=digest: raise HTTPException(409,'Request identifier already used for different content')
    return view(row)


@router.get('/{job_id}')
def get(job_id:str,request:Request,db=Depends(get_db)):
    user=native_user(request);row=db.get(GenerationJob,job_id)
    if not row or row.user_id!=user.id: raise HTTPException(404,'Draft request not found')
    return view(row)


@router.post('/{job_id}/cancel')
def cancel(job_id:str,request:Request,db=Depends(get_db)):
    user=native_user(request)
    row=db.get(GenerationJob,job_id)
    if not row or row.user_id!=user.id: raise HTTPException(404,'Draft request not found')
    if row.status=='cancelled': return view(row)
    changed=db.execute(update(GenerationJob).where(GenerationJob.id==job_id,GenerationJob.user_id==user.id,GenerationJob.status=='queued').values(status='cancelled',updated_at=utcnow()))
    if changed.rowcount!=1: raise HTTPException(409,'This request has already started. Check its result.')
    db.commit();db.refresh(row);return view(row)


def process_jobs(limit=2):
    from .app import generate_draft
    completed=0
    with SessionLocal() as db:
        # An interrupted generation may already have saved its draft. Never
        # repeat the provider call: direct the client to the canonical draft.
        db.execute(update(GenerationJob).where(GenerationJob.status=='running',GenerationJob.updated_at<utcnow()-timedelta(minutes=15)).values(
            status='interrupted',result_json=json.dumps({'detail':'Generation was interrupted. Reload your saved draft before trying again.'}),updated_at=utcnow()))
        db.commit()
        ids=db.scalars(select(GenerationJob.id).where(GenerationJob.status=='queued').order_by(GenerationJob.created_at,GenerationJob.id).limit(limit)).all()
    for job_id in ids:
        with SessionLocal() as db:
            claim=db.execute(update(GenerationJob).where(GenerationJob.id==job_id,GenerationJob.status=='queued').values(status='running',updated_at=utcnow()))
            db.commit()
            if claim.rowcount!=1: continue
            row=db.get(GenerationJob,job_id)
            try:
                user=db.get(User,row.user_id)
                brand=db.get(Brand,row.brand_id) if row.brand_id else None
                if not user or not user.active or user.auth_version!=row.auth_version or (row.brand_id and (not brand or brand.user_id!=user.id)):
                    raise HTTPException(401,'Account or workspace access changed. Sign in again.')
                db.info.update(brand_id=row.brand_id,brand_user_id=row.user_id)
                result=generate_draft(GenerateRequest.model_validate_json(row.payload_json),user,db)
                status='succeeded'
            except HTTPException as exc:
                db.rollback();result={'detail':str(exc.detail),'status_code':exc.status_code};status='failed'
            except Exception:
                db.rollback();result={'detail':'Generation could not be confirmed. Reload the saved draft before retrying.'};status='interrupted'
            row=db.get(GenerationJob,job_id)
            row.status=status;row.result_json=json.dumps(result);row.updated_at=utcnow();db.commit()
            completed+=1
    return completed
