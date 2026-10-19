"""Do not retain OAuth codes, handoff secrets or private search queries in access logs."""
import logging
import re


def safe_path(value):
    path = str(value).split('?', 1)[0]
    return re.sub(r'(/mobile/(?:browser|authorize)/|/data-deletion/status/)[^/]+', r'\1[redacted]', path)


class RedactAccess(logging.Filter):
    def filter(self, record):
        if isinstance(record.args, tuple) and len(record.args) == 5:
            values = list(record.args)
            values[2] = safe_path(values[2])
            record.args = tuple(values)
        return True


def install():
    logger = logging.getLogger('uvicorn.access')
    if not any(isinstance(item, RedactAccess) for item in logger.filters):
        logger.addFilter(RedactAccess())
