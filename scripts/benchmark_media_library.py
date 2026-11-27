"""Disposable representative media-library workload; never uses deployment data."""
import csv
import json
from pathlib import Path
import statistics
import sys
import time
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'tests'),str(Path(__file__).resolve().parents[1])]
import conftest
from sqlalchemy import event
from nova.app import app
from nova.db import Draft, MediaAsset, SessionLocal, engine
from test_account_integrity import account

client,uid,*_=account()
with SessionLocal() as db:
    assets=[MediaAsset(user_id=uid,filename=f'Product {i}.jpg',mime_type='image/jpeg',storage_key='synthetic',size_bytes=1000) for i in range(500)]
    db.add_all(assets);db.flush()
    db.add_all([Draft(user_id=uid,title=f'Post {i}',workspace_json=json.dumps({'media_asset_ids':[assets[i%500].id]})) for i in range(1000)])
    db.commit()
queries=[]
def count(*args):queries.append(1)
event.listen(engine,'before_cursor_execute',count)
measure=[]
for _ in range(8):
    queries.clear();start=time.perf_counter();r=client.get('/api/media/library')
    assert r.status_code==200 and len(r.json()['assets'])==30
    measure.append({'ms':round((time.perf_counter()-start)*1000,2),'queries':len(queries),'bytes':len(r.content)})
target=Path('outputs/confidence-media-learning');target.mkdir(parents=True,exist_ok=True)
result={'workload':'1000 drafts, 500 owned assets, 30-item page; isolated SQLite, local TestClient; no provider calls',
        'samples':measure,'median_ms':statistics.median(x['ms'] for x in measure)}
(target/'library-benchmark.json').write_text(json.dumps(result,indent=2))
with (target/'route-inventory.csv').open('w',newline='',encoding='utf-8') as output:
    writer=csv.writer(output);writer.writerow(['path','methods','endpoint','evidence'])
    for path,operations in sorted(app.openapi()['paths'].items()):
        for method,operation in operations.items():
            if method in ('get','post','put','patch','delete','head','options'):
                writer.writerow([path,method.upper(),operation.get('operationId'),'Inventory only; execution coverage is mapped in the review report'])
print(json.dumps(result))
