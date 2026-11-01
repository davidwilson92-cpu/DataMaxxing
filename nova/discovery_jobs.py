"""Durable, bounded optional topic research, separate from interactive drafting."""
import asyncio
from datetime import timedelta
import hashlib
import json
import logging
import os
import secrets

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from .db import AIConsent, Brand, DiscoveryJob, SessionLocal, Strategy, User, utcnow

log = logging.getLogger('nova.discovery')


def topics(db, uid, themes, revision):
    from . import trends
    themes = themes.strip()[:2000]
    if not themes or not os.environ.get('OPENAI_API_KEY'):
        return trends.discover(themes, uid)
    brand = db.info.get('brand_id', 0)
    digest = hashlib.sha256((str(revision) + '\n' + themes).encode()).hexdigest()
    row = db.scalar(select(DiscoveryJob).where(DiscoveryJob.user_id == uid, DiscoveryJob.brand_id == brand))
    now = utcnow()
    fresh = row and row.completed_at and row.completed_at.replace(tzinfo=None) > (now-timedelta(minutes=15)).replace(tzinfo=None)
    if row and row.request_hash == digest and fresh:
        return json.loads(row.result_json)
    same_request = row and row.request_hash == digest
    if row is None:
        row = DiscoveryJob(user_id=uid, brand_id=brand, request_hash=digest,
                           strategy_revision=revision, themes=themes)
        db.add(row)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            row = db.scalar(select(DiscoveryJob).where(DiscoveryJob.user_id == uid, DiscoveryJob.brand_id == brand))
            if row and row.request_hash != digest:
                db.execute(update(DiscoveryJob).where(DiscoveryJob.id == row.id,
                    DiscoveryJob.request_hash == row.request_hash).values(request_hash=digest,
                    strategy_revision=revision, themes=themes, status='pending', attempts=0,
                    next_attempt_at=now, lease=None, lease_expires_at=None, result_json='{}', completed_at=None))
                db.commit()
    elif not same_request or row.status in {'complete', 'cancelled'} or (
        row.status == 'failed' and row.next_attempt_at.replace(tzinfo=None) <= now.replace(tzinfo=None)
    ):
        db.execute(update(DiscoveryJob).where(DiscoveryJob.id == row.id,
            DiscoveryJob.request_hash == row.request_hash, DiscoveryJob.status == row.status,
            DiscoveryJob.lease == row.lease).values(request_hash=digest, strategy_revision=revision,
            themes=themes, status='pending', attempts=0, next_attempt_at=now, lease=None,
            lease_expires_at=None, result_json='{}', completed_at=None))
        db.commit()
    return {'topics': [], 'checked_at': now.isoformat(),
            'note': 'Current-topic research is updating. This proposal uses your strategy, voice and available performance.'}


def authorized(db, job):
    from .ai_consent import VERSION, required
    user = db.get(User, job.user_id)
    consent = db.get(AIConsent, job.user_id)
    brand = db.get(Brand, job.brand_id) if job.brand_id else None
    strategy = db.scalar(select(Strategy).where(Strategy.user_id == job.user_id,
                                               Strategy.brand_id == job.brand_id))
    return bool(user and user.active and (not job.brand_id or brand and brand.user_id == job.user_id)
                and strategy and strategy.revision == job.strategy_revision
                and (not required() or consent and consent.allowed and consent.version == VERSION))


def process_next():
    """One leased job per call. Crashes retry after expiry, never publish content."""
    from . import trends
    now = utcnow()
    with SessionLocal() as db:
        row = db.scalar(select(DiscoveryJob).where(or_(
            (DiscoveryJob.status == 'pending') & (DiscoveryJob.next_attempt_at <= now),
            (DiscoveryJob.status == 'running') & (DiscoveryJob.lease_expires_at <= now),
        )).order_by(DiscoveryJob.next_attempt_at, DiscoveryJob.id).limit(1))
        if row is None:
            return False
        lease = secrets.token_hex(16)
        claimed = db.execute(update(DiscoveryJob).where(DiscoveryJob.id == row.id,
            DiscoveryJob.status == row.status, DiscoveryJob.lease == row.lease,
            DiscoveryJob.request_hash == row.request_hash).values(status='running', lease=lease,
            lease_expires_at=now+timedelta(minutes=3), attempts=DiscoveryJob.attempts+1))
        db.commit()
        if claimed.rowcount != 1:
            return True
        db.refresh(row)
        if row.lease != lease or row.status != 'running':
            return True
        uid, brand, job_id, digest = row.user_id, row.brand_id, row.id, row.request_hash
        db.info.update(brand_user_id=uid, brand_id=brand)
        if not authorized(db, row) or row.attempts > 3:
            db.execute(update(DiscoveryJob).where(DiscoveryJob.id == job_id, DiscoveryJob.lease == lease)
                       .values(status='cancelled', lease=None, lease_expires_at=None))
            db.commit()
            return True
        themes = row.themes
        db.commit()  # Release the read transaction before any provider wait.
        try:
            # This is the optional research portion of an already-authorised
            # recommendation action. Provider usage is recorded by trends itself;
            # do not consume a second customer action for the same recommendation.
            result = trends.discover(themes, uid)
            # Consent changes lock the same owner. A result cannot overwrite a
            # newer theme request or survive revocation while the read ran.
            db.scalar(select(User).where(User.id == uid).with_for_update())
            db.expire_all()
            job = db.get(DiscoveryJob, job_id)
            if job is None or job.lease != lease or job.request_hash != digest:
                db.rollback()
                return True
            permitted = authorized(db, job)
            db.execute(update(DiscoveryJob).where(DiscoveryJob.id == job_id, DiscoveryJob.lease == lease)
                .values(status='complete' if permitted else 'cancelled', lease=None,
                        lease_expires_at=None, result_json=json.dumps(result) if permitted else '{}',
                        completed_at=utcnow() if permitted else None))
            db.commit()
        except Exception:
            db.rollback()
            job = db.get(DiscoveryJob, job_id)
            if job and job.lease == lease:
                exhausted = job.attempts >= 3
                db.execute(update(DiscoveryJob).where(DiscoveryJob.id == job_id, DiscoveryJob.lease == lease)
                    .values(status='failed' if exhausted else 'pending', lease=None, lease_expires_at=None,
                            next_attempt_at=utcnow()+timedelta(seconds=900 if exhausted else 30*job.attempts)))
                db.commit()
            log.warning('Optional topic research deferred')
    return True


async def loop():
    while True:
        try:
            await asyncio.to_thread(process_next)
        except Exception:
            log.warning('Topic research worker will retry')
        await asyncio.sleep(5)
