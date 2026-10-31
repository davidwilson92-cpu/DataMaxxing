"""Disposable SQLite query-plan benchmark using the three production ORM tables."""
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
os.environ.update(DATABASE_URL='sqlite:///' + (Path(temporary.name)/'index.db').as_posix(),
                  ZOVA_SCHEMA_MODE='initialize', ZOVA_SCHEDULER_MODE='disabled')
from sqlalchemy import insert, text
from nova.db import Activity, Draft, ScheduledPost, engine, utcnow
import atexit
atexit.register(engine.dispose)
from scripts.prepare_performance_indexes import NAMES, prepare

now = utcnow()
with engine.begin() as connection:
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
result = {'rows_per_table':50000, 'owners':50, 'brands_per_owner':4, 'samples':100, 'before':{}, 'after':{}}
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
            result[phase][name] = {'median_ms':round(statistics.median(times),3), 'p95_ms':round(sorted(times)[94],3),
                'plan':[row[3] for row in connection.execute(text('EXPLAIN QUERY PLAN '+sql), parameters)]}
target = root/'docs/performance/index-benchmark.json'
target.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
engine.dispose()
temporary.cleanup()
