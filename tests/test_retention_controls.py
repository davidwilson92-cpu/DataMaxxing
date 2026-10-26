from datetime import datetime, timedelta, timezone
import json
import pytest
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from nova.db import Base, RecoveryToken, EmailVerification, RevokedSession, AuthState, OAuthState, User, MobileSession, MobileRefresh, Draft
from scripts.audit_retention import audit, prune, POLICY_VERSION

NOW = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)


@pytest.fixture
def retention_db():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(User(id=1, email='synthetic@example.invalid', password_hash='synthetic-only', display_name='Synthetic'))
        db.flush()
        yield db
        db.rollback()
    engine.dispose()


def count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def test_only_old_expired_authority_is_pruned_and_output_has_no_identity(retention_db):
    db = retention_db
    for name, hours in [('old', -25), ('boundary', -24), ('recent', -1), ('active', 1)]:
        stamp = NOW + timedelta(hours=hours)
        db.add(RecoveryToken(token_hash=name, user_id=1, auth_version=1, expires_at=stamp))
        db.add(EmailVerification(token_hash=name, user_id=1, email='private@example.invalid', expires_at=stamp))
        db.add(RevokedSession(token_hash=name, expires_at=stamp))
        db.add(AuthState(provider='apple', state_hash=name, nonce_hash='secret-'+name, created_at=stamp))
        db.add(OAuthState(user_id=1, platform='instagram', state_hash=name, encrypted_code_verifier='secret', created_at=stamp))
    db.add(MobileSession(id='active-session', user_id=1, auth_version=1, access_hash='access', access_expires_at=NOW+timedelta(hours=1), expires_at=NOW+timedelta(days=1)))
    db.flush()
    db.add(MobileRefresh(token_hash='used-refresh', session_id='active-session', used=True))
    db.add(Draft(user_id=1, title='Private saved work', brief='Keep me'))
    db.commit()
    report = audit(db, NOW)
    assert list(report['counts'].values()) == [1]*5
    assert count(db, RecoveryToken) == 4  # Audit is read-only.
    result = prune(db, approved_version=POLICY_VERSION, now=NOW)
    db.commit()
    assert list(result['counts'].values()) == [1]*5
    assert count(db, RecoveryToken) == 3
    assert db.get(RecoveryToken, 'active') and db.get(RevokedSession, 'active')
    assert db.get(MobileRefresh, 'used-refresh').used
    assert count(db, Draft) == 1 and count(db, User) == 1
    assert 'private' not in json.dumps([report,result]).lower()
    assert 'secret' not in json.dumps([report,result]).lower()
    assert sum(prune(db, approved_version=POLICY_VERSION, now=NOW)['counts'].values()) == 0


def test_approval_and_batch_are_fail_closed(retention_db):
    db = retention_db
    for i in range(4):
        db.add(RecoveryToken(token_hash=str(i), user_id=1, auth_version=1, expires_at=NOW-timedelta(days=2)))
    db.commit()
    with pytest.raises(ValueError): prune(db, approved_version='not-approved', now=NOW)
    for bad in (0, 501, True, 1.5):
        with pytest.raises(ValueError): prune(db, approved_version=POLICY_VERSION, limit=bad, now=NOW)
    result = prune(db, approved_version=POLICY_VERSION, limit=2, now=NOW)
    assert sum(result['counts'].values()) == 2
    db.rollback()
    assert count(db, RecoveryToken) == 4  # Whole batch can roll back.
