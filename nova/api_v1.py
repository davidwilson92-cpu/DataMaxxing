"""Versioned native API using the same handlers and approvals as the web app.

Explicit allowlist prevents future browser/admin endpoints becoming mobile APIs
accidentally. Existing web routes remain unchanged.
"""
import re
import os
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.routing import APIRoute
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .db import ClientMutation, Draft, MediaAsset, get_db
from .mobile_auth import enabled, native_user, router as auth_router
from .work_summary import draft_title

router=APIRouter(prefix='/api/v1')
SHARED_PATHS={
    '/api/drafts/{draft_id}', '/api/conversation/plan', '/api/ai/generate',
    '/api/ai/rewrite', '/api/ai/schedule', '/api/media', '/api/preview',
    '/api/publish-context', '/api/publish-review', '/api/publish', '/api/schedule',
    '/api/publications/{draft_id}', '/api/schedules',
    '/api/schedules/{schedule_id}/cancel', '/api/schedules/{schedule_id}/reschedule',
    '/api/strategy', '/api/strategy/propose', '/api/strategy/confirm',
    '/api/strategy/actions', '/api/strategy/recommend',
    '/api/strategy/actions/{action_id}/feedback', '/api/strategy/actions/{action_id}/draft',
    '/api/analytics/dashboard', '/api/insights', '/api/recent-posts',
}


async def client_contract(request: Request):
    # Mandatory for every shared route, including handlers that add auth later.
    from starlette.concurrency import run_in_threadpool
    await run_in_threadpool(native_user,request)
    if request.method=='PATCH' and re.fullmatch(r'/api/v1/drafts/\d+',request.url.path):
        body=await request.json()
        if not isinstance(body,dict) or type(body.get('revision')) is not int or body['revision']<0:
            raise HTTPException(428,'Include the saved draft revision before editing')
    if request.url.path=='/api/v1/ai/generate':
        body=await request.json()
        if not isinstance(body,dict) or type(body.get('draft_id')) is not int or type(body.get('revision')) is not int:
            raise HTTPException(428,'Save a draft and include its revision first')


@router.get('/config')
def config():
    return {'api_version':'1','mobile_enabled':enabled(),'publishing_requires_review':True,
            'capabilities':{'drafts':True,'strategy':True,'media':True,'reviewed_publishing':True,
                            'background_ai_jobs':os.environ.get('ZOVA_AI_JOBS_ENABLED','false')=='true','native_billing':False,'push_notifications':False}}


@router.get('/media/{asset_id}')
def media(asset_id:int,request:Request,db=Depends(get_db)):
    from pathlib import Path
    from fastapi.responses import FileResponse, RedirectResponse
    from .storage import UPLOAD_DIR,get_public_url
    user=native_user(request);row=db.get(MediaAsset,asset_id)
    if not row or row.user_id!=user.id: raise HTTPException(404,'Media not found')
    if row.storage_key.startswith('nova/'):
        # Ignore permanent public URLs; obtain a short-lived object-store link.
        try: return RedirectResponse(get_public_url(row.storage_key,None,expires=300),307)
        except RuntimeError: raise HTTPException(404,'Media unavailable') from None
    path=Path(row.storage_key).resolve()
    if not path.is_relative_to(UPLOAD_DIR.resolve()) or not path.is_file(): raise HTTPException(404,'Media unavailable')
    return FileResponse(path,media_type=row.mime_type,headers={'Content-Security-Policy':"sandbox; default-src 'none'"})


@router.get('/me')
def me(request: Request):
    from .brands import context
    user=native_user(request)
    return {'id':user.id,'name':user.display_name,'email':user.email,'workspaces':context(user)['choices']}


@router.get('/drafts')
def drafts(request: Request, before_id: int | None=Query(None,gt=0), limit:int=Query(20,ge=1,le=50), q:str=Query('',max_length=200), db=Depends(get_db)):
    user=native_user(request)
    statement=select(Draft).where(Draft.user_id==user.id)
    if before_id is not None: statement=statement.where(Draft.id<before_id)
    if q.strip(): statement=statement.where(Draft.title.icontains(q.strip(),autoescape=True)|Draft.brief.icontains(q.strip(),autoescape=True))
    rows=db.scalars(statement.order_by(Draft.id.desc()).limit(limit+1)).all()
    page=rows[:limit]
    return {'items':[{'id':r.id,'title':draft_title(r),'status':r.status,'revision':r.revision,'updated_at':r.updated_at.isoformat()} for r in page],
            'next_before_id':page[-1].id if len(rows)>limit else None}


@router.post('/drafts')
def create_draft(request:Request,idempotency_key:str=Header(...,min_length=16,max_length=80),db=Depends(get_db)):
    from .app import subscription_guard
    user=native_user(request);subscription_guard(user)
    if not re.fullmatch(r'[A-Za-z0-9_-]{16,80}',idempotency_key):
        raise HTTPException(400,'Use a unique request identifier')
    brand_id=db.info.get('brand_id',0)
    def existing():
        return db.scalar(select(ClientMutation).where(ClientMutation.user_id==user.id,ClientMutation.brand_id==brand_id,ClientMutation.request_key==idempotency_key))
    mutation=existing()
    if mutation:
        row=db.get(Draft,mutation.draft_id)
        if not row: raise HTTPException(409,'Original draft was deleted; start a new request')
        return {'id':row.id,'revision':row.revision}
    row=Draft(user_id=user.id);db.add(row);db.flush()
    db.add(ClientMutation(user_id=user.id,brand_id=brand_id,request_key=idempotency_key,draft_id=row.id))
    try: db.commit()
    except IntegrityError:
        db.rollback();mutation=existing()
        if not mutation: raise
        row=db.get(Draft,mutation.draft_id)
        if not row: raise HTTPException(409,'Original draft was deleted; start a new request')
    return {'id':row.id,'revision':row.revision}


def install(app):
    # Reuse endpoint functions, dependencies and request schemas. No HTTP proxy or
    # parallel publishing implementation; fixes serve both clients in one place.
    from .strategy import router as strategy_router
    from .schedule_routes import router as schedule_router
    registered=set()
    for route in [*app.routes,*strategy_router.routes,*schedule_router.routes]:
        if isinstance(route,APIRoute) and route.path in SHARED_PATHS:
            key=(route.path,tuple(sorted(route.methods)))
            if key in registered: continue
            registered.add(key)
            app.add_api_route('/api/v1/'+route.path[len('/api/'):],route.endpoint,
                methods=sorted(route.methods),response_model=route.response_model,
                status_code=route.status_code,dependencies=[Depends(client_contract),*route.dependencies],
                name='v1_'+route.name,tags=['Mobile v1'])
    if {key[0] for key in registered} != SHARED_PATHS:
        raise RuntimeError('The native contract references an unavailable shared route')
    app.include_router(auth_router)
    app.include_router(router)
    from .generation_jobs import router as jobs_router
    app.include_router(jobs_router)
