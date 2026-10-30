"""Bounded, read-only provider probes. A timeout is never treated as revocation."""
import json
import os
from concurrent.futures import ThreadPoolExecutor
import httpx
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, update
from .db import SocialConnection, get_db, utcnow
from .security import current_user
from .social import access_token, instagram_graph_base, json_meta
from .request_security import allowed_request

router = APIRouter()


def probe(platform, url, token, params):
    try:
        response = httpx.get(url, headers={'Authorization': 'Bearer ' + token}, params=params, timeout=5.0)
        payload = response.json()
        error = payload.get('error') or {}
        code = error.get('code') if isinstance(error, dict) else None
        if response.status_code == 401 or (platform in {'instagram', 'facebook'} and code in {102, 190}) or (platform == 'tiktok' and code in {'access_token_invalid', 'access_token_expired', 'scope_not_authorized'}):
            return 'reconnect'
        if response.status_code >= 400 or code not in {None, 'ok', 0}:
            return 'unavailable'
        valid = bool(payload.get('id')) if platform in {'instagram', 'facebook'} else bool((payload.get('data') or {}).get('id' if platform == 'x' else 'user'))
        return 'connected' if valid else 'unavailable'
    except (httpx.HTTPError, ValueError, TypeError, AttributeError):
        return 'unavailable'


@router.post('/api/connections/check')
def check(request: Request, db=Depends(get_db)):
    user = current_user(request)
    rows = db.scalars(select(SocialConnection).where(SocialConnection.user_id == user.id, SocialConnection.active.is_(True)).order_by(SocialConnection.id.desc()).limit(20)).all()
    now = utcnow().timestamp()
    pending = []
    may_check = allowed_request(f'connection-health:{user.id}:{db.info.get("brand_id",0)}', 1, 60)
    with ThreadPoolExecutor(max_workers=4) as pool:
        for row in rows:
            if not may_check: break
            meta = json_meta(row)
            checked = meta.get('health_checked_at', 0)
            if isinstance(checked, (int, float)) and 0 <= now - checked < 60:
                continue
            # A proven revoked grant stays blocked until explicitly reconnected.
            if meta.get('connection_health') == 'reconnect': continue
            try: token = access_token(row, db)
            except RuntimeError: continue  # Refresh failure alone isn't proof of revocation.
            meta = json_meta(row)
            if row.platform == 'instagram': url, params = f'{instagram_graph_base(row)}/{row.account_id}', {'fields':'id'}
            elif row.platform == 'facebook': url, params = f"https://graph.facebook.com/{os.environ.get('META_GRAPH_VERSION','v23.0')}/{row.account_id}", {'fields':'id'}
            elif row.platform == 'x': url, params = 'https://api.x.com/2/users/me', {}
            elif row.platform == 'tiktok': url, params = 'https://open.tiktokapis.com/v2/user/info/', {'fields':'open_id'}
            else: continue
            pending.append((row.id, row.encrypted_access_token, row.metadata_json, meta, pool.submit(probe, row.platform, url, token, params)))
        for cid, credential, original_meta, meta, future in pending:
            meta.update(connection_health=future.result(), health_checked_at=now)
            # Never overwrite a reconnect/unlink completed while the probe ran.
            db.execute(update(SocialConnection).where(SocialConnection.id == cid, SocialConnection.user_id == user.id,
                SocialConnection.active.is_(True), SocialConnection.encrypted_access_token == credential,
                SocialConnection.metadata_json == original_meta).values(metadata_json=json.dumps(meta)).execution_options(synchronize_session=False))
    db.commit(); db.expire_all()
    rows = db.scalars(select(SocialConnection).where(SocialConnection.user_id == user.id,
        SocialConnection.active.is_(True)).order_by(SocialConnection.id.desc()).limit(20)).all()
    return {'connections': [{'id': row.id, 'platform': row.platform,
        'status': json_meta(row).get('connection_health', 'unchecked')} for row in rows]}
