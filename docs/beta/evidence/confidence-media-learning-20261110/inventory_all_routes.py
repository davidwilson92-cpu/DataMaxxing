from pathlib import Path
import sys,csv
sys.path[:0]=['tests','.']
import conftest
from nova.app import app
rows=[]
def visit(routes,prefix=''):
 for r in routes:
  if hasattr(r,'original_router'):
   visit(r.original_router.routes,prefix+getattr(r.include_context,'prefix',''))
  elif hasattr(r,'path'):
   kind=type(r).__name__;path=prefix+r.path
   methods=sorted(getattr(r,'methods',None) or ['MOUNT'])
   for method in methods:rows.append((path,method,getattr(r,'name',''),kind,str(getattr(r,'include_in_schema',False))))
visit(app.routes)
path=Path('docs/beta/evidence/confidence-media-learning-20261110/complete-route-inventory.csv')
with path.open('w',newline='',encoding='utf-8') as f:
 w=csv.writer(f);w.writerow(['path','method','name','kind','openapi']);w.writerows(sorted(set(rows)))
print('Complete route operations/mounts:',len(set(rows)))
