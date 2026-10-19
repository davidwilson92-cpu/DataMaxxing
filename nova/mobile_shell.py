"""Bounded native handoffs into the shared Studio. No parallel publishing engine.

Access/refresh tokens never enter WebKit, JavaScript, a URL or browser storage.
The browser receives a revocable cookie bound to the originating device session.
"""
import hashlib
import hmac
import html
import os
import re
import secrets
from datetime import timedelta
from typing import Literal
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from starlette.middleware.base import BaseHTTPMiddleware

from .db import MobileHandoff, MobileSession, SessionLocal, SocialConnection, User, get_db, utcnow
from .mobile_auth import enabled, future, native_user, require_enabled
from .security import current_user, hash_api_key, session_secret, user_from_session

router = APIRouter()
PAGES = {'/studio', '/drafts', '/analytics', '/account', '/security', '/brands'}
BROWSER_PAGES = {'/account', '/security', '/connect/instagram', '/connect/facebook', '/connect/x', '/connect/tiktok'}


def destination(value, purpose):
    parts = urlsplit(value)
    allowed = BROWSER_PAGES if purpose == 'browser' else PAGES
    if parts.scheme or parts.netloc or parts.path not in allowed or '\\' in value or '%' in parts.path:
        raise HTTPException(400, 'Open this page from Zova')
    values = parse_qs(parts.query, keep_blank_values=True)
    if set(values) - {'workspace', 'draft'} or any(len(v) != 1 for v in values.values()):
        raise HTTPException(400, 'Invalid workspace destination')
    for key, val in values.items():
        if not re.fullmatch(r'0|[1-9][0-9]{0,17}', val[0]) or int(val[0]) >= 2**63:
            raise HTTPException(400, 'Invalid workspace destination')
        if key == 'draft' and parts.path != '/studio':
            raise HTTPException(400, 'Invalid draft destination')
    if parts.fragment and parts.fragment not in {'socials', 'voice', 'security'}:
        raise HTTPException(400, 'Invalid page destination')
    return urlunsplit(('', '', parts.path, urlencode({k: v[0] for k, v in values.items()}), parts.fragment))


def shell_session(db, handoff):
    session = db.get(MobileSession, handoff.session_id) if handoff else None
    user = db.get(User, session.user_id) if session else None
    if (not handoff or handoff.used or not future(handoff.expires_at)
            or not session or session.revoked or not future(session.expires_at)
            or not user or not user.active or user.auth_version != session.auth_version):
        raise HTTPException(401, 'Return to Zova and sign in again')
    return session, user


def session_cookie(session):
    expiry = session.expires_at.replace(tzinfo=session.expires_at.tzinfo or utcnow().tzinfo)
    payload = f'ios.{session.user_id}.{session.auth_version}.{int(expiry.timestamp())}.{session.id}.{secrets.token_hex(16)}'
    return payload + '.' + hmac.new(session_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()


def accept_handoff(ticket, purpose, request, native=False):
    with SessionLocal() as db:
        row = db.get(MobileHandoff, hash_api_key(ticket))
        session, user = shell_session(db, row)
        if native and row.session_id != request.state.mobile_session_id:
            raise HTTPException(401, 'Invalid native session handoff')
        if row.purpose != purpose:
            raise HTTPException(401, 'Invalid sign-in handoff')
        claimed = db.execute(update(MobileHandoff).where(
            MobileHandoff.token_hash == row.token_hash, MobileHandoff.used.is_(False),
            MobileHandoff.expires_at > utcnow(),
            MobileHandoff.session_id.in_(select(MobileSession.id).where(
                MobileSession.id == session.id, MobileSession.revoked.is_(False),
                MobileSession.expires_at > utcnow())),
        ).values(used=True).execution_options(synchronize_session=False))
        if claimed.rowcount != 1:
            raise HTTPException(401, 'Sign-in handoff expired or already used')
        db.commit()
        target = destination(row.destination, purpose)
        response = JSONResponse({'destination': target}) if native else RedirectResponse(target, 303)
        response.set_cookie('nova_session', session_cookie(session),
                            max_age=max(0, int((session.expires_at.replace(tzinfo=session.expires_at.tzinfo or utcnow().tzinfo) - utcnow()).total_seconds())),
                            httponly=True, secure=os.environ.get('PUBLIC_BASE_URL', '').startswith('https://'), samesite='lax')
        if not native:
            response.delete_cookie('zova_brand')
        return response


class HandoffRequest(BaseModel):
    destination: str = Field(default='/studio', min_length=1, max_length=500)
    purpose: Literal['studio', 'browser'] = 'studio'


@router.get('/api/v1/native-config')
def config():
    return {'enabled': enabled(), 'api_version': 1, 'client_id': 'zova-ios',
            'redirect_uri': os.environ.get('ZOVA_IOS_REDIRECT_URI', '') if enabled() else '',
            'review_required': True, 'native_billing': False}


@router.get('/api/v1/native-profile')
def profile(request: Request):
    user = native_user(request)
    return {'id': user.id, 'name': user.display_name, 'email': user.email}


@router.get('/api/native-connections')
def connections(request: Request, db=Depends(get_db)):
    user = current_user(request)
    result = {}
    for row in db.scalars(select(SocialConnection).where(SocialConnection.user_id == user.id, SocialConnection.active.is_(True))).all():
        result.setdefault(row.platform, []).append(row.username or row.display_name or 'Connected account')
    return {'connections': result}


@router.post('/api/v1/native-handoff')
def create_handoff(body: HandoffRequest, request: Request):
    user = native_user(request)
    target = destination(body.destination, body.purpose)
    ticket = secrets.token_urlsafe(48)
    with SessionLocal() as db:
        # Recheck the session in the mutation transaction, not browser cookies.
        session = db.get(MobileSession, request.state.mobile_session_id)
        if not session or session.revoked or session.user_id != user.id or not future(session.expires_at):
            raise HTTPException(401, 'Sign in again')
        db.add(MobileHandoff(token_hash=hash_api_key(ticket), session_id=session.id,
                             destination=target, purpose=body.purpose,
                             expires_at=utcnow() + timedelta(seconds=60)))
        db.commit()
    return {'ticket': ticket, 'expires_in': 60}


class NativeWebTicket(BaseModel):
    ticket: str = Field(min_length=40, max_length=100)


@router.post('/api/v1/native-web-session')
def native_web_session(body: NativeWebTicket, request: Request):
    # Redeem through native URLSession, then install only this HttpOnly cookie
    # into WebKit before its first GET. No browser-origin exception is needed.
    native_user(request)
    return accept_handoff(body.ticket, 'studio', request, native=True)


@router.post('/mobile/web-session', include_in_schema=False)
def web_session(request: Request, ticket: str = Form(..., min_length=40, max_length=100)):
    require_enabled()
    return accept_handoff(ticket, 'studio', request)


def browser_proof(ticket, cookie):
    return hmac.new(session_secret().encode(), f'native-browser:{hash_api_key(ticket)}:{hash_api_key(cookie)}'.encode(), hashlib.sha256).hexdigest()


def resume_browser(ticket, request):
    """Back/refresh may revisit the form after its cookie was replaced.

    Only navigate an already-authorised cookie from the exact original device
    session. Never redeem the ticket again or issue another cookie.
    """
    cookie = request.cookies.get('nova_session', '')
    parts = cookie.split('.')
    if len(parts) != 7 or parts[0] != 'ios':
        return None
    user = user_from_session(cookie)
    if not user:
        return None
    with SessionLocal() as db:
        row = db.get(MobileHandoff, hash_api_key(ticket))
        if not row or not row.used or row.purpose != 'browser' or row.session_id != parts[4]:
            return None
        return RedirectResponse(destination(row.destination, 'browser'), 303)


def browser_recovery(ticket=None, status=401):
    action = (f'<a href="/mobile/browser/{html.escape(ticket, quote=True)}">Review your Zova account again</a>'
              if ticket else '<p>Close this browser and start the connection again from Zova.</p>')
    return HTMLResponse(f'''<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Continue your connection | Zova</title><link rel="stylesheet" href="/static/mobile-auth.css?v=20261019-dark"></head><body><main><h1>Let’s resume your connection</h1><p>This browser confirmation is no longer current. Your saved work and existing connections are unchanged.</p>{action}</main></body></html>''', status_code=status)


@router.get('/mobile/browser/{ticket}', include_in_schema=False)
def browser_prompt(ticket: str, request: Request):
    require_enabled()
    if not 40 <= len(ticket) <= 100:
        raise HTTPException(404, 'Not found')
    if resumed := resume_browser(ticket, request):
        return resumed
    with SessionLocal() as db:
        row = db.get(MobileHandoff, hash_api_key(ticket))
        try:
            session, user = shell_session(db, row)
        except HTTPException:
            return browser_recovery()
        if row.purpose != 'browser':
            raise HTTPException(401, 'Invalid browser handoff')
        proof = browser_proof(ticket, request.cookies.get('nova_session', ''))
        return HTMLResponse(f'''<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Continue in your browser | Zova</title><link rel="stylesheet" href="/static/mobile-auth.css?v=20261019-dark"></head><body><main><h1>Continue as {html.escape(user.display_name or 'you')}</h1><p>{html.escape(user.email)}</p><p>This opens the account from your iPhone app. Only continue if this is your Zova email. Your Instagram login is separate.</p><form method="post"><input type="hidden" name="proof" value="{proof}"><button>Continue to your account</button></form><p>When finished, close this browser and return to Zova to refresh your connections.</p><form method="post"><input type="hidden" name="proof" value="{proof}"><button name="decision" value="cancel">This isn’t my Zova account</button></form></main></body></html>''')


@router.post('/mobile/browser/{ticket}', include_in_schema=False)
def browser_accept(ticket: str, request: Request, proof: str = Form(...), decision: Literal['continue', 'cancel'] = Form('continue')):
    require_enabled()
    if decision == 'continue' and (resumed := resume_browser(ticket, request)):
        return resumed
    if not hmac.compare_digest(proof, browser_proof(ticket, request.cookies.get('nova_session', ''))):
        return browser_recovery(ticket, status=403)
    if decision == 'cancel':
        with SessionLocal() as db:
            row = db.get(MobileHandoff, hash_api_key(ticket))
            shell_session(db, row)
            if row.purpose != 'browser':
                raise HTTPException(401, 'Invalid browser handoff')
            claimed = db.execute(update(MobileHandoff).where(
                MobileHandoff.token_hash == row.token_hash, MobileHandoff.used.is_(False)
            ).values(used=True))
            if claimed.rowcount != 1:
                raise HTTPException(401, 'Sign-in handoff expired or already used')
            db.commit()
        return HTMLResponse('''<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Switch Zova account</title><link rel="stylesheet" href="/static/mobile-auth.css?v=20261019-dark"></head><body><main><h1>Switch your Zova account</h1><p>No social account was connected.</p><p>Close this browser. In the Zova app, open Account and select Sign out. Then sign in with your own Zova email before connecting Instagram.</p><p>Your existing drafts and connections stay with their original account.</p></main></body></html>''')
    try:
        return accept_handoff(ticket, 'browser', request)
    except HTTPException:
        return browser_recovery()


@router.get('/mobile/callback', include_in_schema=False)
def callback():
    return HTMLResponse('<!doctype html><html lang="en"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Return to Zova</title><p>Return to the Zova app to finish signing in. If this page stays open, cancel and start sign-in again from the app.</p></html>')


@router.get('/.well-known/apple-app-site-association', include_in_schema=False)
def association():
    app_id = os.environ.get('ZOVA_IOS_APP_ID', '')
    if not enabled() or not re.fullmatch(r'[A-Z0-9]{10}\.[A-Za-z0-9.-]+', app_id):
        raise HTTPException(404, 'Not found')
    return JSONResponse({'applinks': {'details': [{'appIDs': [app_id], 'components': [{'/': '/mobile/callback', 'comment': 'Zova native sign-in only'}]}]}, 'webcredentials': {'apps': [app_id]}})


class NativeBillingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        cookie = request.cookies.get('nova_session', '')
        if cookie.startswith('ios.') and path.startswith('/billing/'):
            return JSONResponse({'detail': 'Purchases are unavailable in the iOS beta.'}, 403,
                                headers={'Cache-Control': 'no-store'})
        return await call_next(request)
