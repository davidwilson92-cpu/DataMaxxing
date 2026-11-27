"""Disposable SQLite/PostgreSQL query-plan benchmark using production ORM tables."""
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time
from datetime import timedelta

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
temporary = tempfile.TemporaryDirectory(prefix='zova-index-benchmark-')
database_url = 'sqlite:///' + (Path(temporary.name)/'index.db').as_posix()
if os.environ.get('ZOVA_TEST_POSTGRES'):
    from sqlalchemy import create_engine
    from sqlalchemy.engine import make_url
    fixture_url = make_url(os.environ['ZOVA_TEST_POSTGRES'])
    if fixture_url.host not in {'localhost', '127.0.0.1'} or not fixture_url.database.startswith('zova_test_'):
        raise RuntimeError('Performance fixtures require an isolated loopback test server')
    administrator = create_engine(fixture_url.set(database='postgres'), isolation_level='AUTOCOMMIT')
    with administrator.connect() as connection:
        # Refuse an existing database rather than overwrite another workload.
        connection.exec_driver_sql('CREATE DATABASE zova_test_performance')
    administrator.dispose()
    database_url = fixture_url.set(database='zova_test_performance').render_as_string(hide_password=False)
os.environ.update(DATABASE_URL=database_url,
                  ZOVA_SCHEMA_MODE='initialize', ZOVA_SCHEDULER_MODE='disabled')
from sqlalchemy import insert, text
from nova.db import Activity, Draft, ScheduledPost, User, engine, utcnow
import atexit
atexit.register(engine.dispose)
from scripts.prepare_performance_indexes import NAMES, prepare

now = utcnow()
with engine.begin() as connection:
    connection.execute(insert(User), [{'id': i, 'email':f'benchmark-{i}@example.test',
        'password_hash':'unusable-benchmark-fixture'} for i in range(1,51)])
    for model in (Draft, ScheduledPost, Activity):
        for index in model.__table__.indexes:
            if index.name in NAMES:
                index.drop(connection)
    for offset in range(0, 50000, 1000):
        rows = [{'user_id': 1+i%50, 'brand_id': (i//50)%4,
                 'updated_at': now-timedelta(seconds=i)} for i in range(offset, offset+1000)]
        connection.execute(insert(Draft), rows)
        connection.execute(insert(Activity), [{**row, 'platform':'instagram', 'draft_id': i+1, 'status':'published'}
                                               for i,row in enumerate(rows, start=offset)])
        connection.execute(insert(ScheduledPost), [{**row, 'platform':'instagram', 'draft_id':i+1,
            'scheduled_at':now+timedelta(seconds=i), 'content_json':'{}'} for i,row in enumerate(rows, start=offset)])

queries = {
    'draft_page': 'SELECT id, title FROM nova_drafts WHERE user_id=1 AND brand_id=0 ORDER BY updated_at DESC, id DESC LIMIT 100',
    'schedule_range': "SELECT id FROM nova_scheduled_posts WHERE user_id=1 AND brand_id=0 AND scheduled_at>=:start AND scheduled_at<:end ORDER BY scheduled_at, id LIMIT 100",
    'activity_links': 'SELECT draft_id, platform, url FROM nova_activity WHERE user_id=1 AND brand_id=0 AND draft_id IN (1,201,401,601,801) ORDER BY id DESC',
}
# Use ORM table names so a future table rename cannot benchmark a different query.
queries = {key: sql.replace('nova_drafts', Draft.__tablename__).replace('nova_scheduled_posts', ScheduledPost.__tablename__).replace('nova_activity', Activity.__tablename__)
           for key,sql in queries.items()}
parameters = {'start':now, 'end':now+timedelta(days=30)}
result = {'database':engine.dialect.name, 'rows_per_table':50000, 'owners':50, 'brands_per_owner':4, 'samples':100, 'before':{}, 'after':{}}
for phase in ('before', 'after'):
    if phase == 'after': prepare()
    with engine.connect() as connection:
        connection.exec_driver_sql('ANALYZE')
        for name, sql in queries.items():
            times = []
            for _ in range(100):
                started = time.perf_counter()
                connection.execute(text(sql), parameters).all()
                times.append((time.perf_counter()-started)*1000)
            if engine.dialect.name == 'postgresql':
                plan = connection.scalar(text('EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) '+sql), parameters)
            else:
                plan = [row[3] for row in connection.execute(text('EXPLAIN QUERY PLAN '+sql), parameters)]
            result[phase][name] = {'median_ms':round(statistics.median(times),3), 'p95_ms':round(sorted(times)[94],3), 'plan':plan}
target = root/('docs/performance/index-postgres.json' if engine.dialect.name == 'postgresql' else 'docs/performance/index-benchmark.json')
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
engine.dispose()
temporary.cleanup()
