"""Content-versioned public assets; private pages and media retain no-store."""
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from urllib.parse import parse_qs

from starlette.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

DIRECTORY = Path(__file__).resolve().parent / 'static'


@lru_cache(maxsize=256)
def version(name):
    path = (DIRECTORY / name).resolve()
    if not path.is_relative_to(DIRECTORY) or not path.is_file():
        return ''
    return sha256(path.read_bytes()).hexdigest()[:16]


def url(name):
    return '/static/' + name + '?v=' + version(name)


class PublicAssets(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        supplied = parse_qs(scope.get('query_string', b'').decode('ascii', errors='ignore')).get('v', [''])[0]
        current = await run_in_threadpool(version, path)
        response.headers['Cache-Control'] = (
            'public, max-age=31536000, immutable'
            if response.status_code in (200, 304) and current and supplied == current
            else 'public, max-age=0, must-revalidate'
        )
        return response
