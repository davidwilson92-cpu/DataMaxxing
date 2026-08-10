from __future__ import annotations

import os
import pathlib
import uuid
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
    safe = pathlib.Path(filename or "upload.bin").name
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
    return pathlib.Path(storage_key).read_bytes()


def get_public_url(storage_key: str, existing_public_url: str | None = None, expires: int = 3600) -> str:
    if existing_public_url:
        return existing_public_url
    client = _s3_client()
    bucket = os.environ.get("S3_BUCKET")
    if client and bucket and storage_key.startswith("nova/"):
        return client.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": storage_key}, ExpiresIn=expires)
    raise RuntimeError("This media does not have a public URL. Configure S3 or another persistent public media store.")


def fetch_remote(url: str) -> bytes:
    r = httpx.get(url, timeout=30.0, follow_redirects=True)
    r.raise_for_status()
    return r.content
