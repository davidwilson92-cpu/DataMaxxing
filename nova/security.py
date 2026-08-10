from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import timedelta
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, Request
from .db import SessionLocal, User, utcnow


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
    payload = f'{user_id}.{expires}'
    signature = hmac.new(session_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f'{payload}.{signature}'


def user_from_session(token: str | None) -> User | None:
    if not token:
        return None
    try:
        user_id, expires, signature = token.split('.', 2)
        payload = f'{user_id}.{expires}'
        expected = hmac.new(session_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected) or int(expires) < int(utcnow().timestamp()):
            return None
        with SessionLocal() as db:
            user = db.get(User, int(user_id))
            if not user or not user.active:
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


def make_state() -> str:
    return secrets.token_urlsafe(32)
