"""Content-versioned public assets; private pages and media retain no-store."""
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from urllib.parse import parse_qs

from starlette.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import Headers
from starlette.responses import Response

DIRECTORY = Path(__file__).resolve().parent / 'static'
BASE_STYLES = ('nova.css', 'refinement.css', 'connections.css', 'workspace-ui.css')
BUNDLE = 'zova-base.css'


@lru_cache(maxsize=1)
def base_styles():
    # Keep the original cascade order and relative asset paths.
    return b'\n'.join((DIRECTORY / name).read_bytes() for name in BASE_STYLES)


@lru_cache(maxsize=256)
def version(name):
    if name == BUNDLE:
        return sha256(base_styles()).hexdigest()[:16]
    path = (DIRECTORY / name).resolve()
    if not path.is_relative_to(DIRECTORY) or not path.is_file():
        return ''
    return sha256(path.read_bytes()).hexdigest()[:16]


def url(name):
    return '/static/' + name + '?v=' + version(name)


class PublicAssets(StaticFiles):
    async def get_response(self, path, scope):
        if path == BUNDLE and scope['method'] in ('GET', 'HEAD'):
            css = await run_in_threadpool(base_styles)
            headers = {'etag': '"' + version(BUNDLE) + '"'}
            if self.is_not_modified(Headers(headers), Headers(scope=scope)):
                response = Response(status_code=304, headers=headers)
            else:
                headers['content-length'] = str(len(css))
                response = Response(css if scope['method'] == 'GET' else b'', media_type='text/css', headers=headers)
        else:
            response = await super().get_response(path, scope)
        supplied = parse_qs(scope.get('query_string', b'').decode('ascii', errors='ignore')).get('v', [''])[0]
        current = await run_in_threadpool(version, path)
        response.headers['Cache-Control'] = (
            'public, max-age=31536000, immutable'
            if response.status_code in (200, 304) and current and supplied == current
            else 'public, max-age=0, must-revalidate'
        )
        return response
