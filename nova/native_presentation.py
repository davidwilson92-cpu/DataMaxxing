"""Read-only presentation data for SwiftUI; mutations use existing services.

The authenticated device-bound cookie retains the same request security and
brand binding as the web client. Never serialize ORM objects or provider tokens.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from .db import SocialConnection, get_db, get_preferences
from .security import current_user

router = APIRouter(prefix='/api/native')

@router.get('/schedule-summary')
def schedule_summary(request: Request, db=Depends(get_db)):
    from .work_summary import work_summary
    return work_summary(db, current_user(request).id)


@router.get('/account')
def account(request: Request, db=Depends(get_db)):
    from .brands import context
    from .voice_memory import FIELDS, snapshot, memory
    from .ai_consent import permitted, required, VERSION
    from .connections import connection_options
    from .social import json_meta
    user = current_user(request)
    prefs = get_preferences(db, user.id)
    connections = db.scalars(select(SocialConnection).where(
        SocialConnection.user_id == user.id, SocialConnection.active.is_(True)
    ).order_by(SocialConnection.id.desc())).all()
    return {
        'presentation_version': 1,
        'profile': {'id': user.id, 'name': user.display_name, 'email': user.email,
                    'email_verified': user.email_verified_at is not None},
        'brand': context(user, db.info.get('brand_id', 0)),
        'voice': {**{key: getattr(prefs, key) for key in FIELDS}, **snapshot(prefs),
                  'timezone': prefs.timezone,
                  'approved_examples': memory(prefs).get('approved_examples', [])},
        'connections': [{'id': row.id, 'platform': row.platform,
                         'name': row.display_name or row.username or 'Connected account',
                         'username': row.username or '',
                         'status': json_meta(row).get('connection_health', 'unchecked')} for row in connections],
        'connection_options': {key: {'available': bool(value.get('ready', False)),
                                     'label': value.get('name', key)}
                               for key, value in connection_options().items()},
        'ai': {'allowed': permitted(user.id), 'required': required(), 'version': VERSION},
        'billing': {'native_purchases': False, 'label': 'Testing access'},
    }


@router.get('/deletion-confirmation')
def deletion_confirmation(request: Request):
    from .account_deletion import proof_for
    current_user(request)
    return {'proof': proof_for(request.cookies.get('nova_session', ''))}
