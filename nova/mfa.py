"""Optional authenticator-based sign-in. No enrollment or grant changes by default."""
import base64
import hashlib
import hmac
import json
import os
import secrets
import struct
import time
from datetime import timedelta, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from .db import MfaChallenge, MfaSettings, User, get_db, utcnow
from .security import current_user, decrypt, encrypt, hash_api_key, verify_password, make_user_session
from .request_security import allowed_request
from .customer_service import context

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / 'templates'))
COOKIE = 'zova_mfa_challenge'


def _future(value):
    return value is not None and value.replace(tzinfo=timezone.utc) > utcnow()


def totp(secret, counter):
    key = base64.b32decode(secret, casefold=True)
    digest = hmac.new(key, struct.pack('>Q', counter), hashlib.sha1).digest()
    offset = digest[-1] & 15
    number = struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7fffffff
    return f'{number % 1000000:06d}'


def _counter(secret, code):
    if len(code) != 6 or not code.isascii() or not code.isdigit():
        return None
    now = int(time.time()) // 30
    for value in (now, now - 1, now + 1):
        if value >= 0 and hmac.compare_digest(totp(secret, value), code):
            return value
    return None


def _code_hash(code):
    return hash_api_key(code.replace('-', '').replace(' ', '').lower())


def _new_recovery_codes():
    codes = []
    for _ in range(10):
        raw = secrets.token_hex(10)
        codes.append('-'.join(raw[i:i+5] for i in range(0, 20, 5)))
    return codes, json.dumps([_code_hash(code) for code in codes])


def _limit(uid):
    if not allowed_request(f'mfa-factor:{uid}', 8, 300):
        raise HTTPException(429, 'Too many security-code attempts. Wait five minutes and try again.')


def _page(request, **values):
    response = templates.TemplateResponse(request=request, name='mfa.html', context={**context(), **values})
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


def _cookie(response, user_id, version):
    token = make_user_session(user_id, expected_auth_version=version)
    response.set_cookie('nova_session', token, max_age=30*86400, httponly=True,
                        secure=os.environ.get('PUBLIC_BASE_URL', '').startswith('https://'), samesite='lax', path='/')
    response.delete_cookie(COOKIE, path='/mfa')
    return response


def begin_login(db, user, verified_version, destination='/studio'):
    settings = db.get(MfaSettings, user.id)
    if not settings or not settings.enabled:
        return None
    if not destination.startswith('/') or destination.startswith('//') or '\\' in destination:
        destination = '/studio'
    token = secrets.token_urlsafe(32)
    db.execute(delete(MfaChallenge).where(MfaChallenge.expires_at < utcnow()))
    db.add(MfaChallenge(token_hash=hash_api_key(token), user_id=user.id, auth_version=verified_version,
                        destination=destination[:500], expires_at=utcnow()+timedelta(minutes=5)))
    db.commit()
    response = RedirectResponse('/mfa/challenge', 303)
    response.set_cookie(COOKIE, encrypt(token), max_age=300, httponly=True,
                        secure=os.environ.get('PUBLIC_BASE_URL', '').startswith('https://'), samesite='lax', path='/mfa')
    # A password alone never establishes the newly selected account's session.
    response.delete_cookie('nova_session', path='/')
    return response


def _challenge(db, request):
    try:
        token = decrypt(request.cookies.get(COOKIE, ''))
        row = db.get(MfaChallenge, hash_api_key(token))
    except (ValueError, RuntimeError):
        row = None
    if not row or row.used or not _future(row.expires_at):
        raise HTTPException(400, 'This sign-in has expired or was used. Sign in again.')
    user = db.get(User, row.user_id)
    settings = db.get(MfaSettings, row.user_id)
    if not user or not user.active or user.auth_version != row.auth_version or not settings or not settings.enabled:
        raise HTTPException(400, 'Your account security changed. Sign in again.')
    return row, settings


def _consume_factor(db, settings, code):
    if len(code) > 40:
        return False
    raw_hashes = settings.recovery_hashes_json
    hashes = json.loads(raw_hashes)
    supplied = _code_hash(code)
    matched = next((stored for stored in hashes if hmac.compare_digest(stored, supplied)), None)
    if matched:
        remaining = json.dumps([stored for stored in hashes if stored != matched])
        result = db.execute(update(MfaSettings).where(MfaSettings.user_id == settings.user_id,
            MfaSettings.enabled.is_(True), MfaSettings.recovery_hashes_json == raw_hashes,
            MfaSettings.encrypted_secret == settings.encrypted_secret).values(recovery_hashes_json=remaining)
            .execution_options(synchronize_session=False))
        return result.rowcount == 1
    counter = _counter(decrypt(settings.encrypted_secret), code.strip())
    if counter is None:
        return False
    result = db.execute(update(MfaSettings).where(MfaSettings.user_id == settings.user_id,
        MfaSettings.enabled.is_(True), MfaSettings.encrypted_secret == settings.encrypted_secret,
        MfaSettings.last_counter < counter).values(last_counter=counter).execution_options(synchronize_session=False))
    return result.rowcount == 1


@router.get('/mfa/challenge')
def challenge_page(request: Request, db=Depends(get_db)):
    _challenge(db, request)
    return _page(request, challenge=True)


@router.post('/mfa/challenge')
def complete_login(request: Request, code: str = Form(...), db=Depends(get_db)):
    challenge, settings = _challenge(db, request)
    _limit(challenge.user_id)
    claimed = db.execute(update(MfaChallenge).where(MfaChallenge.token_hash == challenge.token_hash,
        MfaChallenge.used.is_(False), MfaChallenge.expires_at > utcnow()).values(used=True)
        .execution_options(synchronize_session=False))
    if claimed.rowcount != 1 or not _consume_factor(db, settings, code):
        db.rollback()
        return _page(request, challenge=True, error='That code is invalid or already used. Try a fresh code or a recovery code.')
    authenticated = db.execute(update(User).where(User.id == challenge.user_id,
        User.active.is_(True), User.auth_version == challenge.auth_version)
        .values(last_login_at=utcnow()).execution_options(synchronize_session=False))
    if authenticated.rowcount != 1:
        db.rollback(); raise HTTPException(400, 'Account security changed. Sign in again.')
    db.commit()
    response = RedirectResponse(challenge.destination, 303)
    response.delete_cookie('zova_brand', path='/')
    response.delete_cookie('zova_onboarding', path='/')
    try:
        return _cookie(response, challenge.user_id, challenge.auth_version)
    except ValueError:
        return RedirectResponse('/login?error=Your+account+security+changed.+Sign+in+again.', 303)


def _owned(db, request):
    user = db.get(User, current_user(request).id)
    return user, db.get(MfaSettings, user.id)


@router.get('/mfa/setup')
def settings_page(request: Request, db=Depends(get_db)):
    user, settings = _owned(db, request)
    return _page(request, user=user, enabled=bool(settings and settings.enabled))


@router.post('/mfa/setup')
def start_setup(request: Request, password: str = Form(...), db=Depends(get_db)):
    user, settings = _owned(db, request)
    _limit(user.id)
    if not verify_password(password, user.password_hash):
        return _page(request, user=user, enabled=bool(settings and settings.enabled), error='Check your current Zova password.')
    if settings and settings.enabled:
        raise HTTPException(409, 'Two-step sign-in is already enabled.')
    secret = base64.b32encode(secrets.token_bytes(20)).decode()
    values = dict(encrypted_secret=encrypt(secret), setup_auth_version=user.auth_version,
                  setup_expires_at=utcnow()+timedelta(minutes=10), last_counter=-1)
    if not settings:
        settings = MfaSettings(user_id=user.id, **values)
        db.add(settings)
    else:
        changed = db.execute(update(MfaSettings).where(MfaSettings.user_id == user.id,
            MfaSettings.enabled.is_(False)).values(**values).execution_options(synchronize_session=False))
        if changed.rowcount != 1:
            db.rollback(); raise HTTPException(409, 'Setup changed. Open security settings again.')
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Setup changed in another tab. Start again.')
    return _page(request, user=user, setup_secret=secret)


@router.post('/mfa/enable')
def enable(request: Request, code: str = Form(...), db=Depends(get_db)):
    user, settings = _owned(db, request)
    _limit(user.id)
    if not settings or settings.enabled or settings.setup_auth_version != user.auth_version or not _future(settings.setup_expires_at):
        raise HTTPException(400, 'Start authenticator setup again.')
    secret = decrypt(settings.encrypted_secret)
    counter = _counter(secret, code.strip())
    if counter is None:
        return _page(request, user=user, setup_secret=secret, error='Check the code and your authenticator time, then try again.')
    codes, hashes = _new_recovery_codes()
    changed = db.execute(update(MfaSettings).where(MfaSettings.user_id == user.id,
        MfaSettings.enabled.is_(False), MfaSettings.encrypted_secret == settings.encrypted_secret,
        MfaSettings.setup_expires_at > utcnow()).values(enabled=True, last_counter=counter,
        setup_expires_at=None, recovery_hashes_json=hashes).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        db.rollback(); raise HTTPException(409, 'Setup changed. Open security settings again.')
    version = user.auth_version
    changed = db.execute(update(User).where(User.id == user.id, User.active.is_(True), User.auth_version == version)
        .values(auth_version=version+1).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        db.rollback(); raise HTTPException(409, 'Account security changed. Sign in again.')
    db.commit()
    response = _page(request, user=user, enabled=True, recovery_codes=codes)
    try:
        return _cookie(response, user.id, version+1)
    except ValueError:
        return RedirectResponse('/login?error=Account+security+changed.+Sign+in+again.', 303)


@router.post('/mfa/disable')
def disable(request: Request, password: str = Form(...), code: str = Form(...), db=Depends(get_db)):
    user, settings = _owned(db, request)
    _limit(user.id)
    if not settings or not settings.enabled or not verify_password(password, user.password_hash):
        return _page(request, user=user, enabled=bool(settings and settings.enabled), error='Check your password and security code.')
    if not _consume_factor(db, settings, code):
        db.rollback()
        return _page(request, user=user, enabled=True, error='Use a fresh authenticator code or an unused recovery code.')
    version = user.auth_version
    changed = db.execute(update(User).where(User.id == user.id, User.active.is_(True), User.auth_version == version)
        .values(auth_version=version+1).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        db.rollback(); raise HTTPException(409, 'Account security changed. Sign in again.')
    db.execute(update(MfaSettings).where(MfaSettings.user_id == user.id).values(enabled=False,
        encrypted_secret='', recovery_hashes_json='[]', last_counter=-1, setup_expires_at=None))
    db.execute(delete(MfaChallenge).where(MfaChallenge.user_id == user.id))
    db.commit()
    response = RedirectResponse('/mfa/setup', 303)
    try:
        return _cookie(response, user.id, version+1)
    except ValueError:
        return RedirectResponse('/login?error=Account+security+changed.+Sign+in+again.', 303)
