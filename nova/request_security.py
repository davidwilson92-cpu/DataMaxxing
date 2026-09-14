"""Shared database rate limits and browser-origin protection, including legacy sessions."""
import hashlib
import os
from datetime import timedelta
from urllib.parse import urlsplit

from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from .db import SessionLocal, RequestLimit, utcnow
from .security import user_from_session


def allowed_request(key, maximum, seconds):
    digest = hashlib.sha256(key.encode()).hexdigest()
    now = utcnow()
    with SessionLocal() as db:
        db.execute(delete(RequestLimit).where(RequestLimit.reset_at <= now))
        claimed = db.execute(update(RequestLimit).where(RequestLimit.key == digest, RequestLimit.count < maximum).values(count=RequestLimit.count + 1))
        if claimed.rowcount:
            db.commit(); return True
        if db.get(RequestLimit, digest):
            db.rollback(); return False
        db.add(RequestLimit(key=digest, count=1, reset_at=now + timedelta(seconds=seconds)))
        try:
            db.commit(); return True
        except IntegrityError:
            db.rollback()
            claimed = db.execute(update(RequestLimit).where(RequestLimit.key == digest, RequestLimit.count < maximum).values(count=RequestLimit.count + 1))
            db.commit(); return bool(claimed.rowcount)


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        external_callback = path in {'/billing/webhook','/data-deletion/callback','/auth/apple/callback'}
        unsafe = request.method not in {'GET','HEAD','OPTIONS'}
        response = None
        if unsafe and not external_callback:
            origin = request.headers.get('origin')
            configured = urlsplit(os.environ.get('PUBLIC_BASE_URL',''))
            expected = f'{configured.scheme}://{configured.netloc}' if configured.netloc else str(request.base_url).rstrip('/')
            # Browsers supply Origin on unsafe requests. Non-browser legacy clients have no ambient browser origin.
            if (origin and origin != expected) or request.headers.get('sec-fetch-site') == 'cross-site':
                response = JSONResponse({'detail':'Open Zova directly and try again.'},403)
            size = request.headers.get('content-length','0')
            maximum = 160*1024*1024 if path == '/api/media' else 1024*1024
            if size.isdigit() and int(size) > maximum:
                response = JSONResponse({'detail':'Request too large.'},413)
        if unsafe and not external_callback and response is None:
            from starlette.concurrency import run_in_threadpool
            user = await run_in_threadpool(user_from_session, request.cookies.get('nova_session'))
            identity = f'user:{user.id}' if user else f'ip:{request.client.host if request.client else "unknown"}'
            maximum, seconds = (30,300) if path in {'/login','/signup','/forgot-password','/reset-password'} else (120,60)
            maximum *= max(1,int(os.environ.get('RATE_LIMIT_SCALE','1')))
            if not await run_in_threadpool(allowed_request, f'{identity}:{"auth" if path in {"/login","/signup","/forgot-password","/reset-password"} else "mutations"}', maximum, seconds):
                response = JSONResponse({'detail':'Too many requests. Please wait before trying again.'},429,headers={'Retry-After':str(seconds)})
        if response is None:
            response = await call_next(request)
        response.headers.setdefault('X-Content-Type-Options','nosniff')
        response.headers.setdefault('X-Frame-Options','DENY')
        response.headers.setdefault('Referrer-Policy','same-origin')
        response.headers.setdefault('Permissions-Policy','camera=(), microphone=(), geolocation=()')
        response.headers.setdefault('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' https: data: blob:; media-src 'self' https: blob:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
        if os.environ.get('PUBLIC_BASE_URL','').startswith('https://'):
            response.headers.setdefault('Strict-Transport-Security','max-age=31536000')
        if not path.startswith('/static/'):
            response.headers.setdefault('Cache-Control','no-store')
        return response
