"""Parallel provider reads with immutable inputs and current grant validation."""
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from contextvars import copy_context
import hashlib
import time
from types import SimpleNamespace

from sqlalchemy import func, select
from . import read_cache
from .db import Activity, SocialConnection, User, utcnow
from .security import decrypt

# Independent of the request and publishing executors. No worker holds a Session.
_pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix='social-read')
_fields = ('id', 'account_id', 'username', 'display_name', 'scope', 'expires_at',
           'encrypted_access_token', 'metadata_json')


def signature(conn):
    from .social import json_meta
    meta = json_meta(conn)
    values = (conn.id, conn.account_id, conn.scope, str(conn.expires_at),
              bool(conn.expires_at and conn.expires_at.replace(tzinfo=None) <= utcnow().replace(tzinfo=None)),
              conn.encrypted_access_token, meta.get('auth_provider'), meta.get('connection_health') == 'reconnect')
    return hashlib.sha256(repr(values).encode()).hexdigest()


def read_accounts(db, uid, *, kind, quick=False, refresh=False):
    from .social import access_token, connection_for, follower_count, json_meta, _recent_posts
    brand = db.info.get('brand_id', 0) if db is not None else 0
    activity = db.scalar(select(func.max(Activity.updated_at)).where(
        Activity.user_id == uid, Activity.brand_id == brand)) if db is not None else None
    deadline = time.monotonic() + (8 if quick else 35)
    pending = []
    unavailable = []
    for platform in ('x', 'instagram', 'facebook', 'tiktok'):
        conn = None
        try:
            conn = connection_for(db, uid, platform)
            if quick:
                if json_meta(conn).get('connection_health') == 'reconnect' or (
                    conn.expires_at and conn.expires_at.replace(tzinfo=None) <= utcnow().replace(tzinfo=None)
                ):
                    raise RuntimeError('Feed needs a later refresh')
                token = decrypt(conn.encrypted_access_token)
            else:
                token = access_token(conn, db)
            snapshot = SimpleNamespace(**{field: getattr(conn, field, None) for field in _fields}, platform=platform)
            stamp = signature(snapshot)
            key = (uid, brand, kind, platform, stamp, str(activity))

            def read(snapshot=snapshot, platform=platform, token=token):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError()
                if kind == 'feed':
                    value = _recent_posts(snapshot, platform, token, min(2 if quick else 30, remaining))
                else:
                    # Renewal already ran on the request's own Session.
                    snapshot.expires_at = None
                    value = follower_count(None, snapshot)
                return {'value': value, 'fetched_at': utcnow().isoformat(),
                        'account': snapshot.username or snapshot.display_name}

            def cached_read(key=key, reader=read):
                return reader() if db is None else read_cache.load(key, reader, refresh=refresh)

            pending.append((platform, snapshot.id, stamp, _pool.submit(copy_context().run, cached_read)))
        except RuntimeError:
            if conn is not None:
                unavailable.append(platform)
        except Exception:
            # Preserve partial results if one provider's renewal or credential
            # cannot be read. No credential/error payload reaches logs or clients.
            unavailable.append(platform)
    observations = {}
    for platform, cid, stamp, future in pending:
        try:
            observations[platform] = future.result(timeout=max(0.01, deadline-time.monotonic()))
        except Exception:
            future.cancel()
            unavailable.append(platform)
    if db is not None and pending:
        # A disconnect, account replacement, revocation or rotation during a slow
        # provider call invalidates even a successful response or old cache hit.
        current = {row.platform: row for row in db.execute(select(
            SocialConnection.platform, *[getattr(SocialConnection, field) for field in _fields]
        ).join(User, User.id == SocialConnection.user_id).where(
            SocialConnection.user_id == uid, SocialConnection.brand_id == brand,
            SocialConnection.active.is_(True), User.active.is_(True)).order_by(SocialConnection.id))}
        for platform, cid, stamp, _ in pending:
            if platform not in current or current[platform].id != cid or signature(current[platform]) != stamp:
                observations.pop(platform, None)
                if platform not in unavailable:
                    unavailable.append(platform)
    return observations, unavailable
