"""Single-use recovery links. No plaintext tokens in storage or logs."""
import os
import secrets
import smtplib
import ssl
from datetime import timedelta
from email.message import EmailMessage
from fastapi import APIRouter, Request, Form, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy import select, update
from .db import RecoveryToken, SessionLocal, User, utcnow
from .security import hash_api_key, hash_password
from .request_security import allowed_request
from .customer_service import context as service_context

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent/'templates'))


def recovery_ready():
    return bool(os.environ.get('SMTP_HOST') and os.environ.get('SMTP_FROM') and os.environ.get('PUBLIC_BASE_URL','').startswith('https://'))


def send_recovery_email(email, token):
    send_message(email, 'Reset your Zova password', 'Use this link within 15 minutes to reset your Zova password.\n\n'+os.environ['PUBLIC_BASE_URL'].rstrip('/')+'/reset-password#token='+token+'\n\nIf you did not request this, ignore this email. Your password has not changed.')


def send_message(email, subject, body):
    import uuid
    from .db import MailDelivery
    delivery_id=uuid.uuid4().hex
    with SessionLocal() as db:
        db.add(MailDelivery(id=delivery_id,status='sending'));db.commit()
    outcome='failed'
    try:
        smtp_message(email,subject,body)
        outcome='sent'
    finally:
        with SessionLocal() as db:
            db.get(MailDelivery,delivery_id).status=outcome;db.commit()


def smtp_message(email, subject, body):
    message=EmailMessage()
    message['From']=os.environ['SMTP_FROM']; message['To']=email
    message['Subject']=subject
    message.set_content(body)
    with smtplib.SMTP(os.environ['SMTP_HOST'],int(os.environ.get('SMTP_PORT','587')),timeout=10) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        if os.environ.get('SMTP_USERNAME'):
            smtp.login(os.environ['SMTP_USERNAME'],os.environ['SMTP_PASSWORD'])
        smtp.send_message(message)


@router.get('/forgot-password')
def forgot_page(request:Request):
    return templates.TemplateResponse(request=request,name='recovery.html',context={**service_context(),'ready':recovery_ready(),'sent':request.query_params.get('sent'),'token':None,'contact':os.environ.get('PRIVACY_CONTACT_EMAIL','')})


@router.post('/forgot-password')
def forgot(background_tasks:BackgroundTasks,email:str=Form(...)):
    email=email.strip().lower()[:320]
    # Same response whether the account exists, delivery succeeds, or this address is throttled.
    if recovery_ready() and allowed_request('recovery:'+email,3,900):
        with SessionLocal() as db:
            user=db.scalar(select(User).where(User.email==email,User.active.is_(True)))
            if user:
                token=secrets.token_urlsafe(32)
                db.add(RecoveryToken(token_hash=hash_api_key(token),user_id=user.id,auth_version=user.auth_version,expires_at=utcnow()+timedelta(minutes=15)))
                db.commit()
                background_tasks.add_task(deliver_recovery,email,token)
    return RedirectResponse('/forgot-password?sent=1',303)


def deliver_recovery(email, token):
    try: send_recovery_email(email,token)
    except Exception:
        import logging
        logging.getLogger(__name__).error('Recovery mail delivery failed; request a new link')
        with SessionLocal() as db:
            row=db.get(RecoveryToken,hash_api_key(token))
            if row:row.used=True;db.commit()


@router.get('/reset-password')
def reset_page(request:Request,token:str=''):
    response=templates.TemplateResponse(request=request,name='recovery.html',context={**service_context(),'ready':True,'sent':False,'token':token[:256],'reset':True})
    response.headers['Referrer-Policy']='no-referrer'
    return response


@router.post('/reset-password')
def reset(token:str=Form(...),password:str=Form(...),confirmation:str=Form(...)):
    if not 10<=len(password)<=256 or password!=confirmation:
        raise HTTPException(400,'Use matching passwords with 10–256 characters. Return to the form to try again.')
    with SessionLocal() as db:
        row=db.get(RecoveryToken,hash_api_key(token))
        if not row or row.used:
            raise HTTPException(400,'This reset link is invalid or already used. Request a new link.')
        changed=db.execute(update(RecoveryToken).where(RecoveryToken.token_hash==row.token_hash,RecoveryToken.used.is_(False),RecoveryToken.expires_at>utcnow()).values(used=True).execution_options(synchronize_session=False))
        if changed.rowcount!=1:
            db.rollback(); raise HTTPException(400,'This reset link has expired. Request a new link.')
        changed=db.execute(update(User).where(User.id==row.user_id,User.active.is_(True),User.auth_version==row.auth_version).values(password_hash=hash_password(password),auth_version=User.auth_version+1))
        if changed.rowcount!=1:
            db.rollback(); raise HTTPException(400,'Request a new reset link.')
        db.commit()
    return RedirectResponse('/login?error=Password+updated.+Sign+in+with+your+new+password.',303)
