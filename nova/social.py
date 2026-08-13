from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from typing import Any

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Activity, MediaAsset, SocialConnection, utcnow
from .security import decrypt, encrypt
from .storage import get_bytes, get_public_url

log = logging.getLogger("nova.social")

X_SCOPES = "tweet.read tweet.write users.read offline.access"
META_SCOPES = "pages_show_list,pages_read_engagement,business_management,instagram_basic,instagram_content_publish"
TIKTOK_SCOPES = "user.info.basic,user.info.stats,video.list,video.publish,video.upload"


def json_meta(conn: SocialConnection) -> dict[str, Any]:
    try:
        return json.loads(conn.metadata_json or "{}")
    except Exception:
        return {}


def save_meta(conn: SocialConnection, value: dict[str, Any]) -> None:
    conn.metadata_json = json.dumps(value, ensure_ascii=False)


def pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return verifier, challenge


def public_base() -> str:
    value = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    if not value:
        raise RuntimeError("PUBLIC_BASE_URL is not configured")
    return value


# ---------- X OAuth ----------

def x_authorize_url(state: str, verifier: str) -> str:
    client_id = os.environ.get("X_OAUTH2_CLIENT_ID")
    if not client_id:
        raise RuntimeError("X OAuth is not configured")
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": os.environ.get("X_OAUTH2_REDIRECT_URI") or f"{public_base()}/callback/x",
        "scope": X_SCOPES,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return "https://x.com/i/oauth2/authorize?" + urlencode(params)


def _x_token(data: dict[str, str]) -> dict[str, Any]:
    client_id = os.environ.get("X_OAUTH2_CLIENT_ID", "")
    client_secret = os.environ.get("X_OAUTH2_CLIENT_SECRET", "")
    auth = (client_id, client_secret) if client_secret else None
    if not client_secret:
        data["client_id"] = client_id
    r = httpx.post("https://api.x.com/2/oauth2/token", data=data, auth=auth, timeout=30.0)
    if r.status_code >= 400:
        raise RuntimeError(f"X OAuth token exchange failed: {r.text}")
    return r.json()


def x_exchange(code: str, verifier: str) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = _x_token({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": os.environ.get("X_OAUTH2_REDIRECT_URI") or f"{public_base()}/callback/x",
        "code_verifier": verifier,
    })
    r = httpx.get("https://api.x.com/2/users/me", headers={"Authorization": f"Bearer {payload['access_token']}"}, params={"user.fields": "name,username,profile_image_url"}, timeout=30.0)
    if r.status_code >= 400:
        raise RuntimeError(f"X user lookup failed: {r.text}")
    return payload, r.json()["data"]


def _x_refresh(conn: SocialConnection, db: Session) -> str:
    if not conn.encrypted_refresh_token:
        raise RuntimeError("X connection expired; reconnect X")
    payload = _x_token({"grant_type": "refresh_token", "refresh_token": decrypt(conn.encrypted_refresh_token)})
    conn.encrypted_access_token = encrypt(payload["access_token"])
    if payload.get("refresh_token"):
        conn.encrypted_refresh_token = encrypt(payload["refresh_token"])
    conn.expires_at = utcnow() + timedelta(seconds=max(int(payload.get("expires_in", 7200)) - 60, 60))
    conn.scope = payload.get("scope", conn.scope)
    db.commit()
    return payload["access_token"]


# ---------- Meta OAuth (Facebook + Instagram) ----------

def meta_authorize_url(state: str) -> str:
    app_id = os.environ.get("META_APP_ID")
    if not app_id:
        raise RuntimeError("Meta OAuth is not configured")
    version = os.environ.get("META_GRAPH_VERSION", "v23.0")
    redirect = os.environ.get("META_REDIRECT_URI") or f"{public_base()}/oauth/meta/callback"
    params = {"client_id": app_id, "redirect_uri": redirect, "state": state, "scope": META_SCOPES, "response_type": "code"}
    return f"https://www.facebook.com/{version}/dialog/oauth?{urlencode(params)}"


def meta_exchange(code: str) -> list[dict[str, Any]]:
    version = os.environ.get("META_GRAPH_VERSION", "v23.0")
    redirect = os.environ.get("META_REDIRECT_URI") or f"{public_base()}/oauth/meta/callback"
    params = {"client_id": os.environ.get("META_APP_ID"), "client_secret": os.environ.get("META_APP_SECRET"), "redirect_uri": redirect, "code": code}
    r = httpx.get(f"https://graph.facebook.com/{version}/oauth/access_token", params=params, timeout=30.0)
    if r.status_code >= 400:
        raise RuntimeError(f"Meta token exchange failed: {r.text}")
    user_token = r.json()["access_token"]
    # Prefer a long-lived user token when the app supports the exchange.
    long_r = httpx.get(
        f"https://graph.facebook.com/{version}/oauth/access_token",
        params={"grant_type": "fb_exchange_token", "client_id": os.environ.get("META_APP_ID"), "client_secret": os.environ.get("META_APP_SECRET"), "fb_exchange_token": user_token},
        timeout=30.0,
    )
    if long_r.status_code < 400 and long_r.json().get("access_token"):
        user_token = long_r.json()["access_token"]
    pages_r = httpx.get(
        f"https://graph.facebook.com/{version}/me/accounts",
        params={"fields": "name,access_token,tasks,instagram_business_account{id,username,name,profile_picture_url}", "access_token": user_token},
        timeout=30.0,
    )
    if pages_r.status_code >= 400:
        raise RuntimeError(f"Could not read managed Facebook Pages: {pages_r.text}")
    return pages_r.json().get("data", [])


# ---------- TikTok OAuth ----------

def tiktok_authorize_url(state: str) -> str:
    key = os.environ.get("TIKTOK_CLIENT_KEY")
    if not key:
        raise RuntimeError("TikTok OAuth is not configured")
    redirect = os.environ.get("TIKTOK_REDIRECT_URI") or f"{public_base()}/oauth/tiktok/callback"
    params = {"client_key": key, "scope": TIKTOK_SCOPES, "response_type": "code", "redirect_uri": redirect, "state": state}
    return "https://www.tiktok.com/v2/auth/authorize/?" + urlencode(params)


def _tiktok_token(data: dict[str, str]) -> dict[str, Any]:
    data = {**data, "client_key": os.environ.get("TIKTOK_CLIENT_KEY", ""), "client_secret": os.environ.get("TIKTOK_CLIENT_SECRET", "")}
    r = httpx.post("https://open.tiktokapis.com/v2/oauth/token/", data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30.0)
    if r.status_code >= 400:
        raise RuntimeError(f"TikTok token request failed: {r.text}")
    payload = r.json()
    if payload.get("error") and not payload.get("access_token"):
        raise RuntimeError(f"TikTok OAuth error: {payload}")
    return payload


def tiktok_exchange(code: str) -> tuple[dict[str, Any], dict[str, Any]]:
    redirect = os.environ.get("TIKTOK_REDIRECT_URI") or f"{public_base()}/oauth/tiktok/callback"
    payload = _tiktok_token({"grant_type": "authorization_code", "code": code, "redirect_uri": redirect})
    r = httpx.get(
        "https://open.tiktokapis.com/v2/user/info/",
        headers={"Authorization": f"Bearer {payload['access_token']}"},
        params={"fields": "open_id,union_id,avatar_url,display_name"},
        timeout=30.0,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"TikTok user lookup failed: {r.text}")
    return payload, r.json()["data"]["user"]


def _tiktok_refresh(conn: SocialConnection, db: Session) -> str:
    if not conn.encrypted_refresh_token:
        raise RuntimeError("TikTok connection expired; reconnect TikTok")
    payload = _tiktok_token({"grant_type": "refresh_token", "refresh_token": decrypt(conn.encrypted_refresh_token)})
    conn.encrypted_access_token = encrypt(payload["access_token"])
    if payload.get("refresh_token"):
        conn.encrypted_refresh_token = encrypt(payload["refresh_token"])
    conn.expires_at = utcnow() + timedelta(seconds=max(int(payload.get("expires_in", 86400)) - 120, 60))
    conn.scope = payload.get("scope", conn.scope)
    db.commit()
    return payload["access_token"]


def access_token(conn: SocialConnection, db: Session) -> str:
    expires = conn.expires_at
    if expires and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires and expires <= utcnow() + timedelta(minutes=2):
        if conn.platform == "x":
            return _x_refresh(conn, db)
        if conn.platform == "tiktok":
            return _tiktok_refresh(conn, db)
    return decrypt(conn.encrypted_access_token)


def connection_for(db: Session, user_id: int, platform: str) -> SocialConnection:
    conn = db.scalar(select(SocialConnection).where(SocialConnection.user_id == user_id, SocialConnection.platform == platform, SocialConnection.active.is_(True)).order_by(SocialConnection.id.desc()))
    if not conn:
        raise RuntimeError(f"Connect {platform.title()} before publishing")
    return conn


def upsert_connection(
    db: Session,
    *, user_id: int,
    platform: str,
    account_id: str,
    username: str,
    display_name: str,
    access: str,
    refresh: str | None = None,
    expires_in: int | None = None,
    scope: str = "",
    metadata: dict[str, Any] | None = None,
) -> SocialConnection:
    conn = db.scalar(select(SocialConnection).where(SocialConnection.user_id == user_id, SocialConnection.platform == platform, SocialConnection.account_id == account_id))
    if conn is None:
        conn = SocialConnection(user_id=user_id, platform=platform, account_id=account_id, username=username or "", display_name=display_name or "", encrypted_access_token=encrypt(access))
        db.add(conn)
    conn.username = username or conn.username
    conn.display_name = display_name or conn.display_name
    conn.encrypted_access_token = encrypt(access)
    if refresh:
        conn.encrypted_refresh_token = encrypt(refresh)
    if expires_in:
        conn.expires_at = utcnow() + timedelta(seconds=max(int(expires_in) - 60, 60))
    conn.scope = scope or conn.scope
    conn.active = True
    if metadata is not None:
        save_meta(conn, metadata)
    db.commit(); db.refresh(conn)
    return conn


# ---------- Publishing ----------

def _x_upload_image(token: str, asset: MediaAsset) -> str:
    data = base64.b64encode(get_bytes(asset.storage_key)).decode()
    r = httpx.post(
        "https://api.x.com/2/media/upload",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"media": data, "media_category": "tweet_image"},
        timeout=60.0,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"X media upload failed: {r.text}")
    return str(r.json()["data"]["id"])


def publish_x(db: Session, conn: SocialConnection, posts: list[str], assets: list[MediaAsset], link_url: str = "") -> dict[str, Any]:
    token = access_token(conn, db)
    media_ids = [_x_upload_image(token, a) for a in assets[:4]] if assets else []
    ids: list[str] = []
    urls: list[str] = []
    previous = None
    for i, text in enumerate(posts):
        final_text = text.strip()
        if link_url and i == 0 and link_url not in final_text:
            candidate = (final_text + " " + link_url).strip()
            if len(candidate) <= 280:
                final_text = candidate
        body: dict[str, Any] = {"text": final_text}
        if media_ids and i == 0:
            body["media"] = {"media_ids": media_ids}
        if previous:
            body["reply"] = {"in_reply_to_tweet_id": previous}
        r = httpx.post("https://api.x.com/2/tweets", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=body, timeout=30.0)
        if r.status_code == 401 and conn.encrypted_refresh_token:
            token = _x_refresh(conn, db)
            r = httpx.post("https://api.x.com/2/tweets", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=body, timeout=30.0)
        if r.status_code >= 400:
            raise RuntimeError(f"X publish failed: {r.text}")
        previous = str(r.json()["data"]["id"])
        ids.append(previous)
        urls.append(f"https://x.com/{conn.username or 'i'}/status/{previous}")
    return {"post_id": ids[0], "post_ids": ids, "url": urls[0], "urls": urls}


def publish_facebook(db: Session, conn: SocialConnection, posts: list[str], assets: list[MediaAsset], link_url: str = "") -> dict[str, Any]:
    token = access_token(conn, db)
    version = os.environ.get("META_GRAPH_VERSION", "v23.0")
    text = posts[0]
    if assets:
        image_url = get_public_url(assets[0].storage_key, assets[0].public_url)
        r = httpx.post(f"https://graph.facebook.com/{version}/{conn.account_id}/photos", data={"url": image_url, "caption": text, "access_token": token}, timeout=45.0)
    else:
        data = {"message": text, "access_token": token}
        if link_url:
            data["link"] = link_url
        r = httpx.post(f"https://graph.facebook.com/{version}/{conn.account_id}/feed", data=data, timeout=30.0)
    if r.status_code >= 400:
        raise RuntimeError(f"Facebook publish failed: {r.text}")
    post_id = str(r.json().get("post_id") or r.json().get("id"))
    return {"post_id": post_id, "post_ids": [post_id], "url": f"https://www.facebook.com/{post_id.replace('_', '/posts/')}"}


def publish_instagram(db: Session, conn: SocialConnection, posts: list[str], assets: list[MediaAsset], link_url: str = "") -> dict[str, Any]:
    if not assets:
        raise RuntimeError("Instagram publishing requires an image or video")
    token = access_token(conn, db)
    version = os.environ.get("META_GRAPH_VERSION", "v23.0")
    caption = posts[0]
    if link_url and link_url not in caption:
        caption = (caption + "\n\n" + link_url).strip()
    media_url = get_public_url(assets[0].storage_key, assets[0].public_url)
    is_video = assets[0].mime_type.startswith("video/")
    create_data = {"caption": caption, "access_token": token}
    if is_video:
        create_data.update({"media_type": "REELS", "video_url": media_url, "share_to_feed": "true"})
    else:
        create_data["image_url"] = media_url
    create = httpx.post(f"https://graph.facebook.com/{version}/{conn.account_id}/media", data=create_data, timeout=45.0)
    if create.status_code >= 400:
        raise RuntimeError(f"Instagram media container failed: {create.text}")
    creation_id = str(create.json()["id"])
    if is_video:
        for _ in range(15):
            status = httpx.get(f"https://graph.facebook.com/{version}/{creation_id}", params={"fields": "status_code,status", "access_token": token}, timeout=20.0)
            if status.status_code >= 400:
                raise RuntimeError(f"Instagram video processing failed: {status.text}")
            status_code = status.json().get("status_code")
            if status_code == "FINISHED":
                break
            if status_code in {"ERROR", "EXPIRED"}:
                raise RuntimeError(f"Instagram could not process this video: {status.json().get('status') or status_code}")
            time.sleep(2)
        else:
            raise RuntimeError("Instagram is still processing the video. Try publishing again shortly.")
    publish = httpx.post(f"https://graph.facebook.com/{version}/{conn.account_id}/media_publish", data={"creation_id": creation_id, "access_token": token}, timeout=45.0)
    if publish.status_code >= 400:
        raise RuntimeError(f"Instagram publish failed: {publish.text}")
    post_id = str(publish.json()["id"])
    # Resolve permalink when available.
    detail = httpx.get(f"https://graph.facebook.com/{version}/{post_id}", params={"fields": "permalink", "access_token": token}, timeout=20.0)
    url = detail.json().get("permalink") if detail.status_code < 400 else None
    return {"post_id": post_id, "post_ids": [post_id], "url": url or "https://www.instagram.com/"}


def _tiktok_creator_info(token: str) -> dict[str, Any]:
    r = httpx.post("https://open.tiktokapis.com/v2/post/publish/creator_info/query/", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json={}, timeout=30.0)
    if r.status_code >= 400:
        raise RuntimeError(f"TikTok creator info failed: {r.text}")
    return r.json().get("data", {})


def publishing_context(db: Session, user_id: int, platform: str) -> dict[str, Any]:
    conn = connection_for(db, user_id, platform)
    result = {"platform": platform, "username": conn.username, "display_name": conn.display_name or conn.username or conn.account_id}
    if platform == "tiktok":
        info = _tiktok_creator_info(access_token(conn, db))
        result.update({
            "username": info.get("creator_username") or result["username"],
            "display_name": info.get("creator_nickname") or result["display_name"],
            "avatar_url": info.get("creator_avatar_url") or "",
            "privacy_options": info.get("privacy_level_options") or ["SELF_ONLY"],
            "max_video_duration_sec": int(info.get("max_video_post_duration_sec") or 0),
            "comment_disabled": bool(info.get("comment_disabled")),
            "duet_disabled": bool(info.get("duet_disabled")),
            "stitch_disabled": bool(info.get("stitch_disabled")),
        })
    return result


def publish_tiktok(db: Session, conn: SocialConnection, posts: list[str], assets: list[MediaAsset], link_url: str = "", options: dict[str, Any] | None = None) -> dict[str, Any]:
    if not assets:
        raise RuntimeError("TikTok publishing requires visual media in this Zova build")
    token = access_token(conn, db)
    upload_as_draft = os.environ.get("TIKTOK_SEND_TO_INBOX", "false").lower() in {"1", "true", "yes"}
    info = _tiktok_creator_info(token)
    settings = options or {}
    privacy_options = info.get("privacy_level_options") or ["SELF_ONLY"]
    forced_privacy = str(os.environ.get("TIKTOK_DEFAULT_PRIVACY") or "").strip()
    requested_privacy = forced_privacy or str(settings.get("privacy_level") or "")
    if requested_privacy not in privacy_options:
        raise RuntimeError("The selected TikTok privacy setting is no longer available. Review the post again.")
    privacy = requested_privacy
    is_video = assets[0].mime_type.startswith("video/")
    if is_video:
        duration = float(settings.get("video_duration_sec") or 0)
        maximum = float(info.get("max_video_post_duration_sec") or 0)
        if duration <= 0:
            raise RuntimeError("TikTok video duration could not be verified. Remove and re-add the video.")
        if maximum and duration > maximum:
            raise RuntimeError(f"This TikTok account accepts videos up to {int(maximum)} seconds.")
    description = posts[0]
    if link_url and link_url not in description:
        description = (description + " " + link_url).strip()
    if is_video:
        video = get_bytes(assets[0].storage_key)
        video_size = len(video)
        if not video_size:
            raise RuntimeError("The selected TikTok video is empty. Remove and re-add it.")
        # TikTok accepts chunks between 5 MiB and 64 MiB (the final chunk may
        # be smaller), with no more than 1,000 chunks per upload.
        min_chunk = 5 * 1024 * 1024
        max_chunk = 64 * 1024 * 1024
        chunk_size = min(max_chunk, max(min_chunk, (video_size + 999) // 1000))
        chunk_size = min(chunk_size, video_size)
        total_chunks = (video_size + chunk_size - 1) // chunk_size
        source_info = {"source": "FILE_UPLOAD", "video_size": video_size, "chunk_size": chunk_size, "total_chunk_count": total_chunks}
        if upload_as_draft:
            body = {"source_info": source_info}
            endpoint = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
        else:
            body = {
                "post_info": {"title": description[:2200], "privacy_level": privacy, "disable_duet": not bool(settings.get("allow_duet")), "disable_comment": not bool(settings.get("allow_comment")), "disable_stitch": not bool(settings.get("allow_stitch")), "video_cover_timestamp_ms": 1000, "brand_content_toggle": bool(settings.get("brand_content")), "brand_organic_toggle": bool(settings.get("your_brand"))},
                "source_info": source_info,
            }
            endpoint = "https://open.tiktokapis.com/v2/post/publish/video/init/"
    else:
        urls = [get_public_url(a.storage_key, a.public_url) for a in assets[:10]]
        body = {
        "post_info": {"title": description[:90], "description": description[:4000], "privacy_level": privacy, "disable_comment": not bool(settings.get("allow_comment")), "auto_add_music": True, "brand_content_toggle": bool(settings.get("brand_content")), "brand_organic_toggle": bool(settings.get("your_brand"))},
        "source_info": {"source": "PULL_FROM_URL", "photo_cover_index": 0, "photo_images": urls},
        "post_mode": "DIRECT_POST",
        "media_type": "PHOTO",
        }
        endpoint = "https://open.tiktokapis.com/v2/post/publish/content/init/"
    r = httpx.post(endpoint, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"}, json=body, timeout=45.0)
    if r.status_code >= 400 or (r.json().get("error") or {}).get("code") not in {None, "ok", 0}:
        raise RuntimeError(f"TikTok publish failed: {r.text}")
    response_data = r.json()["data"]
    publish_id = str(response_data["publish_id"])
    if is_video:
        upload_url = response_data.get("upload_url")
        if not upload_url:
            raise RuntimeError("TikTok did not provide a video upload URL")
        for index in range(total_chunks):
            start = index * chunk_size
            chunk = video[start : start + chunk_size]
            end = start + len(chunk) - 1
            upload = httpx.put(
                upload_url,
                content=chunk,
                headers={
                    "Content-Type": assets[0].mime_type or "video/mp4",
                    "Content-Length": str(len(chunk)),
                    "Content-Range": f"bytes {start}-{end}/{video_size}",
                },
                timeout=120.0,
            )
            if upload.status_code >= 400:
                raise RuntimeError(f"TikTok video upload failed ({upload.status_code}): {upload.text}")
    return {"post_id": publish_id, "post_ids": [publish_id], "url": None, "pending": True, "privacy_level": privacy, "requires_tiktok_completion": bool(is_video and upload_as_draft)}


def resolve_tiktok_post(db: Session, conn: SocialConnection, publish_id: str) -> dict[str, Any]:
    token = access_token(conn, db)
    r = httpx.post("https://open.tiktokapis.com/v2/post/publish/status/fetch/", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json={"publish_id": publish_id}, timeout=30.0)
    if r.status_code >= 400:
        return {"status": "unknown"}
    data = r.json().get("data", {})
    post_ids = data.get("publicaly_available_post_id") or []
    return {"status": data.get("status", "unknown"), "public_ids": [str(x) for x in post_ids], "fail_reason": data.get("fail_reason")}


def publish_platform(db: Session, *, user_id: int, platform: str, posts: list[str], assets: list[MediaAsset], link_url: str = "", options: dict[str, Any] | None = None) -> dict[str, Any]:
    conn = connection_for(db, user_id, platform)
    if platform == "x":
        return publish_x(db, conn, posts, assets, link_url)
    if platform == "facebook":
        return publish_facebook(db, conn, posts, assets, link_url)
    if platform == "instagram":
        return publish_instagram(db, conn, posts, assets, link_url)
    if platform == "tiktok":
        return publish_tiktok(db, conn, posts, assets, link_url, options)
    raise RuntimeError("Unsupported social platform")


# ---------- Analytics ----------

def _recent_ids(db: Session, user_id: int, platform: str, limit: int = 10) -> list[str]:
    cutoff = utcnow() - timedelta(days=7)
    rows = db.scalars(select(Activity).where(Activity.user_id == user_id, Activity.platform == platform, Activity.status.in_(["published", "pending"]), Activity.platform_post_id.is_not(None), Activity.created_at >= cutoff).order_by(Activity.id.desc()).limit(limit)).all()
    return [str(r.platform_post_id) for r in rows if r.platform_post_id]


def analytics_x(db: Session, conn: SocialConnection, ids: list[str]) -> dict[str, Any]:
    if not ids:
        return {"posts": 0, "impressions": 0, "likes": 0, "replies": 0, "reposts": 0}
    token = access_token(conn, db)
    r = httpx.get("https://api.x.com/2/tweets", headers={"Authorization": f"Bearer {token}"}, params={"ids": ",".join(ids[:100]), "tweet.fields": "public_metrics,non_public_metrics,organic_metrics"}, timeout=30.0)
    if r.status_code >= 400:
        r = httpx.get("https://api.x.com/2/tweets", headers={"Authorization": f"Bearer {token}"}, params={"ids": ",".join(ids[:100]), "tweet.fields": "public_metrics"}, timeout=30.0)
    if r.status_code >= 400:
        raise RuntimeError("X analytics unavailable")
    out = {"posts": 0, "impressions": 0, "likes": 0, "replies": 0, "reposts": 0}
    for item in r.json().get("data", []):
        pub = item.get("public_metrics") or {}
        private = item.get("non_public_metrics") or item.get("organic_metrics") or {}
        out["posts"] += 1
        out["likes"] += int(pub.get("like_count", 0))
        out["replies"] += int(pub.get("reply_count", 0))
        out["reposts"] += int(pub.get("retweet_count", 0))
        out["impressions"] += int(private.get("impression_count", pub.get("impression_count", 0)) or 0)
    return out


def analytics_instagram(db: Session, conn: SocialConnection, ids: list[str]) -> dict[str, Any]:
    if not ids:
        return {"posts": 0, "likes": 0, "comments": 0}
    token = access_token(conn, db); version = os.environ.get("META_GRAPH_VERSION", "v23.0")
    out = {"posts": 0, "likes": 0, "comments": 0}
    for pid in ids[:10]:
        r = httpx.get(f"https://graph.facebook.com/{version}/{pid}", params={"fields": "like_count,comments_count", "access_token": token}, timeout=20.0)
        if r.status_code < 400:
            data = r.json(); out["posts"] += 1; out["likes"] += int(data.get("like_count", 0)); out["comments"] += int(data.get("comments_count", 0))
    return out


def analytics_facebook(db: Session, conn: SocialConnection, ids: list[str]) -> dict[str, Any]:
    if not ids:
        return {"posts": 0, "reactions": 0, "comments": 0}
    token = access_token(conn, db); version = os.environ.get("META_GRAPH_VERSION", "v23.0")
    out = {"posts": 0, "reactions": 0, "comments": 0}
    for pid in ids[:10]:
        r = httpx.get(f"https://graph.facebook.com/{version}/{pid}", params={"fields": "reactions.limit(0).summary(true),comments.limit(0).summary(true)", "access_token": token}, timeout=20.0)
        if r.status_code < 400:
            d = r.json(); out["posts"] += 1; out["reactions"] += int(((d.get("reactions") or {}).get("summary") or {}).get("total_count", 0)); out["comments"] += int(((d.get("comments") or {}).get("summary") or {}).get("total_count", 0))
    return out


def analytics_tiktok(db: Session, conn: SocialConnection, ids: list[str]) -> dict[str, Any]:
    # Activities may initially hold publish_ids; resolve them to public post IDs first.
    public_ids: list[str] = []
    for value in ids[:10]:
        if value.startswith("p_"):
            state = resolve_tiktok_post(db, conn, value)
            public_ids.extend(state.get("public_ids", []))
        else:
            public_ids.append(value)
    if not public_ids:
        return {"posts": 0, "views": 0, "likes": 0, "comments": 0, "shares": 0, "note": "Metrics appear after TikTok makes a public post ID available."}
    token = access_token(conn, db)
    r = httpx.post("https://open.tiktokapis.com/v2/video/query/", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, params={"fields": "id,share_url,like_count,comment_count,share_count,view_count"}, json={"filters": {"video_ids": public_ids[:20]}}, timeout=30.0)
    if r.status_code >= 400:
        raise RuntimeError("TikTok analytics unavailable")
    out = {"posts": 0, "views": 0, "likes": 0, "comments": 0, "shares": 0}
    for item in r.json().get("data", {}).get("videos", []):
        out["posts"] += 1; out["views"] += int(item.get("view_count", 0)); out["likes"] += int(item.get("like_count", 0)); out["comments"] += int(item.get("comment_count", 0)); out["shares"] += int(item.get("share_count", 0))
    return out


def follower_count(db: Session, conn: SocialConnection) -> int:
    token = access_token(conn, db)
    if conn.platform == "x":
        r = httpx.get(f"https://api.x.com/2/users/{conn.account_id}", headers={"Authorization": f"Bearer {token}"}, params={"user.fields": "public_metrics"}, timeout=20.0)
        return int(((r.json().get("data") or {}).get("public_metrics") or {}).get("followers_count", 0)) if r.status_code < 400 else 0
    if conn.platform in {"instagram", "facebook"}:
        version = os.environ.get("META_GRAPH_VERSION", "v23.0")
        fields = "followers_count" if conn.platform == "instagram" else "followers_count,fan_count"
        r = httpx.get(f"https://graph.facebook.com/{version}/{conn.account_id}", params={"fields": fields, "access_token": token}, timeout=20.0)
        data = r.json() if r.status_code < 400 else {}
        return int(data.get("followers_count", data.get("fan_count", 0)) or 0)
    if conn.platform == "tiktok":
        r = httpx.get("https://open.tiktokapis.com/v2/user/info/", headers={"Authorization": f"Bearer {token}"}, params={"fields": "follower_count"}, timeout=20.0)
        return int((((r.json().get("data") or {}).get("user") or {}).get("follower_count", 0))) if r.status_code < 400 else 0
    return 0


def analytics_for_user(db: Session, user_id: int) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for platform in ["x", "instagram", "facebook", "tiktok"]:
        try:
            conn = connection_for(db, user_id, platform)
        except RuntimeError:
            result[platform] = {"connected": False}
            continue
        ids = _recent_ids(db, user_id, platform)
        try:
            if platform == "x": metrics = analytics_x(db, conn, ids)
            elif platform == "instagram": metrics = analytics_instagram(db, conn, ids)
            elif platform == "facebook": metrics = analytics_facebook(db, conn, ids)
            else: metrics = analytics_tiktok(db, conn, ids)
            result[platform] = {"connected": True, "account": conn.username or conn.display_name, "followers": follower_count(db, conn), **metrics}
        except Exception as exc:
            log.warning("%s analytics error: %s", platform, exc)
            result[platform] = {"connected": True, "account": conn.username or conn.display_name, "error": str(exc)}
    totals = {"impressions": 0, "likes": 0, "comments": 0, "shares": 0, "followers": 0, "posts": 0}
    for platform, values in result.items():
        if not values.get("connected"): continue
        totals["impressions"] += int(values.get("impressions", values.get("views", 0)) or 0)
        totals["likes"] += int(values.get("likes", values.get("reactions", 0)) or 0)
        totals["comments"] += int(values.get("comments", values.get("replies", 0)) or 0)
        totals["shares"] += int(values.get("shares", values.get("reposts", 0)) or 0)
        totals["followers"] += int(values.get("followers", 0) or 0)
        totals["posts"] += int(values.get("posts", 0) or 0)
    result["_summary"] = totals
    return result


def recent_posts_for_user(db: Session, user_id: int, limit: int = 12) -> dict[str, Any]:
    posts: list[dict[str, Any]] = []
    unavailable: list[str] = []
    for platform in ["x", "instagram", "facebook", "tiktok"]:
        try:
            conn = connection_for(db, user_id, platform); token = access_token(conn, db)
            if platform == "x":
                response = httpx.get(f"https://api.x.com/2/users/{conn.account_id}/tweets", headers={"Authorization": f"Bearer {token}"}, params={"max_results": 10, "exclude": "retweets,replies", "tweet.fields": "created_at,public_metrics,attachments", "expansions": "attachments.media_keys", "media.fields": "url,preview_image_url,type"}, timeout=30.0)
                if response.status_code >= 400: raise RuntimeError("X feed unavailable")
                media = {item.get("media_key"): item for item in response.json().get("includes", {}).get("media", [])}
                for item in response.json().get("data", []):
                    metrics = item.get("public_metrics") or {}; keys = (item.get("attachments") or {}).get("media_keys") or []; visual = media.get(keys[0], {}) if keys else {}
                    posts.append({"platform":"x","id":str(item.get("id")),"text":item.get("text") or "","created_at":item.get("created_at") or "","url":f"https://x.com/{conn.username or 'i'}/status/{item.get('id')}","image_url":visual.get("preview_image_url") or visual.get("url") or "","likes":metrics.get("like_count",0),"comments":metrics.get("reply_count",0),"shares":metrics.get("retweet_count",0),"views":metrics.get("impression_count",0)})
            elif platform == "instagram":
                version = os.environ.get("META_GRAPH_VERSION", "v23.0")
                response = httpx.get(f"https://graph.facebook.com/{version}/{conn.account_id}/media", params={"fields":"id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,like_count,comments_count","limit":10,"access_token":token}, timeout=30.0)
                if response.status_code >= 400: raise RuntimeError("Instagram feed unavailable")
                for item in response.json().get("data", []):posts.append({"platform":"instagram","id":str(item.get("id")),"text":item.get("caption") or "","created_at":item.get("timestamp") or "","url":item.get("permalink") or "","image_url":item.get("thumbnail_url") or item.get("media_url") or "","likes":item.get("like_count",0),"comments":item.get("comments_count",0),"shares":0,"views":0})
            elif platform == "facebook":
                version = os.environ.get("META_GRAPH_VERSION", "v23.0")
                response = httpx.get(f"https://graph.facebook.com/{version}/{conn.account_id}/posts", params={"fields":"id,message,created_time,permalink_url,full_picture,reactions.limit(0).summary(true),comments.limit(0).summary(true),shares","limit":10,"access_token":token}, timeout=30.0)
                if response.status_code >= 400: raise RuntimeError("Facebook feed unavailable")
                for item in response.json().get("data", []):posts.append({"platform":"facebook","id":str(item.get("id")),"text":item.get("message") or "","created_at":item.get("created_time") or "","url":item.get("permalink_url") or "","image_url":item.get("full_picture") or "","likes":((item.get("reactions") or {}).get("summary") or {}).get("total_count",0),"comments":((item.get("comments") or {}).get("summary") or {}).get("total_count",0),"shares":(item.get("shares") or {}).get("count",0),"views":0})
            else:
                response = httpx.post("https://open.tiktokapis.com/v2/video/list/", headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"}, params={"fields":"id,title,video_description,cover_image_url,share_url,create_time,like_count,comment_count,share_count,view_count"}, json={"max_count":10}, timeout=30.0)
                if response.status_code >= 400: raise RuntimeError("TikTok feed unavailable")
                for item in response.json().get("data", {}).get("videos", []):
                    created = datetime.fromtimestamp(int(item.get("create_time") or 0),tz=timezone.utc).isoformat() if item.get("create_time") else ""
                    posts.append({"platform":"tiktok","id":str(item.get("id")),"text":item.get("video_description") or item.get("title") or "","created_at":created,"url":item.get("share_url") or "","image_url":item.get("cover_image_url") or "","likes":item.get("like_count",0),"comments":item.get("comment_count",0),"shares":item.get("share_count",0),"views":item.get("view_count",0)})
        except RuntimeError:
            continue
        except Exception as exc:
            log.warning("%s recent posts error: %s", platform, exc); unavailable.append(platform)
    posts.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return {"posts":posts[:max(1,min(limit,30))],"unavailable":unavailable}


def recent_content_for_connection(db: Session, conn: SocialConnection, limit: int = 20) -> list[str]:
    """Read recent creator-authored content for voice learning."""
    token = access_token(conn, db)
    if conn.platform == "x":
        r = httpx.get(f"https://api.x.com/2/users/{conn.account_id}/tweets", headers={"Authorization": f"Bearer {token}"}, params={"max_results": max(5, min(limit, 100)), "tweet.fields": "created_at", "exclude": "retweets,replies"}, timeout=30.0)
        if r.status_code >= 400: raise RuntimeError("X recent posts are unavailable")
        return [str(x.get("text", "")).strip() for x in r.json().get("data", []) if x.get("text")]
    if conn.platform in {"instagram", "facebook"}:
        version = os.environ.get("META_GRAPH_VERSION", "v23.0")
        edge = "media" if conn.platform == "instagram" else "posts"
        fields = "caption,timestamp" if conn.platform == "instagram" else "message,created_time"
        r = httpx.get(f"https://graph.facebook.com/{version}/{conn.account_id}/{edge}", params={"fields": fields, "limit": limit, "access_token": token}, timeout=30.0)
        if r.status_code >= 400: raise RuntimeError(f"{conn.platform.title()} recent posts are unavailable")
        key = "caption" if conn.platform == "instagram" else "message"
        return [str(x.get(key, "")).strip() for x in r.json().get("data", []) if x.get(key)]
    if conn.platform == "tiktok":
        r = httpx.post("https://open.tiktokapis.com/v2/video/list/", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, params={"fields": "id,title,video_description,create_time"}, json={"max_count": min(limit, 20)}, timeout=30.0)
        if r.status_code >= 400: raise RuntimeError("TikTok recent posts are unavailable")
        videos = (r.json().get("data") or {}).get("videos", [])
        return [str(x.get("video_description") or x.get("title") or "").strip() for x in videos if x.get("video_description") or x.get("title")]
    return []


def recent_content_for_user(db: Session, user_id: int) -> list[str]:
    rows = db.scalars(select(SocialConnection).where(SocialConnection.user_id == user_id, SocialConnection.active.is_(True))).all()
    content: list[str] = []
    for conn in rows:
        try: content.extend(recent_content_for_connection(db, conn))
        except Exception as exc: log.warning("%s voice scan failed: %s", conn.platform, exc)
    return content[:60]
