#!/usr/bin/env python3
"""Multi-tenant X posting API for Custom GPT Actions."""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timezone
from typing import Annotated

import tweepy
from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

log = logging.getLogger("x_poster_api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

MAX_LEN = 280
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

    posts: Mapped[list[PostLog]] = relationship(back_populates="creator")


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
    version="2.0.0",
    description="Preview and publish explicitly approved posts for the creator identified by the bearer key.",
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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
        raise HTTPException(status_code=500, detail="Stored creator credentials could not be decrypted") from exc


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


def x_credentials_for(creator: Creator) -> dict[str, str]:
    return {
        "consumer_key": decrypt_secret(creator.encrypted_x_api_key),
        "consumer_secret": decrypt_secret(creator.encrypted_x_api_secret),
        "access_token": decrypt_secret(creator.encrypted_x_access_token),
        "access_token_secret": decrypt_secret(creator.encrypted_x_access_token_secret),
    }


@app.on_event("startup")
def bootstrap_existing_account() -> None:
    """Optionally migrate the original single-account environment variables into the database once."""
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
    return {"status": "ok", "version": "2.0.0"}


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

    creds = x_credentials_for(creator)
    client = tweepy.Client(**creds)
    try:
        response = client.create_tweet(text=request.text)
        post_id = str(response.data["id"])
        log_row.status = "published"
        log_row.x_post_id = post_id
        db.commit()
    except tweepy.TweepyException as exc:
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
    return [
        CreatorSummary(
            id=c.id,
            name=c.name,
            x_username=c.x_username,
            active=c.active,
            created_at=c.created_at,
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
