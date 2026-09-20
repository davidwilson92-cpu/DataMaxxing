"""Optional email ownership proof; existing sessions and access are unchanged."""
import secrets
import os
from datetime import timedelta
from fastapi import APIRouter, BackgroundTasks, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import update
from .db import SessionLocal, EmailVerification, User, utcnow
from .security import current_user, hash_api_key
from . import recovery
from .request_security import allowed_request
from .customer_service import context

router=APIRouter()


def deliver(address,token):
    try:
        recovery.send_message(address,'Verify your Zova email',
            'Confirm your email within 15 minutes. Sign in to the same Zova account first.\n\n'+
            os.environ['PUBLIC_BASE_URL'].rstrip('/')+'/verify-email#token='+token)
    except Exception:
        import logging
        logging.getLogger(__name__).error('Verification mail delivery failed; request a new link')
        with SessionLocal() as db:
            row=db.get(EmailVerification,hash_api_key(token))
            if row:row.used=True;db.commit()


@router.post('/account/verify-email')
def send(request:Request, background_tasks:BackgroundTasks):
    user=current_user(request)
    if not recovery.recovery_ready():raise HTTPException(503,'Email delivery is unavailable. Contact support; your current access is unchanged.')
    if not user.email_verified_at and allowed_request(f'verification:{user.id}',3,900):
        token=secrets.token_urlsafe(32)
        with SessionLocal() as db:
            db.add(EmailVerification(token_hash=hash_api_key(token),user_id=user.id,email=user.email,expires_at=utcnow()+timedelta(minutes=15)))
            db.commit()
        background_tasks.add_task(deliver,user.email,token)
    return RedirectResponse('/verify-email?sent=1',303)


@router.get('/verify-email')
def page(request:Request):
    response=recovery.templates.TemplateResponse(request=request,name='verification.html',context=context())
    response.headers['Referrer-Policy']='no-referrer'
    return response


@router.post('/verify-email')
def confirm(request:Request, token:str=Form(...)):
    user=current_user(request)
    with SessionLocal() as db:
        row=db.get(EmailVerification,hash_api_key(token))
        if not row or row.user_id!=user.id or row.email!=user.email:
            raise HTTPException(400,'Sign in to the account that requested this link, or request another link.')
        result=db.execute(update(EmailVerification).where(EmailVerification.token_hash==row.token_hash,EmailVerification.used.is_(False),EmailVerification.expires_at>utcnow()).values(used=True).execution_options(synchronize_session=False))
        if result.rowcount!=1:raise HTTPException(400,'This link expired or was already used. Request another link.')
        db.execute(update(User).where(User.id==user.id,User.email==row.email,User.active.is_(True)).values(email_verified_at=utcnow()))
        db.commit()
    return RedirectResponse('/account?saved=verified',303)
