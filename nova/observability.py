"""Content-free request diagnostics with server-generated support references."""
import json
import logging
import os
import time
import uuid
from contextvars import ContextVar
from starlette.responses import JSONResponse

request_id = ContextVar('zova_request_id', default=None)
log = logging.getLogger('nova.requests')


class RequestDiagnostics:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        reference = uuid.uuid4().hex
        token = request_id.set(reference)
        started = time.monotonic()
        status = 500
        sent = False

        async def wrapped_send(message):
            nonlocal status, sent
            if message['type'] == 'http.response.start':
                status, sent = message['status'], True
                message = {**message, 'headers': [(k, v) for k, v in message.get('headers', [])
                                                  if k.lower() != b'x-request-id'] + [(b'x-request-id', reference.encode())]}
            await send(message)

        try:
            await self.app(scope, receive, wrapped_send)
        except Exception as exc:
            # Never log exception bodies/URLs: provider responses can contain credentials.
            log.error(json.dumps({'event':'request_failed', 'request_id':reference,
                                  'exception_type':type(exc).__name__}))
            if sent:
                raise RuntimeError('Response interrupted; support reference ' + reference) from None
            headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
                     'X-Frame-Options':'DENY','Referrer-Policy':'no-referrer',
                     'Content-Security-Policy':"default-src 'none'; frame-ancestors 'none'"}
            if os.environ.get('PUBLIC_BASE_URL','').startswith('https://'):
                headers['Strict-Transport-Security']='max-age=31536000'
            response = JSONResponse({'detail':'Zova could not complete this request. Please try again.',
                                     'support_reference':reference}, status_code=500,
                                    headers=headers)
            await response(scope, receive, wrapped_send)
        finally:
            route = scope.get('route')
            log.info(json.dumps({'event':'request_finished', 'request_id':reference,
                                 'route':getattr(route, 'path', 'unmatched'),
                                 'method':scope['method'], 'status':status,
                                 'duration_ms':round((time.monotonic()-started)*1000)}))
            request_id.reset(token)
