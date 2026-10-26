from __future__ import annotations

import os
import pathlib
import uuid
import hashlib
import hmac
import time
from dataclasses import dataclass
from urllib.parse import urlsplit, urlencode

UPLOAD_DIR = pathlib.Path(os.environ.get("UPLOAD_DIR", "./uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class StoredObject:
    storage_key: str
    public_url: str | None


def _s3_client():
    if not os.environ.get("S3_BUCKET"):
        return None
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("boto3 is required for S3 uploads") from exc
    return boto3.client(
        "s3",
        region_name=os.environ.get("AWS_REGION") or None,
        endpoint_url=os.environ.get("S3_ENDPOINT_URL") or None,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID") or None,
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY") or None,
    )


def save_bytes(data: bytes, filename: str, content_type: str, base_url: str) -> StoredObject:
    extensions={"image/jpeg":".jpg","image/png":".png","image/gif":".gif","image/webp":".webp","video/mp4":".mp4","video/quicktime":".mov","video/webm":".webm"}
    safe = "media" + extensions.get(content_type,".bin")
    key = f"nova/{uuid.uuid4().hex}-{safe}"
    client = _s3_client()
    bucket = os.environ.get("S3_BUCKET")
    if client and bucket:
        extra = {"ContentType": content_type}
        client.put_object(Bucket=bucket, Key=key, Body=data, **extra)
        public_base = os.environ.get("S3_PUBLIC_BASE_URL", "").rstrip("/")
        public_url = f"{public_base}/{key}" if public_base else None
        return StoredObject(key, public_url)
    path = UPLOAD_DIR / key.replace("/", "_")
    path.write_bytes(data)
    return StoredObject(str(path), f"{base_url.rstrip('/')}/media/raw/{path.name}")


def get_bytes(storage_key: str) -> bytes:
    client = _s3_client()
    bucket = os.environ.get("S3_BUCKET")
    if client and bucket and storage_key.startswith("nova/"):
        response = client.get_object(Bucket=bucket, Key=storage_key)
        return response["Body"].read()
    return local_path(storage_key).read_bytes()


def local_path(storage_key: str) -> pathlib.Path:
    """Only regular files in the managed upload directory may be read."""
    path = pathlib.Path(storage_key)
    resolved = path.resolve(strict=True)
    if path.is_symlink() or not resolved.is_relative_to(UPLOAD_DIR.resolve()) or not resolved.is_file():
        raise ValueError('Invalid upload path')
    return resolved


def media_signature(filename: str, expires_at: int) -> str:
    from .security import session_secret
    payload = f'zova-media-v1:{filename}:{expires_at}'
    return hmac.new(session_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()


def valid_media_signature(filename: str, expires_at: int, signature: str) -> bool:
    now = int(time.time())
    return (len(signature) == 64 and signature.isascii()
            and now < expires_at <= now + 3600
            and hmac.compare_digest(media_signature(filename, expires_at), signature))


def verify_available(storage_key: str, size_bytes: int) -> None:
    """Check the stored object before review/dispatch, without sending to a provider."""
    try:
        if storage_key.startswith('nova/') and os.environ.get('S3_BUCKET'):
            size = _s3_client().head_object(Bucket=os.environ['S3_BUCKET'], Key=storage_key)['ContentLength']
        else:
            resolved = local_path(storage_key)
            # Opening catches unreadable files, without loading a large video.
            with resolved.open('rb') as stream:
                size = os.fstat(stream.fileno()).st_size
        if size != size_bytes or size <= 0:
            raise ValueError('Upload size mismatch')
    except Exception:
        raise RuntimeError('An attachment is unavailable. Remove it and upload it again before reviewing.') from None


def get_public_url(storage_key: str, existing_public_url: str | None = None, expires: int = 3600) -> str:
    base = os.environ.get('PUBLIC_BASE_URL', '').rstrip('/')
    existing = urlsplit(existing_public_url or '')
    configured = urlsplit(base)
    if (existing_public_url and base and existing.scheme == configured.scheme
            and existing.netloc == configured.netloc and existing.path.startswith('/media/raw/')):
        path = local_path(storage_key)
        expires_at = int(time.time()) + min(3600, max(1, expires))
        query = urlencode({'expires': expires_at, 'signature': media_signature(path.name, expires_at)})
        return f'{base}/media/raw/{path.name}?{query}'
    if existing_public_url:
        return existing_public_url
    client = _s3_client()
    bucket = os.environ.get("S3_BUCKET")
    if client and bucket and storage_key.startswith("nova/"):
        return client.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": storage_key}, ExpiresIn=expires)
    raise RuntimeError("This media does not have a public URL. Configure S3 or another persistent public media store.")
