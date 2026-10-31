"""Repeatable production-ASGI benchmark with disposable data and controlled providers.

Run with the production dependencies. No real credentials, social writes or AI costs.
Provider delay and SQL round-trip delay are explicit simulation inputs, not live SLAs.
"""
from __future__ import annotations

import argparse
import contextvars
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(os.environ.get('BENCH_SOURCE_ROOT', Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(ROOT))


def runtime_digest():
    digest = hashlib.sha256()
    for folder in ('nova', 'ios'):
        for path in sorted((ROOT/folder).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                digest.update(path.relative_to(ROOT).as_posix().encode())
                digest.update(path.read_bytes().replace(b'\r\n', b'\n'))
    return digest.hexdigest()


def serve(port: int):
    from datetime import timedelta
    from sqlalchemy import event
    from nova.app import app
    from nova import ai, strategy, trends, storage
    from nova.db import (SessionLocal, User, Draft, Activity, SocialConnection,
                         ContentSeries, SeriesOccurrence, Strategy, MediaAsset, engine, utcnow)
    from nova.security import encrypt, hash_password
    import httpx
    import uvicorn

    with SessionLocal() as db:
        owner = User(email='benchmark@example.test', display_name='Benchmark Gym',
                     password_hash=hash_password('Synthetic-benchmark-only-2026!'),
                     studio_intro_pending=False)
        db.add(owner)
        db.flush()
        db.add(Strategy(user_id=owner.id, revision=1, confirmed_json=json.dumps({
            'goal':'Grow beginner gym class membership in Brixton',
            'audience':'Local people starting strength training',
            'themes':'Beginner strength training', 'platforms':['instagram']})))
        from PIL import Image
        import io
        import random
        image = Image.frombytes('RGB', (2048, 1536), random.Random(42).randbytes(2048*1536*3))
        image_bytes = io.BytesIO(); image.save(image_bytes, format='JPEG', quality=92)
        saved = storage.save_bytes(image_bytes.getvalue(), 'gym-photo.jpg', 'image/jpeg', os.environ['PUBLIC_BASE_URL'])
        media = MediaAsset(user_id=owner.id, filename='gym-photo.jpg', mime_type='image/jpeg',
                           storage_key=saved.storage_key, public_url=saved.public_url, size_bytes=len(image_bytes.getvalue()))
        db.add(media); db.flush()
        for platform in ('x', 'instagram', 'facebook', 'tiktok'):
            db.add(SocialConnection(user_id=owner.id, platform=platform,
                account_id=platform+'-synthetic', username='brixtongym',
                encrypted_access_token=encrypt('invalid-synthetic-token'),
                scope='video.list,user.info.stats,instagram_business_basic',
                metadata_json=json.dumps({'auth_provider':'instagram_login'})))
        drafts = [Draft(user_id=owner.id, title=f'Gym class {i}', brief='Beginner strength classes in Brixton.',
            platforms_json='["instagram"]', variants_json='{"instagram":{"posts":["Try our beginner strength class."]}}',
            workspace_json=json.dumps({'media_asset_ids':[media.id],
                'conversation':[{'role':'user','content':'Plan a gym post. '*30}]}))
            for i in range(1000)]
        db.add_all(drafts)
        db.flush()
        for platform in ('x','instagram','facebook','tiktok'):
            db.add_all([Activity(user_id=owner.id, draft_id=drafts[-i-1].id,
                platform=platform, status='published', platform_post_id=str(100+i),
                url=f'https://example.test/{platform}/{i}') for i in range(10)])
        for i in range(10):
            series=ContentSeries(user_id=owner.id, request_key=f'benchmark-{i}', spec_json='{}')
            db.add(series)
            db.flush()
            db.add_all([SeriesOccurrence(user_id=owner.id, series_id=series.id,
                position=j, due_at=utcnow()+timedelta(days=j), draft_id=drafts[i*10+j].id)
                for j in range(10)])
        db.commit()

    counts = contextvars.ContextVar('benchmark_counts', default=None)
    sql_delay = float(os.environ['BENCH_SQL_DELAY'])
    provider_delay = float(os.environ['BENCH_PROVIDER_DELAY'])

    @event.listens_for(engine, 'before_cursor_execute')
    def count_query(*args):
        value=counts.get()
        if value is not None:
            value['sql'] += 1
            time.sleep(sql_delay)

    @app.middleware('http')
    async def measure(request, call_next):
        value={'sql':0,'provider':0,'ai':0}
        token=counts.set(value)
        try:
            response=await call_next(request)
            for key,total in value.items():
                response.headers['X-Benchmark-'+key]=str(total)
            return response
        finally:
            counts.reset(token)

    def provider(method, url, **kwargs):
        value=counts.get()
        if value is not None:value['provider']+=1
        time.sleep(provider_delay)
        now=utcnow().isoformat()
        posts=[{'id':str(100+i),'text':'A gym class update','caption':'A gym class update',
                'message':'A gym class update','title':'A gym class update','created_at':now,
                'timestamp':now,'created_time':now,'create_time':int(time.time()),
                'like_count':10,'comments_count':2,'comment_count':2,'share_count':1,'view_count':100,
                'public_metrics':{'like_count':10,'reply_count':2,'retweet_count':1,'impression_count':100},
                'reactions':{'summary':{'total_count':10}},'comments':{'summary':{'total_count':2}},
                'shares':{'count':1},'permalink':'https://example.test/post',
                'permalink_url':'https://example.test/post'} for i in range(10)]
        if 'open.tiktokapis.com' in url:
            data={'data':{'videos':posts,'user':{'follower_count':200}},'error':{'code':'ok'}}
        elif '/tweets' in url or url.endswith(('/media','/posts')):
            data={'data':posts}
        elif 'api.x.com' in url:
            data={'data':{'public_metrics':{'followers_count':200}}}
        else:
            data={'followers_count':200,'like_count':10,'comments_count':2,
                  'reactions':{'summary':{'total_count':10}},'comments':{'summary':{'total_count':2}}}
        return httpx.Response(200,json=data,request=httpx.Request(method,url))

    for method in ('get','post','put','patch','delete'):
        setattr(httpx,method,lambda url,_method=method,**kwargs:provider(_method.upper(),url,**kwargs))

    def generate(**kwargs):
        value=counts.get()
        if value is not None:value['ai']+=1
        time.sleep(0.3)
        return {p:{'posts':['Try a beginner strength class in Brixton.']} for p in kwargs['platforms']}

    recommendation_batch=0
    def recommend(*args,**kwargs):
        nonlocal recommendation_batch
        recommendation_batch+=1
        value=counts.get()
        if value is not None:value['ai']+=1
        time.sleep(0.3)
        return {'actions':[{'kind':'draft','title':f'Share gym tip {recommendation_batch}-{i}',
            'reason':'Help beginners feel confident.','brief':f'Introduce beginner exercise {recommendation_batch}-{i}.',
            'effort':'10 minutes','needs':'One photo','platform':'instagram','format':'post'} for i in range(3)]}

    ai.generate_variants=generate
    strategy.model_json=recommend
    def research(*args):
        time.sleep(1)
        return {'topics':[], 'checked_at':utcnow().isoformat(), 'note':'No usable recent sources found.'}
    trends.discover=research
    # Production already receives static gzip at Cloudflare. Normalise this on
    # both local revisions so origin compression is not misreported as a new win.
    from starlette.middleware.gzip import GZipMiddleware
    compressed = GZipMiddleware(app, compresslevel=4)
    async def serving(scope, receive, send):
        target = compressed if scope.get('path', '').startswith('/static/') else app
        await target(scope, receive, send)
    uvicorn.run(serving,host='127.0.0.1',port=port,access_log=False,log_level='warning')


def benchmark(output: str, port: int, samples: int, browser: bool, browser_only=False):
    import httpx
    run_root=Path(tempfile.mkdtemp(prefix='zova-performance-'))
    env={key:value for key,value in os.environ.items() if not any(part in key for part in
        ('TOKEN','SECRET','API_KEY','DATABASE_URL','SMTP','STRIPE','AWS_','BOOTSTRAP','S3_'))}
    env.update(DATABASE_URL='sqlite:///'+(run_root/'benchmark.db').as_posix(),
        SESSION_SECRET='synthetic-benchmark-session-only',
        CREDENTIAL_ENCRYPTION_KEY='eV7ZGbkgONCU5t6fVtxgBMvCKx6-4UlAHWVHN2LoflE=',
        UPLOAD_DIR=str(run_root/'uploads'),PUBLIC_BASE_URL=f'http://127.0.0.1:{port}',
        ZOVA_SCHEDULER_MODE='disabled',ZOVA_SCHEMA_MODE='initialize',STRIPE_MODE='off',
        OPENAI_API_KEY='synthetic-benchmark-only',
        REQUIRE_SUBSCRIPTION='false',PLAN_LIMITS_ENABLED='false',ZOVA_AI_CONSENT_REQUIRED='false',
        RATE_LIMIT_SCALE='100',BENCH_SQL_DELAY='0.002',BENCH_PROVIDER_DELAY='0.1')
    result={'source':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'runtime_sha256':runtime_digest(),
        'workload':{'drafts':1000,'series':10,'occurrences':100,'platforms':4,
                    'provider_delay_ms':100,'sql_round_trip_ms':2,'ai_delay_ms':300,'optional_research_delay_ms':1000,
                    'samples':samples,'static_compression':'gzip on both revisions, matching live edge',
                    'server':'production FastAPI/Uvicorn, isolated SQLite'},'routes':{}}
    if browser_only:
        result = json.loads(Path(output).read_text(encoding='utf-8'))
    with (run_root/'server.log').open('w') as log:
        process=subprocess.Popen([sys.executable,__file__,'--serve','--port',str(port)],
                                 cwd=ROOT,env=env,stdout=log,stderr=log)
        try:
            with httpx.Client(base_url=f'http://127.0.0.1:{port}',timeout=60) as client:
                for _ in range(90):
                    try:
                        if client.get('/health').status_code==200:break
                    except httpx.HTTPError:pass
                    if process.poll() is not None:raise RuntimeError((run_root/'server.log').read_text())
                    time.sleep(0.5)
                login={'email':'benchmark@example.test','password':'Synthetic-benchmark-only-2026!'}
                response=client.post('/login',data=login)
                if response.status_code!=303:raise RuntimeError('Synthetic login failed')
                cases=[('login','POST','/login',{'data':login}),('studio','GET','/studio',{}),
                    ('native_account','GET','/api/native/account',{}),('drafts','GET','/api/drafts',{}),
                    ('schedule_page','GET','/drafts',{}),('series','GET','/api/series',{}),
                    ('analytics','GET','/api/analytics/dashboard?days=7&refresh=false',{}),
                    ('analytics_30','GET','/api/analytics/dashboard?days=30&refresh=false',{}),
                    ('recent_posts','GET','/api/recent-posts',{}),
                    ('next_move','POST','/api/strategy/recommend',{'json':{'brief':'Help beginners join our gym in Brixton','fresh':True,'post_only':True,'platforms':['instagram']}}),
                    ('generate','POST','/api/ai/generate',{'json':{'brief':'Write a gym tip','platforms':['instagram']}}),
                    ('compact_image','GET','/media/thumbnail/1' if (ROOT/'nova/thumbnails.py').exists() else '/media/download/1',{}),
                    ('css','GET','/static/nova.css?v=6.3',{}),('js','GET','/static/strategy.js?v=20261027',{})]
                for name,method,path,kwargs in ([] if browser_only else cases):
                    values=[]
                    for _ in range(samples):
                        start=time.perf_counter()
                        response=client.request(method,path,**kwargs)
                        elapsed=(time.perf_counter()-start)*1000
                        if response.status_code not in (200,303):
                            raise RuntimeError(f'{name} {response.status_code}: {response.text[:300]}')
                        values.append({'ms':round(elapsed,2),'bytes':len(response.content),
                            **{key:int(response.headers.get('x-benchmark-'+key,0)) for key in ('sql','provider','ai')}})
                    times=sorted(v['ms'] for v in values)
                    result['routes'][name]={'median_ms':statistics.median(times),'p95_ms':times[min(len(times)-1,int(len(times)*.95))],
                        'samples':values,'cache_control':response.headers.get('cache-control'),
                        'content_encoding':response.headers.get('content-encoding'),'wire_bytes':response.headers.get('content-length')}
                    print(name,result['routes'][name]['median_ms'],flush=True)
                    target=Path(output);target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
                if browser:
                    subprocess.run(['node', str(Path(__file__).with_name('benchmark_browser.cjs')),
                        f'http://127.0.0.1:{port}', str(Path(output).resolve().with_name(Path(output).stem+'-browser.json'))],
                        cwd=ROOT,check=True)
                with ThreadPoolExecutor(max_workers=4) as pool:
                    start=time.perf_counter()
                    responses=list(pool.map(lambda _:client.get('/api/drafts'),range(4)))
                    result['concurrent_drafts']={'wall_ms':round((time.perf_counter()-start)*1000,2),
                                                 'statuses':[r.status_code for r in responses]}
                    start=time.perf_counter()
                    responses=list(pool.map(lambda _:client.get('/api/analytics/dashboard?refresh=true'),range(4)))
                    result['concurrent_analytics']={'wall_ms':round((time.perf_counter()-start)*1000,2),
                        'statuses':[r.status_code for r in responses],
                        'provider_calls':sum(int(r.headers.get('x-benchmark-provider',0)) for r in responses)}
                if browser_only:
                    result['browser_runtime_sha256'] = runtime_digest()
                Path(output).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        finally:
            process.terminate()
            process.wait(timeout=15)
    target=Path(output);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--serve',action='store_true')
    parser.add_argument('--port',type=int,default=8791)
    parser.add_argument('--samples',type=int,default=5)
    parser.add_argument('--browser',action='store_true')
    parser.add_argument('--browser-only',action='store_true')
    parser.add_argument('--output',default='performance-results.json')
    args=parser.parse_args()
    serve(args.port) if args.serve else benchmark(args.output,args.port,args.samples,args.browser or args.browser_only,args.browser_only)
