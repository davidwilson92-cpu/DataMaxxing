from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
from datetime import timedelta, timezone
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
META_SCOPES = "pages_show_list,pages_read_engagement,pages_manage_posts,instagram_basic,instagram_content_publish,instagram_manage_insights"
TIKTOK_SCOPES = "user.info.basic,video.list,video.publish"


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
        raise RuntimeError("Instagram publishing requires an image in this Nova build")
    token = access_token(conn, db)
    version = os.environ.get("META_GRAPH_VERSION", "v23.0")
    caption = posts[0]
    if link_url and link_url not in caption:
        caption = (caption + "\n\n" + link_url).strip()
    image_url = get_public_url(assets[0].storage_key, assets[0].public_url)
    create = httpx.post(f"https://graph.facebook.com/{version}/{conn.account_id}/media", data={"image_url": image_url, "caption": caption, "access_token": token}, timeout=45.0)
    if create.status_code >= 400:
        raise RuntimeError(f"Instagram media container failed: {create.text}")
    creation_id = str(create.json()["id"])
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


def publish_tiktok(db: Session, conn: SocialConnection, posts: list[str], assets: list[MediaAsset], link_url: str = "") -> dict[str, Any]:
    if not assets:
        raise RuntimeError("TikTok publishing requires visual media in this Nova build")
    token = access_token(conn, db)
    info = _tiktok_creator_info(token)
    options = info.get("privacy_level_options") or ["SELF_ONLY"]
    preferred = os.environ.get("TIKTOK_DEFAULT_PRIVACY", "PUBLIC_TO_EVERYONE")
    privacy = preferred if preferred in options else ("SELF_ONLY" if "SELF_ONLY" in options else options[0])
    urls = [get_public_url(a.storage_key, a.public_url) for a in assets[:10]]
    description = posts[0]
    if link_url and link_url not in description:
        description = (description + " " + link_url).strip()
    body = {
        "post_info": {"title": description[:90], "description": description[:4000], "privacy_level": privacy, "disable_comment": False, "auto_add_music": True},
        "source_info": {"source": "PULL_FROM_URL", "photo_cover_index": 0, "photo_images": urls},
        "post_mode": "DIRECT_POST",
        "media_type": "PHOTO",
    }
    r = httpx.post("https://open.tiktokapis.com/v2/post/publish/content/init/", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"}, json=body, timeout=45.0)
    if r.status_code >= 400 or (r.json().get("error") or {}).get("code") not in {None, "ok", 0}:
        raise RuntimeError(f"TikTok publish failed: {r.text}")
    publish_id = str(r.json()["data"]["publish_id"])
    return {"post_id": publish_id, "post_ids": [publish_id], "url": None, "pending": True, "privacy_level": privacy}


def resolve_tiktok_post(db: Session, conn: SocialConnection, publish_id: str) -> dict[str, Any]:
    token = access_token(conn, db)
    r = httpx.post("https://open.tiktokapis.com/v2/post/publish/status/fetch/", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json={"publish_id": publish_id}, timeout=30.0)
    if r.status_code >= 400:
        return {"status": "unknown"}
    data = r.json().get("data", {})
    post_ids = data.get("publicaly_available_post_id") or []
    return {"status": data.get("status", "unknown"), "public_ids": [str(x) for x in post_ids], "fail_reason": data.get("fail_reason")}


def publish_platform(db: Session, *, user_id: int, platform: str, posts: list[str], assets: list[MediaAsset], link_url: str = "") -> dict[str, Any]:
    conn = connection_for(db, user_id, platform)
    if platform == "x":
        return publish_x(db, conn, posts, assets, link_url)
    if platform == "facebook":
        return publish_facebook(db, conn, posts, assets, link_url)
    if platform == "instagram":
        return publish_instagram(db, conn, posts, assets, link_url)
    if platform == "tiktok":
        return publish_tiktok(db, conn, posts, assets, link_url)
    raise RuntimeError("Unsupported social platform")


# ---------- Analytics ----------

def _recent_ids(db: Session, user_id: int, platform: str, limit: int = 10) -> list[str]:
    rows = db.scalars(select(Activity).where(Activity.user_id == user_id, Activity.platform == platform, Activity.status.in_(["published", "pending"]), Activity.platform_post_id.is_not(None)).order_by(Activity.id.desc()).limit(limit)).all()
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
            result[platform] = {"connected": True, "account": conn.username or conn.display_name, **metrics}
        except Exception as exc:
            log.warning("%s analytics error: %s", platform, exc)
            result[platform] = {"connected": True, "account": conn.username or conn.display_name, "error": str(exc)}
    return result
