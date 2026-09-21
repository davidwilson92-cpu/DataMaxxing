"""An OAuth grant is staged until its owner confirms the exact destination."""
import json
import secrets
from datetime import timedelta,timezone
from fastapi import APIRouter,Depends,Form,HTTPException,Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select,update,delete
from .db import PendingConnection,SocialConnection,get_db,utcnow
from .security import encrypt,decrypt,hash_api_key

router=APIRouter()


def stage(db,request,state,platform,candidates):
    from .app import current_user
    user=current_user(request)
    # Expired grants are inaccessible; scrub them opportunistically on new flows.
    db.execute(delete(PendingConnection).where(PendingConnection.expires_at<utcnow()))
    raw=secrets.token_urlsafe(32)
    payload={'candidates':candidates,'onboarding':request.cookies.get('zova_onboarding')==str(user.id)}
    db.add(PendingConnection(code_hash=hash_api_key(raw),user_id=user.id,brand_id=state.brand_id,auth_version=user.auth_version,platform=platform,encrypted_payload=encrypt(json.dumps(payload)),expires_at=utcnow()+timedelta(minutes=10)))
    db.commit()
    return RedirectResponse(f'/connections/review/{raw}?workspace={state.brand_id}',303)


def owned(db,request,code):
    from .app import current_user
    user=current_user(request)
    row=db.get(PendingConnection,hash_api_key(code))
    if not row or row.user_id!=user.id or row.brand_id!=db.info.get('brand_id',0) or row.auth_version!=user.auth_version:
        raise HTTPException(404,'Connection review not found in this account and brand. Return to the workspace where you started.')
    expiry=row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
    if row.used or expiry<=utcnow():
        if row.encrypted_payload:row.encrypted_payload='';db.commit()
        raise HTTPException(410,'This connection review expired or was already completed. Start again from Account → Socials.')
    return user,row,json.loads(decrypt(row.encrypted_payload))


@router.get('/connections/review/{code}')
def review(code:str,request:Request,db=Depends(get_db)):
    from .app import templates,template_context
    user,row,payload=owned(db,request,code)
    safe=[{k:c.get(k,'') for k in ('platform','account_id','username','display_name')} for c in payload['candidates']]
    return templates.TemplateResponse(request,'connection_review.html',template_context(request,user,code=code,candidates=safe,platform=row.platform))


@router.post('/connections/review/{code}')
def confirm(code:str,request:Request,choice:int=Form(...),action:str=Form('connect'),db=Depends(get_db)):
    from .social import upsert_connection
    user,row,payload=owned(db,request,code)
    if action not in {'connect','cancel','switch'}:raise HTTPException(400,'Choose a connection action.')
    if action=='connect' and not 0<=choice<len(payload['candidates']):raise HTTPException(400,'Choose an account from this review.')
    claimed=db.execute(update(PendingConnection).where(PendingConnection.code_hash==row.code_hash,PendingConnection.used.is_(False),PendingConnection.expires_at>utcnow()).values(used=True,encrypted_payload='').execution_options(synchronize_session=False))
    if claimed.rowcount!=1:db.rollback();raise HTTPException(409,'This connection review was already completed.')
    if action=='connect':
        candidate=payload['candidates'][choice]
        existing=db.scalar(select(SocialConnection).where(SocialConnection.user_id==user.id,SocialConnection.platform==candidate['platform'],SocialConnection.account_id==candidate['account_id'],SocialConnection.active.is_(True)))
        # Keep an existing direct Instagram grant when the linked-Page route returns it.
        preserve=existing and candidate['platform']=='instagram' and 'instagram_business_basic' in (existing.scope or '') and candidate.get('metadata',{}).get('auth_provider')=='facebook_login'
        if not preserve:upsert_connection(db,user_id=user.id,**candidate)
    db.commit()
    if action=='switch':return RedirectResponse(f'/connect/{row.platform}?switch_account=1&workspace={row.brand_id}',303)
    destination='/onboarding/socials' if payload['onboarding'] else '/account'
    return RedirectResponse(f'{destination}?{"connected" if action=="connect" else "cancelled"}={row.platform}&workspace={row.brand_id}',303)
