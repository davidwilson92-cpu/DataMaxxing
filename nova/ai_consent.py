"""Account-bound permission before content is sent to the AI provider."""
import os
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, StrictBool
from sqlalchemy import select

from .db import AIConsent, SessionLocal, User, get_db, utcnow
from .security import current_user

VERSION = '2026-10-19'
router = APIRouter()


def required():
    return os.environ.get('ZOVA_AI_CONSENT_REQUIRED', 'true').lower() != 'false'


def uses_ai(path):
    return (path.startswith(('/api/ai/', '/api/voice/'))
            or path in {'/api/conversation/plan', '/api/insights',
                        '/api/strategy/propose', '/api/strategy/recommend'}
            or bool(re.fullmatch(r'/api/(?:strategy/actions|series/occurrences)/[^/]+/draft', path)))


def permitted(uid):
    with SessionLocal() as db:
        row = db.get(AIConsent, uid)
        return bool(row and row.version == VERSION and row.allowed)


class Choice(BaseModel):
    model_config = ConfigDict(extra='forbid')
    allowed: StrictBool
    version: str


@router.get('/api/privacy/ai')
def status(request: Request):
    uid = current_user(request).id
    return {'allowed': permitted(uid), 'version': VERSION, 'required': required()}


@router.post('/api/privacy/ai')
def choose(body: Choice, request: Request, db=Depends(get_db)):
    uid = current_user(request).id
    if body.version != VERSION:
        raise HTTPException(409, 'The AI information changed. Review it again.')
    # Serialise choices from this account, including first-use requests in two tabs.
    db.scalar(select(User).where(User.id == uid).with_for_update())
    row = db.get(AIConsent, uid)
    if row is None:
        row = AIConsent(user_id=uid)
        db.add(row)
    row.allowed = body.allowed
    row.version = VERSION
    row.updated_at = utcnow()
    db.commit()
    return {'allowed': row.allowed, 'version': VERSION}
