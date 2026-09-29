from __future__ import annotations

import os
import pathlib
import uuid
import hashlib
import hmac
import time
from urllib.parse import quote
from dataclasses import dataclass

import httpx

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
        return StoredObject(key, None)
    path = UPLOAD_DIR / key.replace("/", "_")
    path.write_bytes(data)
    return StoredObject(str(path), None)


def get_bytes(storage_key: str) -> bytes:
    client = _s3_client()
    bucket = os.environ.get("S3_BUCKET")
    if client and bucket and storage_key.startswith("nova/"):
        response = client.get_object(Bucket=bucket, Key=storage_key)
        return response["Body"].read()
    return pathlib.Path(storage_key).read_bytes()


def get_public_url(storage_key: str, existing_public_url: str | None = None, expires: int = 3600) -> str:
    expires=max(1,min(int(expires),3600))
    client = _s3_client()
    bucket = os.environ.get("S3_BUCKET")
    if client and bucket and storage_key.startswith("nova/"):
        return client.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": storage_key}, ExpiresIn=expires)
    path=pathlib.Path(storage_key).resolve()
    if path.parent!=UPLOAD_DIR.resolve() or not path.is_file():
        raise RuntimeError('Media is unavailable in the configured private storage.')
    deadline=int(time.time())+expires
    signature=media_signature(path.name,deadline)
    base=os.environ.get('PUBLIC_BASE_URL','').rstrip('/')
    return f'{base}/media/raw/{quote(path.name)}?expires={deadline}&signature={signature}'


def media_signature(filename, deadline):
    from .security import session_secret
    return hmac.new(session_secret().encode(),f'media-download:{filename}:{deadline}'.encode(),hashlib.sha256).hexdigest()


def valid_media_signature(filename, deadline, signature):
    try:
        expires=int(deadline)
        now=int(time.time())
        return (now < expires <= now+3600 and
                hmac.compare_digest(signature,media_signature(filename,expires)))
    except (TypeError,ValueError):
        return False
