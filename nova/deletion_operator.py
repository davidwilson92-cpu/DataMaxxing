"""Receipt-bound manual erasure; never exposed as an HTTP mutation endpoint."""
import re
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from .db import DeletionRequest, User, WorkerHeartbeat, utcnow
from .security import hash_api_key
from .data_lifecycle import erase_plan, erase_local_account
from .deletion_policy import timing
from .maintenance import account_erasure_mode
from .runtime import scheduler_mode

DRAIN_SECONDS = 300


def resolve_receipt(db, code):
    if 'brand_id' in db.info:raise ValueError('Use a dedicated account-wide operator session')
    if not re.fullmatch(r'[0-9a-f]{64}',code or ''):raise ValueError('Use the exact account deletion receipt')
    receipt=db.get(DeletionRequest,code)
    if not receipt or receipt.status not in {'access_revoked','erasing','active_store_erased'}:
        raise ValueError('Receipt is not a verified self-service account deletion')
    # Limited-beta queue: resolve only nonpersonal IDs, never print/hash-scan email.
    # Keep the stable receipt after anonymisation so completion is still inspectable.
    ids=[uid for uid in db.scalars(select(User.id)) if hash_api_key(f'account:{uid}')==receipt.subject_hash]
    if len(ids)!=1:raise ValueError('Receipt cannot be resolved to exactly one account')
    user=db.get(User,ids[0])
    if user.active:raise ValueError('Account access is still active; investigate before erasure')
    return receipt,user.id


def plan_receipt(db,code):
    receipt,uid=resolve_receipt(db,code)
    plan=erase_plan(db,uid)
    return {'receipt':receipt.code,'status':receipt.status,**timing(receipt),**plan,
            'mutation':'none','required':'Pause and drain all web/worker services; reconcile blockers; review retention and backups.'}


def execute_receipt(db,code,case,proof,*,services_drained=False,retention_reviewed=False):
    """Proof is obtained by the CLI from the running service, not from the user UI.

    The operator must still verify *all* old instances/workers are stopped. A
    five-minute clean pause and worker heartbeat checks supplement that explicit
    confirmation; they do not pretend to detect arbitrary external writers.
    """
    if not account_erasure_mode() or scheduler_mode()!='disabled':
        raise ValueError('Operator process is not in account-erasure maintenance with disabled scheduling')
    if not services_drained or not retention_reviewed:
        raise ValueError('Service drain and retention review confirmations are required')
    if not isinstance(proof,dict) or proof.get('account_erasure_mode') is not True or proof.get('scheduler_mode')!='disabled':
        raise ValueError('Running service has not confirmed account-erasure maintenance')
    try:
        started=datetime.fromisoformat(proof['started_at'].replace('Z','+00:00'))
        if started.tzinfo is None or started>utcnow()-timedelta(seconds=DRAIN_SECONDS):raise ValueError()
    except (ValueError,TypeError,KeyError):
        raise ValueError('Allow at least five minutes after the replacement maintenance service starts') from None
    heartbeat=db.get(WorkerHeartbeat,'publishing')
    if heartbeat:
        latest=heartbeat.started_at
        if latest.tzinfo is None:latest=latest.replace(tzinfo=timezone.utc)
        if latest>=started:raise ValueError('A publishing worker ran after maintenance began; stop and drain it before continuing')
    receipt,uid=resolve_receipt(db,code)
    plan=erase_plan(db,uid)
    if plan['blockers']:raise ValueError('; '.join(plan['blockers']))
    result=erase_local_account(db,uid,case,writes_paused=True)
    db.refresh(receipt)
    if receipt.status!='active_store_erased' or receipt.completed_at is None:
        raise ValueError('Cleanup has not produced a verified completed receipt')
    return {**result,'receipt':receipt.code,**timing(receipt),'customer_notification':'Verified status receipt; no email was sent.'}
