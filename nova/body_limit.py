"""Bound streamed request bodies before multipart parsing, including chunked uploads."""
from starlette.responses import JSONResponse


class BodyLimitMiddleware:
    def __init__(self, app):
        self.app=app

    async def __call__(self, scope, receive, send):
        if scope['type']!='http' or scope['method'] in {'GET','HEAD','OPTIONS'}:
            return await self.app(scope,receive,send)
        maximum=160*1024*1024 if scope['path']=='/api/media' else 1024*1024
        # Spool to disk above 1 MB instead of buffering a complete video in RAM.
        from tempfile import SpooledTemporaryFile
        with SpooledTemporaryFile(max_size=1024*1024) as body:
            size=0
            while True:
                message=await receive()
                if message['type']=='http.disconnect':return
                data=message.get('body',b'');size+=len(data)
                if size>maximum:
                    return await JSONResponse({'detail':'Request too large.'},413)(scope,receive,send)
                body.write(data)
                if not message.get('more_body',False):break
            body.seek(0)
            remaining=size
            async def replay():
                nonlocal remaining
                if remaining<0:return await receive()
                chunk=body.read(1024*1024);remaining-=len(chunk)
                more=remaining>0
                if not more:remaining=-1
                return {'type':'http.request','body':chunk,'more_body':more}
            await self.app(scope,replay,send)
