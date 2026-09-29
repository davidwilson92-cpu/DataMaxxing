"""Owner-scoped durable Custom GPT submissions. No automatic external retries."""
import hashlib
import json
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from .db import Creator, LegacyPublication, OAuth2Connection, SessionLocal, utcnow


def authority(db, creator):
    oauth = db.scalar(select(OAuth2Connection).where(OAuth2Connection.creator_id == creator.id))
    fields = [creator.id, creator.api_key_hash, creator.x_username, creator.active]
    if oauth:
        fields += [oauth.id, oauth.x_user_id, oauth.scope, oauth.encrypted_access_token]
    else:
        fields += [creator.encrypted_x_api_key, creator.encrypted_x_api_secret,
                   creator.encrypted_x_access_token, creator.encrypted_x_access_token_secret]
    return hashlib.sha256(json.dumps(fields).encode()).hexdigest()


def response(row):
    return {'job_id': row.id, 'status': row.status, 'success': row.status == 'published',
            'account': '@' + row.account, **json.loads(row.result_json or '{}'),
            'status_url': '/x/jobs/' + row.id}


def enqueue(db, creator, text, key):
    if not key:
        raise HTTPException(400, 'Supply an idempotency_key for this approved post and reuse it on retries.')
    job_id = hashlib.sha256(f'{creator.id}:{key}'.encode()).hexdigest()
    existing = db.get(LegacyPublication, job_id)
    if existing:
        if existing.text != text:
            raise HTTPException(409, 'This idempotency key belongs to different content.')
        return response(existing)
    row = LegacyPublication(id=job_id, creator_id=creator.id, text=text,
                            account=creator.x_username, authority_digest=authority(db, creator))
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.get(LegacyPublication, job_id)
        if not existing:
            raise
        if existing.text != text:
            raise HTTPException(409, 'This idempotency key belongs to different content.')
        row = existing
    return response(row)


def process_legacy(limit=25, publisher=None):
    if publisher is None:
        from .app import publish_legacy_creator
        publisher = publish_legacy_creator
    counts = {'published': 0, 'failed': 0}
    with SessionLocal() as db:
        db.execute(update(LegacyPublication).where(
            LegacyPublication.status == 'publishing',
            LegacyPublication.updated_at < utcnow() - timedelta(minutes=15)
        ).values(status='unknown', result_json=json.dumps({
            'error': 'Worker interrupted. Check X; this job will not be resent automatically.'})))
        db.commit()
        ids = db.scalars(select(LegacyPublication.id).where(LegacyPublication.status == 'queued')
                         .order_by(LegacyPublication.created_at).limit(limit)).all()
        for job_id in ids:
            claimed = db.execute(update(LegacyPublication).where(
                LegacyPublication.id == job_id, LegacyPublication.status == 'queued'
            ).values(status='publishing', updated_at=utcnow()))
            if claimed.rowcount != 1:
                db.rollback()
                continue
            db.commit()
            row = db.get(LegacyPublication, job_id)
            creator = db.get(Creator, row.creator_id)
            oauth = db.scalar(select(OAuth2Connection).where(OAuth2Connection.creator_id == row.creator_id))
            if (not creator or not creator.active or authority(db, creator) != row.authority_digest
                    or (oauth and 'tweet.write' not in (oauth.scope or '').replace(',', ' ').split())):
                row.status = 'failed'
                row.result_json = json.dumps({'error': 'The approved account or publishing permission changed. Review before submitting a new job.'})
                counts['failed'] += 1
                db.commit()
                continue
            try:
                result = publisher(row.text, creator, db)
                if not result.get('post_id'):
                    raise RuntimeError('Unconfirmed outcome')
                row.status = 'published'
                row.result_json = json.dumps({'post_id': str(result['post_id']), 'url': result.get('url')})
                counts['published'] += 1
            except Exception:
                db.rollback()
                row = db.get(LegacyPublication, job_id)
                row.status = 'unknown'
                row.result_json = json.dumps({'error': 'Publication outcome unconfirmed. Check X; this job will not be resent automatically.'})
                counts['failed'] += 1
            db.commit()
    return counts
