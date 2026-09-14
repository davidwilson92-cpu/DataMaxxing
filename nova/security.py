from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import timedelta, datetime, timezone
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, Request
from .db import SessionLocal, User, RevokedSession, utcnow


def hash_api_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def fernet() -> Fernet:
    key = os.environ.get('CREDENTIAL_ENCRYPTION_KEY')
    if not key:
        raise RuntimeError('CREDENTIAL_ENCRYPTION_KEY is required')
    return Fernet(key.encode())


def encrypt(value: str) -> str:
    return fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    try:
        return fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise RuntimeError('Unable to decrypt stored credentials') from exc


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        algorithm, salt_hex, digest_hex = hashed.split("$", 2)
        if algorithm != "scrypt":
            return False
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1, dklen=32)
        return hmac.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False


def session_secret() -> str:
    value = os.environ.get('SESSION_SECRET') or os.environ.get('ADMIN_API_KEY')
    if not value:
        raise RuntimeError('SESSION_SECRET is required')
    return value


def make_user_session(user_id: int) -> str:
    expires = int((utcnow() + timedelta(days=30)).timestamp())
    with SessionLocal() as db:
        user = db.get(User, user_id)
        if not user or not user.active:
            raise ValueError('Active user required')
        payload = f'v2.{user_id}.{user.auth_version}.{expires}.{secrets.token_hex(16)}'
    signature = hmac.new(session_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f'{payload}.{signature}'


def user_from_session(token: str | None) -> User | None:
    if not token:
        return None
    try:
        parts = token.split('.')
        if len(parts) == 3:
            user_id, expires, signature = parts
            version = 0  # Existing reviewer/customer sessions remain valid until revoked or expired.
        elif len(parts) == 6 and parts[0] == 'v2':
            _, user_id, version, expires, nonce, signature = parts
            version = int(version)
        else:
            return None
        payload = '.'.join(parts[:-1])
        expected = hmac.new(session_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected) or int(expires) < int(utcnow().timestamp()):
            return None
        with SessionLocal() as db:
            if db.get(RevokedSession, hash_api_key(token)):
                return None
            user = db.get(User, int(user_id))
            if not user or not user.active or user.auth_version != version:
                return None
            db.expunge(user)
            return user
    except Exception:
        return None


def current_user(request: Request) -> User:
    user = user_from_session(request.cookies.get('nova_session'))
    if not user:
        raise HTTPException(status_code=401, detail='Sign in required')
    return user


def revoke_session(token: str | None) -> None:
    if not token or not user_from_session(token):
        return
    parts = token.split('.')
    expires = int(parts[1] if len(parts) == 3 else parts[3])
    from sqlalchemy.exc import IntegrityError
    with SessionLocal() as db:
        db.add(RevokedSession(token_hash=hash_api_key(token), expires_at=datetime.fromtimestamp(expires, timezone.utc)))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()  # Two logout requests for the same session are both successful.


def make_state() -> str:
    return secrets.token_urlsafe(32)
