#!/usr/bin/env python3
"""Multi-tenant X posting API with self-service OAuth 2.0 onboarding."""

from __future__ import annotations

import base64
import hashlib
import hmac
import html
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated
from urllib.parse import urlencode

import httpx
import tweepy
from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

log = logging.getLogger("x_poster_api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

MAX_LEN = 280
X_AUTHORIZE_URL = "https://x.com/i/oauth2/authorize"
X_TOKEN_URL = "https://api.x.com/2/oauth2/token"
X_ME_URL = "https://api.x.com/2/users/me"
X_POST_URL = "https://api.x.com/2/tweets"
OAUTH_SCOPES = "tweet.read tweet.write users.read offline.access"

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./x_poster.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Creator(Base):
    __tablename__ = "creators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    x_username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    api_key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    encrypted_x_api_key: Mapped[str] = mapped_column(Text)
    encrypted_x_api_secret: Mapped[str] = mapped_column(Text)
    encrypted_x_access_token: Mapped[str] = mapped_column(Text)
    encrypted_x_access_token_secret: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    posts: Mapped[list["PostLog"]] = relationship(back_populates="creator")
    oauth2_connection: Mapped["OAuth2Connection | None"] = relationship(back_populates="creator", uselist=False)


class OAuth2Connection(Base):
    __tablename__ = "oauth2_connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("creators.id"), unique=True, index=True)
    x_user_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    encrypted_access_token: Mapped[str] = mapped_column(Text)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scope: Mapped[str] = mapped_column(Text, default=OAUTH_SCOPES)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    creator: Mapped[Creator] = relationship(back_populates="oauth2_connection")


class OAuthState(Base):
    __tablename__ = "oauth_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    state_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    encrypted_code_verifier: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class PostLog(Base):
    __tablename__ = "post_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("creators.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30))
    x_post_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    creator: Mapped[Creator] = relationship(back_populates="posts")


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Multi-Tenant X Posting API",
    version="3.0.0",
    description="Preview and publish explicitly approved posts, with self-service X OAuth onboarding.",
)


class PostRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_LEN)
    approved: bool = False

    @field_validator("text")
    @classmethod
    def clean_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Post text cannot be blank")
        return value


class PreviewResponse(BaseModel):
    text: str
    character_count: int
    valid: bool
    account: str


class PostResponse(BaseModel):
    success: bool
    post_id: str
    url: str
    text: str
    account: str


class CreatorCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    x_username: str = Field(..., min_length=1, max_length=50)
    x_api_key: str = Field(..., min_length=1)
    x_api_secret: str = Field(..., min_length=1)
    x_access_token: str = Field(..., min_length=1)
    x_access_token_secret: str = Field(..., min_length=1)

    @field_validator("x_username")
    @classmethod
    def clean_username(cls, value: str) -> str:
        return value.strip().lstrip("@")


class CreatorCreateResponse(BaseModel):
    id: int
    name: str
    x_username: str
    creator_api_key: str
    warning: str = "Copy this key now. Only its hash is stored and it cannot be recovered later."


class CreatorSummary(BaseModel):
    id: int
    name: str
    x_username: str
    active: bool
    created_at: datetime
    connection_type: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def get_fernet() -> Fernet:
    key = os.environ.get("CREDENTIAL_ENCRYPTION_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="Credential encryption is not configured")
    try:
        return Fernet(key.encode("utf-8"))
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="Credential encryption key is invalid") from exc


def encrypt_secret(value: str) -> str:
    return get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    try:
        return get_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise HTTPException(status_code=500, detail="Stored credentials could not be decrypted") from exc


def bearer_token(authorization: str | None) -> str:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


def require_creator(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
) -> Creator:
    token = bearer_token(authorization)
    creator = db.scalar(select(Creator).where(Creator.api_key_hash == hash_key(token), Creator.active.is_(True)))
    if creator is None:
        raise HTTPException(status_code=401, detail="Invalid or inactive creator API key")
    return creator


def require_admin(authorization: Annotated[str | None, Header()] = None) -> None:
    token = bearer_token(authorization)
    expected = os.environ.get("ADMIN_API_KEY")
    if not expected or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="Invalid admin API key")


def oauth_redirect_uri() -> str:
    explicit = os.environ.get("X_OAUTH2_REDIRECT_URI")
    if explicit:
        return explicit.rstrip("/")
    base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    if not base:
        raise HTTPException(status_code=500, detail="PUBLIC_BASE_URL is not configured")
    return f"{base}/callback/x"


def oauth_client_id() -> str:
    value = os.environ.get("X_OAUTH2_CLIENT_ID")
    if not value:
        raise HTTPException(status_code=500, detail="X OAuth Client ID is not configured")
    return value


def pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def token_request(data: dict[str, str]) -> httpx.Response:
    client_id = oauth_client_id()
    client_secret = os.environ.get("X_OAUTH2_CLIENT_SECRET")
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    auth = (client_id, client_secret) if client_secret else None
    if not client_secret:
        data["client_id"] = client_id
    return httpx.post(X_TOKEN_URL, data=data, headers=headers, auth=auth, timeout=30.0)


def refresh_oauth_token(connection: OAuth2Connection, db: Session) -> str:
    if not connection.encrypted_refresh_token:
        raise HTTPException(status_code=401, detail="X connection expired; reconnect the X account")

    response = token_request(
        {
            "grant_type": "refresh_token",
            "refresh_token": decrypt_secret(connection.encrypted_refresh_token),
        }
    )
    if response.status_code >= 400:
        log.error("X refresh failed: %s", response.text)
        raise HTTPException(status_code=502, detail="X token refresh failed; reconnect the X account")

    payload = response.json()
    connection.encrypted_access_token = encrypt_secret(payload["access_token"])
    if payload.get("refresh_token"):
        connection.encrypted_refresh_token = encrypt_secret(payload["refresh_token"])
    expires_in = int(payload.get("expires_in", 7200))
    connection.expires_at = utcnow() + timedelta(seconds=max(expires_in - 60, 60))
    connection.scope = payload.get("scope", connection.scope)
    db.commit()
    return payload["access_token"]


def oauth_access_token(connection: OAuth2Connection, db: Session) -> str:
    expires_at = connection.expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at and expires_at <= utcnow() + timedelta(minutes=2):
        return refresh_oauth_token(connection, db)
    return decrypt_secret(connection.encrypted_access_token)


def x_credentials_for(creator: Creator) -> dict[str, str]:
    return {
        "consumer_key": decrypt_secret(creator.encrypted_x_api_key),
        "consumer_secret": decrypt_secret(creator.encrypted_x_api_secret),
        "access_token": decrypt_secret(creator.encrypted_x_access_token),
        "access_token_secret": decrypt_secret(creator.encrypted_x_access_token_secret),
    }


def page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>
body{{font-family:Inter,system-ui,-apple-system,sans-serif;background:#f5f7fb;color:#101828;margin:0;padding:24px}}
.card{{max-width:620px;margin:8vh auto;background:white;border:1px solid #e4e7ec;border-radius:18px;padding:32px;box-shadow:0 12px 36px rgba(16,24,40,.08)}}
h1{{font-size:30px;margin:0 0 12px}}p{{line-height:1.55;color:#475467}}.button{{display:inline-block;background:#101828;color:white;text-decoration:none;padding:13px 20px;border-radius:10px;font-weight:700;margin-top:12px}}
.code{{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;background:#f2f4f7;border:1px solid #e4e7ec;border-radius:10px;padding:14px;overflow-wrap:anywhere;color:#101828}}
.warn{{background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;padding:12px;color:#9a3412}}small{{color:#667085}}
</style></head><body><main class="card">{body}</main></body></html>"""
    )


@app.on_event("startup")
def bootstrap_existing_account() -> None:
    required = [
        "BOOTSTRAP_CREATOR_API_KEY",
        "X_API_KEY",
        "X_API_SECRET",
        "X_ACCESS_TOKEN",
        "X_ACCESS_TOKEN_SECRET",
    ]
    if not all(os.environ.get(name) for name in required):
        return

    username = os.environ.get("X_USERNAME", "DataMaxxing").lstrip("@")
    with SessionLocal() as db:
        existing = db.scalar(select(Creator).where(Creator.x_username == username))
        if existing:
            return
        creator = Creator(
            name=os.environ.get("BOOTSTRAP_CREATOR_NAME", username),
            x_username=username,
            api_key_hash=hash_key(os.environ["BOOTSTRAP_CREATOR_API_KEY"]),
            encrypted_x_api_key=encrypt_secret(os.environ["X_API_KEY"]),
            encrypted_x_api_secret=encrypt_secret(os.environ["X_API_SECRET"]),
            encrypted_x_access_token=encrypt_secret(os.environ["X_ACCESS_TOKEN"]),
            encrypted_x_access_token_secret=encrypt_secret(os.environ["X_ACCESS_TOKEN_SECRET"]),
        )
        db.add(creator)
        db.commit()
        log.info("Bootstrapped creator @%s", username)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "3.0.0"}


@app.get("/privacy", response_class=HTMLResponse)
def privacy() -> HTMLResponse:
    return page(
        "Privacy Policy",
        """<h1>Privacy Policy</h1>
<p>This private integration receives only the content explicitly submitted for previewing or publishing to X and the account information returned when a user chooses to connect X.</p>
<p>It uses that information solely to authenticate the connected account, publish requested content and maintain an operational audit log. X authorization tokens are encrypted at rest. Credentials and submitted content are not sold or used for advertising.</p>
<p>Infrastructure providers may retain standard technical logs. Users can revoke the application's access from their X account settings.</p>""",
    )


@app.get("/connect/x", response_class=HTMLResponse)
def connect_x_page() -> HTMLResponse:
    return page(
        "Connect X",
        """<h1>Connect your X account</h1>
<p>Authorise this service to identify your account and publish posts only when you explicitly approve them in your connected ChatGPT assistant.</p>
<p>Requested permissions: read basic account details, publish posts and remain connected until you revoke access.</p>
<a class="button" href="/connect/x/start">Connect X</a>
<p><small>You will be redirected to X to review and approve access.</small></p>""",
    )


@app.get("/connect/x/start")
def connect_x_start(db: Session = Depends(get_db)) -> RedirectResponse:
    verifier, challenge = pkce_pair()
    state = secrets.token_urlsafe(32)
    db.add(
        OAuthState(
            state_hash=hash_key(state),
            encrypted_code_verifier=encrypt_secret(verifier),
        )
    )
    db.commit()

    params = {
        "response_type": "code",
        "client_id": oauth_client_id(),
        "redirect_uri": oauth_redirect_uri(),
        "scope": OAUTH_SCOPES,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return RedirectResponse(f"{X_AUTHORIZE_URL}?{urlencode(params)}", status_code=302)


@app.get("/callback/x", response_class=HTMLResponse)
def connect_x_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    if error:
        return page("X connection cancelled", f"<h1>Connection not completed</h1><p>{html.escape(error_description or error)}</p>")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing OAuth code or state")

    state_row = db.scalar(select(OAuthState).where(OAuthState.state_hash == hash_key(state), OAuthState.used.is_(False)))
    if state_row is None:
        raise HTTPException(status_code=400, detail="Invalid or already-used OAuth state")
    created_at = state_row.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    if created_at < utcnow() - timedelta(minutes=10):
        raise HTTPException(status_code=400, detail="OAuth request expired; start again")

    verifier = decrypt_secret(state_row.encrypted_code_verifier)
    response = token_request(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": oauth_redirect_uri(),
            "code_verifier": verifier,
        }
    )
    if response.status_code >= 400:
        log.error("X token exchange failed: %s", response.text)
        raise HTTPException(status_code=502, detail="X token exchange failed")
    token_payload = response.json()
    access_token = token_payload["access_token"]

    me_response = httpx.get(X_ME_URL, headers={"Authorization": f"Bearer {access_token}"}, timeout=30.0)
    if me_response.status_code >= 400:
        log.error("X users/me failed: %s", me_response.text)
        raise HTTPException(status_code=502, detail="Could not retrieve the connected X account")
    user = me_response.json()["data"]
    username = user["username"].lstrip("@")
    x_user_id = str(user["id"])

    existing_connection = db.scalar(select(OAuth2Connection).where(OAuth2Connection.x_user_id == x_user_id))
    existing_creator = db.scalar(select(Creator).where(Creator.x_username == username))
    if existing_connection or existing_creator:
        state_row.used = True
        db.commit()
        return page(
            "Already connected",
            f"<h1>@{html.escape(username)} is already connected</h1><p>This account already exists in the service. No new key was created.</p>",
        )

    raw_key = "xcp_" + secrets.token_urlsafe(32)
    placeholder = encrypt_secret("oauth2-managed")
    creator = Creator(
        name=user.get("name") or username,
        x_username=username,
        api_key_hash=hash_key(raw_key),
        encrypted_x_api_key=placeholder,
        encrypted_x_api_secret=placeholder,
        encrypted_x_access_token=placeholder,
        encrypted_x_access_token_secret=placeholder,
    )
    db.add(creator)
    db.flush()

    expires_in = int(token_payload.get("expires_in", 7200))
    connection = OAuth2Connection(
        creator_id=creator.id,
        x_user_id=x_user_id,
        encrypted_access_token=encrypt_secret(access_token),
        encrypted_refresh_token=encrypt_secret(token_payload["refresh_token"]) if token_payload.get("refresh_token") else None,
        expires_at=utcnow() + timedelta(seconds=max(expires_in - 60, 60)),
        scope=token_payload.get("scope", OAUTH_SCOPES),
    )
    db.add(connection)
    state_row.used = True
    db.commit()

    return page(
        "X connected",
        f"""<h1>@{html.escape(username)} is connected</h1>
<p>Your creator key is shown once below. Copy it now and store it securely. It will be used as the Bearer API key in the creator's private Custom GPT Action.</p>
<div class="code">{html.escape(raw_key)}</div>
<p class="warn"><strong>Do not share this key.</strong> Only its hash is retained, so the original cannot be recovered later.</p>""",
    )


@app.post("/x/preview", response_model=PreviewResponse)
def preview_post(request: PostRequest, creator: Creator = Depends(require_creator)) -> PreviewResponse:
    return PreviewResponse(
        text=request.text,
        character_count=len(request.text),
        valid=len(request.text) <= MAX_LEN,
        account=f"@{creator.x_username}",
    )


@app.post("/x/post", response_model=PostResponse)
def publish_post(
    request: PostRequest,
    creator: Creator = Depends(require_creator),
    db: Session = Depends(get_db),
) -> PostResponse:
    if request.approved is not True:
        raise HTTPException(status_code=400, detail="Publication requires approved=true after explicit user confirmation")

    log_row = PostLog(creator_id=creator.id, text=request.text, status="attempted")
    db.add(log_row)
    db.commit()
    db.refresh(log_row)

    try:
        connection = db.scalar(select(OAuth2Connection).where(OAuth2Connection.creator_id == creator.id))
        if connection:
            access_token = oauth_access_token(connection, db)
            response = httpx.post(
                X_POST_URL,
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                json={"text": request.text},
                timeout=30.0,
            )
            if response.status_code == 401 and connection.encrypted_refresh_token:
                access_token = refresh_oauth_token(connection, db)
                response = httpx.post(
                    X_POST_URL,
                    headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                    json={"text": request.text},
                    timeout=30.0,
                )
            if response.status_code >= 400:
                raise RuntimeError(f"X API returned {response.status_code}: {response.text}")
            post_id = str(response.json()["data"]["id"])
        else:
            client = tweepy.Client(**x_credentials_for(creator))
            response = client.create_tweet(text=request.text)
            post_id = str(response.data["id"])

        log_row.status = "published"
        log_row.x_post_id = post_id
        db.commit()
    except (tweepy.TweepyException, httpx.HTTPError, RuntimeError) as exc:
        log_row.status = "failed"
        log_row.error = str(exc)
        db.commit()
        log.exception("X rejected post for @%s", creator.x_username)
        raise HTTPException(status_code=502, detail=f"X API error: {exc}") from exc

    url = f"https://x.com/{creator.x_username}/status/{post_id}"
    return PostResponse(
        success=True,
        post_id=post_id,
        url=url,
        text=request.text,
        account=f"@{creator.x_username}",
    )


@app.post("/admin/creators", response_model=CreatorCreateResponse, dependencies=[Depends(require_admin)])
def create_creator(request: CreatorCreateRequest, db: Session = Depends(get_db)) -> CreatorCreateResponse:
    if db.scalar(select(Creator).where(Creator.x_username == request.x_username)):
        raise HTTPException(status_code=409, detail="That X username is already registered")

    raw_key = "xcp_" + secrets.token_urlsafe(32)
    creator = Creator(
        name=request.name,
        x_username=request.x_username,
        api_key_hash=hash_key(raw_key),
        encrypted_x_api_key=encrypt_secret(request.x_api_key),
        encrypted_x_api_secret=encrypt_secret(request.x_api_secret),
        encrypted_x_access_token=encrypt_secret(request.x_access_token),
        encrypted_x_access_token_secret=encrypt_secret(request.x_access_token_secret),
    )
    db.add(creator)
    db.commit()
    db.refresh(creator)
    return CreatorCreateResponse(id=creator.id, name=creator.name, x_username=creator.x_username, creator_api_key=raw_key)


@app.get("/admin/creators", response_model=list[CreatorSummary], dependencies=[Depends(require_admin)])
def list_creators(db: Session = Depends(get_db)) -> list[CreatorSummary]:
    creators = db.scalars(select(Creator).order_by(Creator.id)).all()
    oauth_creator_ids = set(db.scalars(select(OAuth2Connection.creator_id)).all())
    return [
        CreatorSummary(
            id=c.id,
            name=c.name,
            x_username=c.x_username,
            active=c.active,
            created_at=c.created_at,
            connection_type="oauth2" if c.id in oauth_creator_ids else "oauth1_manual",
        )
        for c in creators
    ]


@app.post("/admin/creators/{creator_id}/deactivate", dependencies=[Depends(require_admin)])
def deactivate_creator(creator_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    creator = db.get(Creator, creator_id)
    if creator is None:
        raise HTTPException(status_code=404, detail="Creator not found")
    creator.active = False
    db.commit()
    return {"success": True, "creator_id": creator_id, "active": False}
