"""Owner previews and short-lived, read-only media access for social providers."""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import select

from .db import MediaAsset, SessionLocal, User
from .security import user_from_session
from .storage import UPLOAD_DIR, local_path, valid_media_signature, verify_available

router = APIRouter()


@router.get('/media/raw/{filename}')
def local_media(filename: str, request: Request):
    if filename != filename.replace('\\', '/').split('/')[-1]:
        raise HTTPException(404, 'Media not found')
    candidate = UPLOAD_DIR / filename
    try:
        path = local_path(str(candidate))
    except (ValueError, OSError):
        raise HTTPException(404, 'Media not found') from None
    try:
        expires_at = int(request.query_params.get('expires', '0'))
        signed = valid_media_signature(filename, expires_at, request.query_params.get('signature', ''))
    except (ValueError, OverflowError):
        signed = False
    # No browser workspace filter: a signed provider fetch has no browser cookie.
    # Explicit owner/active-account checks apply before any bytes are returned.
    with SessionLocal() as db:
        row = db.scalar(select(MediaAsset).join(User, User.id == MediaAsset.user_id).where(
            MediaAsset.storage_key.in_([str(candidate), str(path)]), User.active.is_(True)))
        if not row:
            raise HTTPException(404, 'Media not found')
        if not signed:
            user = user_from_session(request.cookies.get('nova_session'))
            if not user or user.id != row.user_id:
                raise HTTPException(404, 'Media not found')
        try:
            verify_available(row.storage_key, row.size_bytes)
        except RuntimeError:
            raise HTTPException(404, 'Media not found') from None
        return FileResponse(path, media_type=row.mime_type, headers={
            'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'no-store',
            'Referrer-Policy': 'no-referrer',
            'Content-Security-Policy': "sandbox; default-src 'none'",
        })
