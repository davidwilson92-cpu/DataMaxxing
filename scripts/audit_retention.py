"""Report expired authentication state; opt-in pruning never touches content.

Run on the existing deployment host. Default is aggregate read-only reporting.
No migrations, provider calls, identifiers, token values or customer text appear.
Activation needs the approved policy version; it is NOT scheduled by this tool.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys

POLICY_VERSION = '2026-10-26-v1'


def rules(now):
    from nova.db import AuthState, OAuthState, RecoveryToken, EmailVerification, RevokedSession
    cutoff = now - timedelta(hours=24)
    # Age of OAuth states deliberately exceeds their 10/20 minute validity.
    # Keep native refresh-reuse history and browser navigation receipts untouched.
    return (
        (RecoveryToken, RecoveryToken.expires_at < cutoff),
        (EmailVerification, EmailVerification.expires_at < cutoff),
        (RevokedSession, RevokedSession.expires_at < cutoff),
        (AuthState, AuthState.created_at < cutoff),
        (OAuthState, OAuthState.created_at < cutoff),
    )


def audit(db, now=None):
    from sqlalchemy import select, func
    now = now or datetime.now(timezone.utc)
    return {'policy_version': POLICY_VERSION, 'mode': 'report', 'counts': {
        model.__tablename__: db.scalar(select(func.count()).select_from(model).where(predicate))
        for model, predicate in rules(now)
    }, 'content_affected': False, 'native_sessions_affected': False}


def prune(db, *, approved_version, limit=500, now=None):
    """One bounded transactional batch. Caller commits; errors roll back all tables."""
    from sqlalchemy import delete, select
    if approved_version != POLICY_VERSION:
        raise ValueError('Approve the exact retention policy version before pruning')
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
        raise ValueError('Batch limit must be between 1 and 500')
    now = now or datetime.now(timezone.utc)
    counts = {}
    remaining = limit
    for model, predicate in rules(now):
        key = next(iter(model.__table__.primary_key.columns))
        ids = list(db.scalars(select(key).where(predicate).order_by(key).limit(remaining))) if remaining else []
        # Recheck age in the mutation; never turn a concurrent change into erasure.
        result = db.execute(delete(model).where(key.in_(ids), predicate)) if ids else None
        counts[model.__tablename__] = result.rowcount if result else 0
        remaining -= len(ids)
    return {'policy_version': POLICY_VERSION, 'mode': 'prune', 'counts': counts,
            'content_affected': False, 'native_sessions_affected': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--confirm-expired-only', action='store_true')
    args = parser.parse_args(argv)
    if not os.environ.get('DATABASE_URL'):
        parser.error('An explicit DATABASE_URL is required; no implicit database is used')
    approval = os.environ.get('ZOVA_RETENTION_POLICY_APPROVED', '')
    if args.apply and (not args.confirm_expired_only or approval != POLICY_VERSION):
        parser.error('Applying requires --confirm-expired-only and approved policy environment version')
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from sqlalchemy import text
    from nova.db import SessionLocal
    try:
        with SessionLocal() as db:
            if not args.apply:
                if db.get_bind().dialect.name == 'postgresql':
                    db.execute(text('SET TRANSACTION READ ONLY'))
                    db.execute(text("SET LOCAL statement_timeout = '30s'"))
                elif db.get_bind().dialect.name == 'sqlite':
                    db.execute(text('PRAGMA query_only = ON'))
                else:
                    raise ValueError('Unsupported database')
                result = audit(db)
                db.rollback()
            else:
                result = prune(db, approved_version=approval)
                db.commit()
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:
        print(json.dumps({'status': 'failed', 'detail': 'No completion claimed; inspect privately. No credentials printed.'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
