"""First-party native sessions. Browser consent + S256; no embedded client secret.

Disabled until an exact, owned HTTPS universal-link callback is configured.
Tokens are opaque and only hashes are stored. Refresh replay revokes the family.
"""
import base64
import hashlib
import hmac
import html
import os
import re
import secrets
from datetime import timedelta, timezone
from urllib.parse import urlencode, urlsplit

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, update

from .db import MobileGrant, MobileRefresh, MobileSession, SessionLocal, User, utcnow
from .security import hash_api_key, session_secret, user_from_session

router = APIRouter()
ACCESS_SECONDS = 900


def enabled():
    return os.environ.get('ZOVA_MOBILE_ENABLED', 'false').lower() == 'true'


def require_enabled():
    if not enabled():
        raise HTTPException(404, 'Not found')


def validate_client(client_id, redirect_uri):
    require_enabled()
    configured = os.environ.get('ZOVA_IOS_REDIRECT_URI', '')
    parts = urlsplit(configured)
    if (client_id != 'zova-ios' or not configured or redirect_uri != configured
            or parts.scheme != 'https' or not parts.hostname or parts.username
            or parts.password or parts.query or parts.fragment):
        raise HTTPException(400, 'Unrecognised mobile callback')


def future(value):
    return value.replace(tzinfo=value.tzinfo or timezone.utc) > utcnow()


def challenge_for(verifier):
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode('ascii')).digest()).decode().rstrip('=')


def consent_proof(grant_id, browser_token):
    return hmac.new(session_secret().encode(), f'mobile-consent:{grant_id}:{hash_api_key(browser_token)}'.encode(), hashlib.sha256).hexdigest()


def resume_destination(grant_id, db):
    """Resume only the completed sign-in that started this native request."""
    if not enabled() or not re.fullmatch(r'[A-Za-z0-9_-]{43}', grant_id or ''):
        return None
    row = db.get(MobileGrant, grant_id)
    if not row or row.code_hash or not future(row.expires_at):
        return None
    validate_client(row.client_id, row.redirect_uri)
    return '/mobile/authorize/' + row.id


@router.get('/mobile/authorize', include_in_schema=False)
def begin(request: Request, client_id: str, redirect_uri: str, code_challenge: str, state: str, code_challenge_method: str = 'S256'):
    validate_client(client_id, redirect_uri)
    if code_challenge_method != 'S256' or not re.fullmatch(r'[A-Za-z0-9_-]{43}', code_challenge) or not re.fullmatch(r'[A-Za-z0-9_-]{32,128}', state):
        raise HTTPException(400, 'S256 challenge and random state required')
    from .request_security import allowed_request
    identity = request.client.host if request.client else 'unknown'
    maximum = 20 * max(1, int(os.environ.get('RATE_LIMIT_SCALE', '1')))
    if not allowed_request('native-signin:' + identity, maximum, 300):
        raise HTTPException(429, 'Wait a moment before signing in again', headers={'Retry-After': '300'})
    remove_expired_sessions()
    # GET creates only a short-lived pending request, never a session or grant.
    with SessionLocal() as db:
        grant = MobileGrant(id=secrets.token_urlsafe(32), client_id=client_id, redirect_uri=redirect_uri,
                            challenge=code_challenge, state=state, expires_at=utcnow()+timedelta(minutes=10))
        db.add(grant); db.commit()
        response = RedirectResponse('/mobile/authorize/'+grant.id, 303)
        response.set_cookie('zova_mobile_grant', grant.id, max_age=600, httponly=True,
                            secure=redirect_uri.startswith('https://'), samesite='lax')
        return response


@router.get('/mobile/authorize/{grant_id}', include_in_schema=False)
def consent(grant_id: str, request: Request):
    require_enabled()
    with SessionLocal() as db:
        grant = db.get(MobileGrant, grant_id)
        if not grant or grant.code_hash or not future(grant.expires_at):
            raise HTTPException(400, 'Sign-in request expired. Start again from the app.')
        validate_client(grant.client_id, grant.redirect_uri)
    token = request.cookies.get('nova_session', '')
    user = user_from_session(token)
    if not user:
        return RedirectResponse('/login?'+urlencode({'next':'/mobile/authorize/'+grant_id}), 303)
    proof = consent_proof(grant_id, token)
    return HTMLResponse(f'''<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sign in to Zova for iOS</title>
    <link rel="stylesheet" href="/static/mobile-auth.css"></head><body><main>
    <img src="/static/zova-mark.svg" alt="Zova" width="48" height="48">
    <h1>Continue to Zova for iOS</h1><p>Sign in as <strong>{html.escape(user.email)}</strong>.</p>
    <p>Your drafts, strategy and connected accounts will be available in the app. Posting still needs your approval.</p>
    <form method="post"><input type="hidden" name="proof" value="{proof}"><button type="submit">Continue to the app</button></form>
    <p><a href="/login?next=/mobile/authorize/{html.escape(grant_id)}">Use a different account</a></p>
    <form method="post"><input type="hidden" name="proof" value="{proof}"><button type="submit" name="decision" value="cancel">Cancel sign-in</button></form></main></body></html>''')


@router.post('/mobile/authorize/{grant_id}', include_in_schema=False)
def approve(grant_id: str, request: Request, proof: str = Form(...), decision: str = Form('approve')):
    require_enabled()
    token = request.cookies.get('nova_session', '')
    user = user_from_session(token)
    if not user or not hmac.compare_digest(proof, consent_proof(grant_id, token)):
        raise HTTPException(403, 'Sign-in confirmation expired')
    if decision not in {'approve', 'cancel'}:
        raise HTTPException(400, 'Invalid sign-in decision')
    code = secrets.token_urlsafe(32)
    with SessionLocal() as db:
        row = db.get(MobileGrant, grant_id)
        if not row:
            raise HTTPException(400, 'Sign-in request expired')
        validate_client(row.client_id, row.redirect_uri)
        if decision == 'cancel':
            changed = db.execute(update(MobileGrant).where(MobileGrant.id==grant_id, MobileGrant.code_hash.is_(None), MobileGrant.expires_at>utcnow()).values(expires_at=utcnow()).execution_options(synchronize_session=False))
            if changed.rowcount != 1:
                raise HTTPException(409, 'Sign-in request already completed or expired')
            db.commit()
            response = RedirectResponse(row.redirect_uri+'?'+urlencode({'error':'access_denied','state':row.state}),303)
            response.delete_cookie('zova_mobile_grant')
            return response
        claimed = db.execute(update(MobileGrant).where(MobileGrant.id==grant_id, MobileGrant.code_hash.is_(None), MobileGrant.expires_at>utcnow()).values(
            user_id=user.id, auth_version=user.auth_version, code_hash=hash_api_key(code), expires_at=utcnow()+timedelta(seconds=90)).execution_options(synchronize_session=False))
        if claimed.rowcount != 1:
            raise HTTPException(409, 'Sign-in request already completed or expired')
        db.commit()
        response = RedirectResponse(row.redirect_uri+'?'+urlencode({'code':code,'state':row.state}),303)
        response.delete_cookie('zova_mobile_grant')
        return response


class CodeExchange(BaseModel):
    client_id: str = Field(max_length=40)
    redirect_uri: str = Field(max_length=500)
    code: str = Field(min_length=40, max_length=100)
    code_verifier: str = Field(pattern=r'^[A-Za-z0-9._~-]{43,128}$')


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=40, max_length=100)


def token_pair(db, session):
    access, refresh = secrets.token_urlsafe(48), secrets.token_urlsafe(48)
    session.access_hash = hash_api_key(access)
    session.access_expires_at = utcnow()+timedelta(seconds=ACCESS_SECONDS)
    db.flush([session])
    db.add(MobileRefresh(token_hash=hash_api_key(refresh), session_id=session.id))
    return {'access_token':access, 'refresh_token':refresh, 'token_type':'Bearer', 'expires_in':ACCESS_SECONDS,
            'session_id':session.id, 'refresh_expires_at':session.expires_at.isoformat()}


def remove_expired_sessions():
    """Only expired native authority; no drafts, uploads or web sessions touched."""
    from sqlalchemy import delete
    from .db import MobileHandoff
    with SessionLocal() as db:
        expired=select(MobileSession.id).where(MobileSession.expires_at<=utcnow())
        db.execute(delete(MobileHandoff).where(MobileHandoff.session_id.in_(expired)))
        db.execute(delete(MobileHandoff).where(MobileHandoff.expires_at<=utcnow()))
        db.execute(delete(MobileRefresh).where(MobileRefresh.session_id.in_(expired)))
        db.execute(delete(MobileSession).where(MobileSession.expires_at<=utcnow()))
        db.execute(delete(MobileGrant).where(MobileGrant.expires_at<=utcnow()))
        db.commit()


@router.post('/api/v1/auth/token')
def exchange(body: CodeExchange):
    validate_client(body.client_id, body.redirect_uri)
    with SessionLocal() as db:
        row = db.scalar(select(MobileGrant).where(MobileGrant.code_hash==hash_api_key(body.code)))
        if (not row or row.used or not future(row.expires_at) or row.client_id!=body.client_id
                or row.redirect_uri!=body.redirect_uri or not hmac.compare_digest(row.challenge,challenge_for(body.code_verifier))):
            raise HTTPException(401,'Invalid or expired sign-in code')
        user = db.get(User,row.user_id)
        if not user or not user.active or user.auth_version!=row.auth_version:
            raise HTTPException(401,'Sign in again')
        claimed = db.execute(update(MobileGrant).where(MobileGrant.id==row.id,MobileGrant.used.is_(False),MobileGrant.expires_at>utcnow()).values(used=True).execution_options(synchronize_session=False))
        if claimed.rowcount!=1:
            raise HTTPException(401,'Sign-in code already used')
        session = MobileSession(id=secrets.token_urlsafe(24), user_id=user.id, auth_version=user.auth_version,
                                expires_at=utcnow()+timedelta(days=30))
        db.add(session)
        result=token_pair(db,session)
        db.commit()
        return result


@router.post('/api/v1/auth/refresh')
def refresh(body: RefreshRequest):
    require_enabled()
    with SessionLocal() as db:
        row=db.get(MobileRefresh,hash_api_key(body.refresh_token))
        session=db.get(MobileSession,row.session_id) if row else None
        user=db.get(User,session.user_id) if session else None
        if not session or session.revoked or not future(session.expires_at) or not user or not user.active or user.auth_version!=session.auth_version:
            raise HTTPException(401,'Sign in again')
        claimed=db.execute(update(MobileRefresh).where(MobileRefresh.token_hash==row.token_hash,MobileRefresh.used.is_(False)).values(used=True).execution_options(synchronize_session=False))
        if claimed.rowcount!=1:
            db.execute(update(MobileSession).where(MobileSession.id==session.id).values(revoked=True))
            db.commit()
            raise HTTPException(401,'Refresh token reused. Sign in again.')
        result=token_pair(db,session)
        db.commit()
        return result


def native_user(request):
    require_enabled()
    scheme, _, token=request.headers.get('authorization','').partition(' ')
    if scheme.lower()!='bearer' or not 40<=len(token)<=100:
        raise HTTPException(401,'Sign in required',headers={'WWW-Authenticate':'Bearer'})
    with SessionLocal() as db:
        session=db.scalar(select(MobileSession).where(MobileSession.access_hash==hash_api_key(token)))
        user=db.get(User,session.user_id) if session else None
        if not session or session.revoked or not future(session.expires_at) or not future(session.access_expires_at) or not user or not user.active or user.auth_version!=session.auth_version:
            raise HTTPException(401,'Sign in required',headers={'WWW-Authenticate':'Bearer'})
        request.state.mobile_session_id=session.id
        db.expunge(user)
        return user


@router.post('/api/v1/auth/logout', status_code=204)
def logout(request: Request):
    user=native_user(request)
    with SessionLocal() as db:
        db.execute(update(MobileSession).where(MobileSession.id==request.state.mobile_session_id,MobileSession.user_id==user.id).values(revoked=True))
        db.commit()


@router.get('/api/v1/auth/sessions')
def sessions(request: Request):
    user=native_user(request)
    with SessionLocal() as db:
        rows=db.scalars(select(MobileSession).where(MobileSession.user_id==user.id,MobileSession.revoked.is_(False),MobileSession.expires_at>utcnow(),MobileSession.auth_version==user.auth_version).order_by(MobileSession.created_at.desc()).limit(100)).all()
        return {'sessions':[{'id':r.id,'created_at':r.created_at.isoformat(),'expires_at':r.expires_at.isoformat(),'current':r.id==request.state.mobile_session_id} for r in rows]}


@router.delete('/api/v1/auth/sessions/{session_id}',status_code=204)
def revoke(session_id: str,request: Request):
    user=native_user(request)
    with SessionLocal() as db:
        changed=db.execute(update(MobileSession).where(MobileSession.id==session_id,MobileSession.user_id==user.id).values(revoked=True))
        if changed.rowcount!=1:
            raise HTTPException(404,'Session not found')
        db.commit()
