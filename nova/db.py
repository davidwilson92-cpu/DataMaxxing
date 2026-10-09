from __future__ import annotations

import os
from datetime import datetime, timezone
from fastapi import Request
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, CheckConstraint, event, inspect, func, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///./nova.db')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+psycopg://', 1)
elif DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg://', 1)
connect_args = {'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}
pool_options = {} if DATABASE_URL.startswith('sqlite') else {
    'pool_size': max(1, min(20, int(os.environ.get('DB_POOL_SIZE', '5')))),
    'max_overflow': 0,
    'pool_timeout': 10,
    'pool_recycle': 1800,
}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, hide_parameters=True, connect_args=connect_args, **pool_options)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class CanonicalWorkspace:
    # SQLite's compatible legacy inserts are filled by an AFTER INSERT guard.
    # PostgreSQL enforces NOT NULL during the offline reference migration.
    workspace_id: Mapped[str] = mapped_column(ForeignKey('zova_workspaces.id'), nullable=True)


class BrandScoped(CanonicalWorkspace):
    brand_id: Mapped[int] = mapped_column(Integer, default=0, server_default='0', index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('nova_users.id'), index=True)


class Brand(Base):
    __tablename__ = 'zova_brands'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('nova_users.id'), index=True)
    name: Mapped[str] = mapped_column(String(100))


class TenantWorkspace(Base):
    __tablename__ = 'zova_workspaces'
    __table_args__ = (UniqueConstraint('owner_user_id','legacy_brand_id'), CheckConstraint('legacy_brand_id >= 0',name='workspace_nonnegative_brand'))
    id: Mapped[str] = mapped_column(String(36),primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey('nova_users.id'))
    legacy_brand_id: Mapped[int] = mapped_column(Integer)


class WorkspaceMembership(Base):
    __tablename__ = 'zova_workspace_memberships'
    __table_args__ = (CheckConstraint("role IN ('owner','admin','publisher','creator','analyst','viewer')",name='membership_known_role'), CheckConstraint('revision >= 1',name='membership_positive_revision'))
    workspace_id: Mapped[str] = mapped_column(ForeignKey('zova_workspaces.id'),primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('nova_users.id'),primary_key=True)
    role: Mapped[str] = mapped_column(String(20),default='viewer')
    active: Mapped[bool] = mapped_column(Boolean,default=False)
    revision: Mapped[int] = mapped_column(Integer,default=1)


class BrandVoice(BrandScoped, Base):
    __tablename__ = 'zova_brand_voices'
    __table_args__ = (UniqueConstraint('user_id', 'brand_id'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    writing_tone: Mapped[str] = mapped_column(Text, default='')
    audience: Mapped[str] = mapped_column(Text, default='')
    topics: Mapped[str] = mapped_column(Text, default='')
    things_to_avoid: Mapped[str] = mapped_column(Text, default='')
    example_posts: Mapped[str] = mapped_column(Text, default='')
    preferred_post_length: Mapped[int] = mapped_column(Integer, default=220)
    timezone: Mapped[str] = mapped_column(String(80), default='Europe/London')
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class UsageEntry(Base):
    __tablename__ = 'zova_usage_entries'
    key: Mapped[str] = mapped_column(String(180), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('nova_users.id'), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    period: Mapped[str] = mapped_column(String(7), index=True)
    amount: Mapped[int] = mapped_column(Integer, default=1)
    state: Mapped[str] = mapped_column(String(20), default='reserved')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


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


class LegacyPublication(Base):
    __tablename__ = 'zova_legacy_publications'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey('creators.id'), index=True)
    text: Mapped[str] = mapped_column(Text)
    account: Mapped[str] = mapped_column(String(50))
    authority_digest: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30), default='queued', index=True)
    result_json: Mapped[str] = mapped_column(Text, default='{}')
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
    display_name: Mapped[str] = mapped_column(String(160), default='')
    default_brand_name: Mapped[str] = mapped_column(String(100), default='My brand', server_default='My brand')
    country_code: Mapped[str] = mapped_column(String(2), default='')
    password_hash: Mapped[str] = mapped_column(Text)
    auth_version: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    subscription_status: Mapped[str] = mapped_column(String(40), default='none')
    terms_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    marketing_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    marketing_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    preferences: Mapped['CreatorPreferences | None'] = relationship(back_populates='user', uselist=False, cascade='all,delete-orphan')
    social_connections: Mapped[list['SocialConnection']] = relationship(back_populates='user', cascade='all,delete-orphan')


class RevokedSession(Base):
    __tablename__ = 'zova_revoked_sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class RecoveryToken(Base):
    __tablename__ = 'zova_recovery_tokens'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('nova_users.id'), index=True)
    auth_version: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class RequestLimit(Base):
    __tablename__ = 'zova_request_limits'
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    reset_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class DeletionRequest(Base):
    __tablename__ = 'zova_deletion_requests'
    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    subject_hash: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(30), default='received')
    scope: Mapped[str] = mapped_column(Text, default='Platform connection credentials')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


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


class SocialConnection(BrandScoped, Base):
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


class OAuthState(CanonicalWorkspace, Base):
    __tablename__ = 'nova_oauth_states'
    brand_id: Mapped[int] = mapped_column(Integer, default=0, server_default='0')
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('nova_users.id'), index=True)
    platform: Mapped[str] = mapped_column(String(30), index=True)
    state_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    encrypted_code_verifier: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class Draft(BrandScoped, Base):
    __tablename__ = 'nova_drafts'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('nova_users.id'), index=True)
    brief: Mapped[str] = mapped_column(Text, default='')
    title: Mapped[str] = mapped_column(String(120), default='', server_default='')
    instruction: Mapped[str] = mapped_column(Text, default='')
    platforms_json: Mapped[str] = mapped_column(Text, default='[]')
    variants_json: Mapped[str] = mapped_column(Text, default='{}')
    workspace_json: Mapped[str] = mapped_column(Text, default='{}')
    revision: Mapped[int] = mapped_column(Integer, default=0)
    thread_length: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default='draft')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class PublishReview(BrandScoped, Base):
    __tablename__ = 'zova_publish_reviews'
    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('nova_users.id'), index=True)
    draft_id: Mapped[int] = mapped_column(ForeignKey('nova_drafts.id'), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    payload_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default='review')
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Publication(BrandScoped, Base):
    __tablename__ = 'zova_publications'
    __table_args__ = (UniqueConstraint('draft_id','platform',name='uq_publication_draft_platform'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('nova_users.id'), index=True)
    draft_id: Mapped[int] = mapped_column(ForeignKey('nova_drafts.id'), index=True)
    platform: Mapped[str] = mapped_column(String(30))
    connection_id: Mapped[int] = mapped_column(ForeignKey('nova_social_connections.id'))
    review_code: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30), default='queued',index=True)
    result_json: Mapped[str] = mapped_column(Text,default='{}')
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow)


class MediaAsset(BrandScoped, Base):
    __tablename__ = 'nova_media_assets'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('nova_users.id'), index=True)
    analysis_json: Mapped[str] = mapped_column(Text, default='{}')
    filename: Mapped[str] = mapped_column(String(260))
    mime_type: Mapped[str] = mapped_column(String(120))
    storage_key: Mapped[str] = mapped_column(Text)
    public_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ScheduledPost(BrandScoped, Base):
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


class Activity(BrandScoped, Base):
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


class BillingAccount(Base):
    __tablename__ = 'zova_billing_accounts'
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('nova_users.id'), index=True)
    mode: Mapped[str] = mapped_column(String(10))
    customer_id: Mapped[str | None] = mapped_column(String(120), nullable=True, unique=True)
    subscription_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default='none')
    price_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    period_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checkout_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    checkout_started: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checkout_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    checkout_session: Mapped[str | None] = mapped_column(String(150), nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=0)


class BillingEvent(Base):
    __tablename__ = 'zova_billing_events'
    event_id: Mapped[str] = mapped_column(String(150), primary_key=True)
    mode: Mapped[str] = mapped_column(String(10))
    event_type: Mapped[str] = mapped_column(String(100))
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AICall(Base):
    __tablename__ = 'zova_ai_calls'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey('nova_users.id'), nullable=True, index=True)
    model: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(30))
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cached_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_gbp: Mapped[str | None] = mapped_column(String(40), nullable=True)
    rate_date: Mapped[str | None] = mapped_column(String(30), nullable=True)
    rate_snapshot: Mapped[str] = mapped_column(Text, default='{}')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ProductEvent(Base):
    __tablename__ = 'zova_product_events'
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('nova_users.id'), index=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class MailDelivery(Base):
    __tablename__ = 'zova_mail_deliveries'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class EmailVerification(Base):
    __tablename__ = 'zova_email_verifications'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('nova_users.id'), index=True)
    email: Mapped[str] = mapped_column(String(320))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class PendingConnection(CanonicalWorkspace, Base):
    __tablename__ = 'zova_pending_connections'
    code_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('nova_users.id'), index=True)
    brand_id: Mapped[int] = mapped_column(Integer, default=0)
    auth_version: Mapped[int] = mapped_column(Integer)
    platform: Mapped[str] = mapped_column(String(30))
    encrypted_payload: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class PerformanceSnapshot(BrandScoped, Base):
    __tablename__ = 'zova_performance_snapshots'
    __table_args__ = (UniqueConstraint('user_id', 'brand_id', name='uq_performance_snapshot_brand'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload_json: Mapped[str] = mapped_column(Text, default='{}')
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Strategy(BrandScoped, Base):
    __tablename__ = 'zova_strategies'
    __table_args__ = (UniqueConstraint('user_id', 'brand_id'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    confirmed_json: Mapped[str] = mapped_column(Text, default='{}')
    proposal_json: Mapped[str] = mapped_column(Text, default='{}')
    revision: Mapped[int] = mapped_column(Integer, default=0)


class StrategyAction(BrandScoped, Base):
    __tablename__ = 'zova_strategy_actions'
    __table_args__ = (UniqueConstraint('user_id', 'brand_id', 'action_key'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action_key: Mapped[str] = mapped_column(String(80))
    strategy_revision: Mapped[int] = mapped_column(Integer)
    payload_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default='open')
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    feedback: Mapped[str] = mapped_column(String(80), default='')
    draft_id: Mapped[int | None] = mapped_column(ForeignKey('nova_drafts.id'), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ContentSeries(BrandScoped, Base):
    __tablename__ = 'zova_content_series'
    __table_args__ = (UniqueConstraint('user_id', 'brand_id', 'request_key'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_key: Mapped[str] = mapped_column(String(80))
    spec_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default='active')
    revision: Mapped[int] = mapped_column(Integer, default=0)


class SeriesOccurrence(BrandScoped, Base):
    __tablename__ = 'zova_series_occurrences'
    __table_args__ = (UniqueConstraint('series_id', 'position'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey('zova_content_series.id'), index=True)
    position: Mapped[int] = mapped_column(Integer)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    draft_id: Mapped[int | None] = mapped_column(ForeignKey('nova_drafts.id'), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default='planned')


class SeriesApproval(BrandScoped, Base):
    __tablename__ = 'zova_series_approvals'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey('zova_content_series.id'))
    revision: Mapped[int] = mapped_column(Integer)
    token: Mapped[str] = mapped_column(String(80), unique=True)
    payload_json: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MfaSettings(Base):
    __tablename__ = 'zova_mfa_settings'
    user_id: Mapped[int] = mapped_column(ForeignKey('nova_users.id'), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    encrypted_secret: Mapped[str] = mapped_column(Text, default='')
    setup_auth_version: Mapped[int] = mapped_column(Integer, default=0)
    setup_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_counter: Mapped[int] = mapped_column(Integer, default=-1)
    recovery_hashes_json: Mapped[str] = mapped_column(Text, default='[]')


class MfaChallenge(Base):
    __tablename__ = 'zova_mfa_challenges'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('nova_users.id'), index=True)
    auth_version: Mapped[int] = mapped_column(Integer)
    destination: Mapped[str] = mapped_column(String(500), default='/studio')
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)


from .schema_startup import schema_mode, verify_runtime_schema, verify_runtime_role
if schema_mode(engine) == 'verify':
    with engine.connect() as schema_connection:
        verify_runtime_role(schema_connection)
        verify_runtime_schema(schema_connection, Base.metadata)
else:
    # Existing databases require the reviewed offline registry backfill before startup.
    # Never silently assign privileges while serving requests.
    existing_users = 0
    with engine.connect() as registry_connection:
        if inspect(registry_connection).has_table('nova_users'):
            existing_users = registry_connection.scalar(select(func.count()).select_from(User.__table__))
            if existing_users and not all(inspect(registry_connection).has_table(name) for name in ('zova_workspaces','zova_workspace_memberships')):
                raise RuntimeError('Workspace registry migration required before application startup')
            if existing_users:
                from .tenant_references import verify_references, VERSION as reference_version
                from sqlalchemy import text
                verify_references(registry_connection)
                if not inspect(registry_connection).has_table('zova_schema_migrations') or not registry_connection.scalar(
                        text('SELECT COUNT(*) FROM zova_schema_migrations WHERE version=:version'), {'version':reference_version}):
                    raise RuntimeError('Workspace reference migration required before application startup')

    Base.metadata.create_all(bind=engine, tables=[table for table in Base.metadata.sorted_tables
                                                 if table not in (LegacyPublication.__table__, MfaSettings.__table__, MfaChallenge.__table__)])
    from .migrations import run_migrations
    run_migrations(engine)
    from .migrations import run_legacy_queue_migration
    run_legacy_queue_migration(engine, LegacyPublication.__table__)
    from .migrations import run_mfa_migration
    run_mfa_migration(engine, (MfaSettings.__table__, MfaChallenge.__table__))
    if not existing_users:
        from .tenant_references import apply_references
        apply_references(engine, writes_paused=True)


def get_db(request: Request):
    services = getattr(request.app.state, 'database_services', None)
    if services is not None:
        yield from services.request_session(request)
        return
    db = SessionLocal()
    try:
        from .brands import bind_request
        bind_request(db, request)
        yield db
    finally:
        db.close()


def get_preferences(db: Session, user_id: int) -> CreatorPreferences:
    from .brands import voice
    branded = voice(db, user_id)
    if branded is not None:
        return branded
    pref = db.scalar(select(CreatorPreferences).where(CreatorPreferences.user_id == user_id))
    if pref is None:
        pref = CreatorPreferences(user_id=user_id)
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return pref


def _create_workspace(connection, uid, bid, active):
    from .tenant_migration import workspace_key
    wid = workspace_key(uid,bid)
    connection.execute(TenantWorkspace.__table__.insert().values(id=wid,owner_user_id=uid,legacy_brand_id=bid))
    connection.execute(WorkspaceMembership.__table__.insert().values(workspace_id=wid,user_id=uid,role='owner',active=active,revision=1))


@event.listens_for(User,'after_insert')
def _new_user_workspace(mapper,connection,user):
    _create_workspace(connection,user.id,0,user.active)


@event.listens_for(Brand,'after_insert')
def _new_brand_workspace(mapper,connection,brand):
    active = connection.scalar(select(User.active).where(User.id==brand.user_id))
    if active is None:
        raise ValueError('Brand owner is unavailable')
    _create_workspace(connection,brand.user_id,brand.id,active)


@event.listens_for(Base, 'before_insert', propagate=True)
def _canonical_record_workspace(mapper, connection, row):
    if not isinstance(row, CanonicalWorkspace):
        return
    from .tenant_migration import workspace_key
    bid = row.brand_id if row.brand_id is not None else 0
    expected = workspace_key(row.user_id, bid)
    found = connection.scalar(select(TenantWorkspace.id).where(
        TenantWorkspace.id == expected, TenantWorkspace.owner_user_id == row.user_id,
        TenantWorkspace.legacy_brand_id == bid))
    if found is None or row.workspace_id not in (None, expected):
        raise ValueError('Invalid canonical workspace ownership')
    row.workspace_id = expected
