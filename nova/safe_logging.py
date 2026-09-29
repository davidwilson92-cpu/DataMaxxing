"""Do not retain signed downloads, OAuth codes or recovery tokens in access logs."""
import logging


class SafeAccessLog(logging.Filter):
    def filter(self, record):
        # Both supported Uvicorn HTTP implementations use this structured shape.
        # Fail closed on an unknown shape rather than logging an unredacted URL.
        if record.msg != '%s - "%s %s HTTP/%s" %d' or not isinstance(record.args, tuple) or len(record.args) != 5:
            return False
        client, method, path, version, status = record.args
        record.args = (client, method, str(path).partition('?')[0], version, status)
        return True


def install_access_filter():
    logger = logging.getLogger('uvicorn.access')
    if not any(isinstance(item, SafeAccessLog) for item in logger.filters):
        logger.addFilter(SafeAccessLog())
