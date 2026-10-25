"""Explicit full-service pause for offline erasure or a consistent cloud copy."""
import os
from datetime import datetime, timezone

STARTED_AT = datetime.now(timezone.utc)


def account_erasure_mode():
    return os.environ.get('ZOVA_MAINTENANCE_MODE', '') == 'account-erasure'


def maintenance_mode():
    return os.environ.get('ZOVA_MAINTENANCE_MODE', '') in {'account-erasure','cloud-migration'}


def permits_request(path, method):
    # Receipt/status/static responses have no customer write path. All provider
    # callbacks and webhooks are blocked as well; providers can retry after pause.
    return method in {'GET', 'HEAD'} and (path in {'/health', '/internal/ready', '/internal/status',
        '/internal/deletions', '/internal/maintenance'} or path.startswith('/data-deletion/status/')
        or path.startswith('/static/'))
