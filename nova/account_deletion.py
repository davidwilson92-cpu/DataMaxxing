"""Self-service deletion initiation; verified erasure is a separate operation.

Stopping access is not proof of erasure. In-flight provider operations, retained
ledgers and upload removal must still be reconciled by data_lifecycle.
"""
import hashlib
import hmac
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select, update

from . import allowances
from .db import (ContentSeries, DeletionRequest, MobileSession, OAuthState,
                 PendingConnection, Publication, PublishReview, RecoveryToken,
                 ScheduledPost, SeriesOccurrence, SocialConnection, User, utcnow)
from .security import hash_api_key, session_secret, verify_password


def proof_for(token):
    expires = int((utcnow() + timedelta(minutes=15)).timestamp())
    signature = hmac.new(session_secret().encode(), f'delete:{hash_api_key(token)}:{expires}'.encode(), hashlib.sha256).hexdigest()
    return f'{expires}.{signature}'


def check_proof(token, proof):
    try:
        expires, signature = proof.split('.', 1)
        if not int(utcnow().timestamp()) < int(expires) <= int((utcnow()+timedelta(minutes=16)).timestamp()):
            return False
        expected = hmac.new(session_secret().encode(), f'delete:{hash_api_key(token)}:{expires}'.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected)
    except (ValueError, TypeError):
        return False


def initiate(db, uid, password):
    if 'brand_id' in db.info:
        raise ValueError('Account deletion must use an account-wide session')
    allowances.lock(db,uid)
    user=db.scalar(select(User).where(User.id==uid).with_for_update())
    if not user or not user.active:
        raise HTTPException(401,'Sign in required')
    if not verify_password(password,user.password_hash):
        raise HTTPException(400,'The current password is incorrect.')
    code=hmac.new(session_secret().encode(),f'account-deletion:{uid}'.encode(),hashlib.sha256).hexdigest()
    receipt=db.get(DeletionRequest,code)
    if receipt is None:
        receipt=DeletionRequest(code=code,subject_hash=hash_api_key(f'account:{uid}'))
        db.add(receipt)
    # These conditional writes never overwrite claimed/pending/unknown outcomes.
    for row in db.scalars(select(Publication).where(Publication.user_id==uid,Publication.status.in_(('queued','scheduled')))).all():
        changed=db.execute(update(Publication).where(Publication.id==row.id,Publication.status.in_(('queued','scheduled'))).values(status='cancelled',updated_at=utcnow()).execution_options(synchronize_session=False))
        if changed.rowcount:
            allowances.finish(db,f'publication:{row.id}',False)
    db.execute(update(ScheduledPost).where(ScheduledPost.user_id==uid,ScheduledPost.status=='scheduled').values(status='cancelled',updated_at=utcnow()))
    db.execute(update(PublishReview).where(PublishReview.user_id==uid,PublishReview.status=='review').values(status='cancelled'))
    db.execute(update(ContentSeries).where(ContentSeries.user_id==uid,ContentSeries.status=='active').values(status='paused'))
    db.execute(update(SeriesOccurrence).where(SeriesOccurrence.user_id==uid,SeriesOccurrence.status=='planned').values(status='cancelled'))
    db.execute(update(SocialConnection).where(SocialConnection.user_id==uid).values(active=False))
    db.execute(update(MobileSession).where(MobileSession.user_id==uid).values(revoked=True))
    db.execute(update(RecoveryToken).where(RecoveryToken.user_id==uid).values(used=True))
    db.execute(update(OAuthState).where(OAuthState.user_id==uid).values(used=True))
    db.execute(update(PendingConnection).where(PendingConnection.user_id==uid).values(used=True,encrypted_payload=''))
    user.active=False
    user.auth_version+=1
    receipt.status='access_revoked'
    receipt.scope=('Full account deletion requested by the verified owner. Account access and future connection use are disabled; '
                   'unsent schedules are cancelled. Data, retained records and any provider operation already in progress still '
                   'require verified erasure processing. Published posts and provider-side grants are not removed by this request.')
    db.commit()
    return code
