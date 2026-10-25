"""Bounded brand voice memory; explicit preferences always win over learning."""
import json

from sqlalchemy import select, update
from fastapi import HTTPException
from .db import AIConsent, BrandVoice, CreatorPreferences, User, utcnow

FIELDS = ('writing_tone', 'audience', 'topics', 'things_to_avoid', 'example_posts', 'preferred_post_length')
TEXT_FIELDS = FIELDS[:-1]


def lock_active_owner(db, uid):
    """Do not let an AI response or stale form write after account revocation."""
    claimed = db.execute(update(User).where(User.id == uid, User.active.is_(True)).values(updated_at=User.updated_at))
    if claimed.rowcount != 1:
        raise HTTPException(401, 'Sign in again to continue.')
    db.expire_all()


def memory(prefs):
    try:
        value = json.loads(getattr(prefs, 'learned_json', '{}') or '{}')
        return value if isinstance(value, dict) else {}
    except (ValueError, TypeError):
        return {}


def snapshot(prefs):
    saved = memory(prefs)
    return {'preferences': {key: getattr(prefs, key) for key in FIELDS},
            'learned': saved.get('profile', {}),
            'updated_at': prefs.updated_at.isoformat() if prefs.updated_at else None,
            'learned_at': saved.get('learned_at'),
            'approved_at': saved.get('approved_at'),
            'approved_count': len(saved.get('approved_examples', [])),
            'overrides': saved.get('overrides', [])}


def save_learning(prefs, profile, examples):
    """Refresh inferred fields only where the creator has not overridden them."""
    state = memory(prefs)
    previous = state.get('profile', {})
    overrides = set(state.get('overrides', []))
    learned = {key: str(profile.get(key, '')).strip()[:5000] for key in TEXT_FIELDS if key != 'example_posts'}
    if not learned['writing_tone']:
        raise ValueError('Voice analysis did not return a usable writing tone')
    learned['example_posts'] = '\n\n'.join(examples)[:12000]
    learned['preferred_post_length'] = max(30, min(4000, int(profile['preferred_post_length'])))
    for key in FIELDS:
        current = getattr(prefs, key)
        default = 220 if key == 'preferred_post_length' else ''
        if key not in overrides and (current == previous.get(key, default) or current == default):
            setattr(prefs, key, learned[key])
        else:
            overrides.add(key)
    state.update(profile=learned, overrides=sorted(overrides), learned_at=utcnow().isoformat())
    prefs.learned_json = json.dumps(state, ensure_ascii=False)
    prefs.updated_at = utcnow()


def mark_edits(prefs, values):
    state = memory(prefs)
    overrides = set(state.get('overrides', []))
    for key, value in values.items():
        if key in FIELDS and value != getattr(prefs, key):
            overrides.add(key)
        setattr(prefs, key, value)
    state['overrides'] = sorted(overrides)
    prefs.learned_json = json.dumps(state, ensure_ascii=False)


def remember_approved(db, uid, payload):
    """Use only the exact approved captions, with current AI sharing permission.

    This is local memory, not an additional provider call during publication.
    It never learns unapproved chat text or claims that a post was published.
    """
    from .ai_consent import VERSION
    consent = db.get(AIConsent, uid)
    if not consent or not consent.allowed or consent.version != VERSION:
        return
    texts = []
    for target in payload.get('targets', {}).values():
        for value in target.get('posts', []):
            if isinstance(value, str) and value.strip():
                value = value.strip()[:4000]
                if value not in texts:
                    texts.append(value)
    if not texts:
        return
    brand_id = db.info.get('brand_id', 0)
    model = BrandVoice if brand_id else CreatorPreferences
    statement = select(model).where(model.user_id == uid)
    if brand_id:
        statement = statement.where(BrandVoice.brand_id == brand_id)
    prefs = db.scalar(statement)
    if prefs is None:
        prefs = model(user_id=uid, **({'brand_id': brand_id} if brand_id else {}))
        db.add(prefs); db.flush()  # Never commit the surrounding approval early.
    state = memory(prefs)
    samples = texts + [value for value in state.get('approved_examples', []) if value not in texts]
    state['approved_examples'] = samples[:12]
    state['approved_at'] = utcnow().isoformat()
    prefs.learned_json = json.dumps(state, ensure_ascii=False)
    prefs.updated_at = utcnow()


def generation_examples(prefs):
    """Explicit examples first; recently approved examples remain visibly editable."""
    state = memory(prefs)
    examples = getattr(prefs, 'example_posts', '') or ''
    approved = state.get('approved_examples', [])
    if approved:
        examples += '\n\nRecently approved captions:\n' + '\n\n'.join(approved)
    return examples[:20000]
