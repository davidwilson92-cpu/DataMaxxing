"""Owner-scoped downloads for finishing a post in the destination app."""
import os
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse

from .db import MediaAsset, get_db
from .security import current_user
from .storage import verify_available, _s3_client

router = APIRouter()


@router.get('/media/download/{asset_id}')
def download_media(asset_id: int, request: Request, db=Depends(get_db)):
    user = current_user(request)
    row = db.get(MediaAsset, asset_id)
    if not row or row.user_id != user.id or row.brand_id != db.info.get('brand_id', 0):
        raise HTTPException(404, 'Media not found')
    if not row.mime_type.startswith(('image/', 'video/')):
        raise HTTPException(400, 'This file cannot be exported as post media')
    try:
        verify_available(row.storage_key, row.size_bytes)
    except RuntimeError:
        raise HTTPException(404, 'This media is unavailable. Upload it again to continue.')
    name = Path(row.filename.replace('\\', '/')).name[:160] or 'Zova-media'
    if row.storage_key.startswith('nova/') and os.environ.get('S3_BUCKET'):
        try:
            stream = _s3_client().get_object(Bucket=os.environ['S3_BUCKET'], Key=row.storage_key)['Body']
        except Exception:
            raise HTTPException(503, 'The media could not be downloaded. Please try again.') from None
        def chunks():
            try:
                yield from stream.iter_chunks(chunk_size=65536)
            finally:
                stream.close()
        return StreamingResponse(chunks(), media_type=row.mime_type, headers={
            'Content-Disposition': "attachment; filename*=UTF-8''" + quote(name, safe=''),
            'Content-Length': str(row.size_bytes),
        })
    return FileResponse(row.storage_key, media_type=row.mime_type, filename=name)
