from fastapi import BackgroundTasks
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from nova import verification
from nova.db import SessionLocal, User, EmailVerification
from test_account_integrity import account


def test_new_account_verification_is_hashed_bound_and_queued(monkeypatch):
    _, uid, *_ = account()
    monkeypatch.setattr(verification.recovery, 'recovery_ready', lambda: True)
    monkeypatch.setattr(verification, 'allowed_request', lambda *a: True)
    tasks = BackgroundTasks()
    with SessionLocal() as db:
        user = db.get(User, uid)
        verification.welcome_verification(user, tasks)
        token = tasks.tasks[0].args[1]
        row = db.scalar(select(EmailVerification).where(EmailVerification.user_id == uid))
        assert row.email == user.email and row.token_hash == verification.hash_api_key(token)
        assert token not in row.token_hash and not row.used


def test_optional_verification_failure_does_not_undo_registration(monkeypatch):
    _, uid, *_ = account()
    monkeypatch.setattr(verification.recovery, 'recovery_ready', lambda: True)
    monkeypatch.setattr(verification, 'allowed_request', lambda *a: True)
    def fail(): raise SQLAlchemyError('synthetic private diagnostic')
    tasks = BackgroundTasks()
    with SessionLocal() as db:
        user = db.get(User, uid)
        monkeypatch.setattr(verification, 'SessionLocal', fail)
        verification.welcome_verification(user, tasks)
        assert user.active and tasks.tasks == []
