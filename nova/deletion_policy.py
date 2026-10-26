"""Owner-approved limited-beta deletion service target; no automatic erasure."""
from datetime import timedelta, timezone
from .db import utcnow

OWNER = 'David'
TARGET_DAYS = 7
PENDING = ('received', 'access_revoked', 'erasing')


def timing(receipt):
    created = receipt.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    due = created + timedelta(days=TARGET_DAYS)
    return {'owner': OWNER, 'target_days': TARGET_DAYS, 'due_at': due.isoformat(),
            'overdue': receipt.status in PENDING and utcnow() > due,
            'completed_at': receipt.completed_at.isoformat() if receipt.completed_at else None}
