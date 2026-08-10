from __future__ import annotations

import os
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///./nova.db')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+psycopg://', 1)
elif DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg://', 1)
connect_args = {'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# Legacy X tables are intentionally retained so existing Custom GPTs keep working.
class Creator(Base):
    __tablename__ = 'creators'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    x_username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    api_key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    encrypted_x_api_key: Mapped[str] = mapped_column(Text)
    encrypted_x_api_secret: Mapped[str] = mapped_column(Text)
    encrypted_x_access_token: Mapped[str] = mapped_column(Text)
    encrypted_x_access_token_secret: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class OAuth2Connection(Base):
    __tablename__ = 'oauth2_connections'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey('creators.id'), unique=True, index=True)
    x_user_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    encrypted_access_token: Mapped[str] = mapped_column(Text)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scope: Mapped[str] = mapped_column(Text, default='tweet.read tweet.write users.read offline.access')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class PostLog(Base):
    __tablename__ = 'post_logs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey('creators.id'), index=True)
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30))
    x_post_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(Base):
    __tablename__ = 'nova_users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    subscription_status: Mapped[str] = mapped_column(String(40), default='none')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    preferences: Mapped['CreatorPreferences | None'] = relationship(back_populates='user', uselist=False, cascade='all,delete-orphan')
    social_connections: Mapped[list['SocialConnection']] = relationship(back_populates='user', cascade='all,delete-orphan')


class AuthIdentity(Base):
    __tablename__ = 'zova_auth_identities'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('nova_users.id'), index=True)
    provider: Mapped[str] = mapped_column(String(30), index=True)
    subject: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuthState(Base):
    __tablename__ = 'zova_auth_states'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(30), index=True)
    state_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    nonce_hash: Mapped[str] = mapped_column(String(64), index=True)
    intent: Mapped[str] = mapped_column(String(20), default='login')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class CreatorPreferences(Base):
    __tablename__ = 'nova_creator_preferences'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('nova_users.id'), unique=True, index=True)
    writing_tone: Mapped[str] = mapped_column(Text, default='')
    audience: Mapped[str] = mapped_column(Text, default='')
    topics: Mapped[str] = mapped_column(Text, default='')
    things_to_avoid: Mapped[str] = mapped_column(Text, default='')
    example_posts: Mapped[str] = mapped_column(Text, default='')
    preferred_post_length: Mapped[int] = mapped_column(Integer, default=220)
    timezone: Mapped[str] = mapped_column(String(80), default='Europe/London')
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    user: Mapped[User] = relationship(back_populates='preferences')


class SocialConnection(Base):
    __tablename__ = 'nova_social_connections'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('nova_users.id'), index=True)
    platform: Mapped[str] = mapped_column(String(30), index=True)  # x, instagram, facebook, tiktok
    account_id: Mapped[str] = mapped_column(String(160), index=True)
    username: Mapped[str] = mapped_column(String(160), default='')
    display_name: Mapped[str] = mapped_column(String(200), default='')
    encrypted_access_token: Mapped[str] = mapped_column(Text)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scope: Mapped[str] = mapped_column(Text, default='')
    metadata_json: Mapped[str] = mapped_column(Text, default='{}')
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    user: Mapped[User] = relationship(back_populates='social_connections')


class OAuthState(Base):
    __tablename__ = 'nova_oauth_states'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('nova_users.id'), index=True)
    platform: Mapped[str] = mapped_column(String(30), index=True)
    state_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    encrypted_code_verifier: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class Draft(Base):
    __tablename__ = 'nova_drafts'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('nova_users.id'), index=True)
    brief: Mapped[str] = mapped_column(Text, default='')
    instruction: Mapped[str] = mapped_column(Text, default='')
    platforms_json: Mapped[str] = mapped_column(Text, default='[]')
    variants_json: Mapped[str] = mapped_column(Text, default='{}')
    thread_length: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default='draft')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class MediaAsset(Base):
    __tablename__ = 'nova_media_assets'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('nova_users.id'), index=True)
    filename: Mapped[str] = mapped_column(String(260))
    mime_type: Mapped[str] = mapped_column(String(120))
    storage_key: Mapped[str] = mapped_column(Text)
    public_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ScheduledPost(Base):
    __tablename__ = 'nova_scheduled_posts'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('nova_users.id'), index=True)
    draft_id: Mapped[int | None] = mapped_column(ForeignKey('nova_drafts.id'), nullable=True, index=True)
    platform: Mapped[str] = mapped_column(String(30), index=True)
    connection_id: Mapped[int | None] = mapped_column(ForeignKey('nova_social_connections.id'), nullable=True)
    content_json: Mapped[str] = mapped_column(Text)
    media_asset_ids_json: Mapped[str] = mapped_column(Text, default='[]')
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(30), default='scheduled', index=True)
    platform_post_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    post_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Activity(Base):
    __tablename__ = 'nova_activity'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('nova_users.id'), index=True)
    draft_id: Mapped[int | None] = mapped_column(ForeignKey('nova_drafts.id'), nullable=True, index=True)
    platform: Mapped[str] = mapped_column(String(30), index=True)
    action: Mapped[str] = mapped_column(String(50), default='publish')
    status: Mapped[str] = mapped_column(String(30), index=True)
    text: Mapped[str] = mapped_column(Text, default='')
    platform_post_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    metrics_json: Mapped[str] = mapped_column(Text, default='{}')
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class UserCreatorLink(Base):
    __tablename__ = 'nova_user_creator_links'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('nova_users.id'), index=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey('creators.id'), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_preferences(db: Session, user_id: int) -> CreatorPreferences:
    pref = db.scalar(select(CreatorPreferences).where(CreatorPreferences.user_id == user_id))
    if pref is None:
        pref = CreatorPreferences(user_id=user_id)
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return pref
