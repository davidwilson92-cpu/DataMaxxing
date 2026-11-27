import io,json,time,statistics,random
from pathlib import Path
import httpx
from PIL import Image
rng=random.Random(1)
image=Image.frombytes('RGB',(1024,1024),rng.randbytes(1024*1024*3)); buffer=io.BytesIO();image.save(buffer,format='JPEG',quality=85);content=buffer.getvalue()
result={'workload':'Local production ASGI preview, disposable authenticated accounts, 1024x1024 synthetic JPEG, five samples, no external services','upload_bytes':len(content)}
for label,port in [('before',8799),('after',8798)]:
 base=f'http://127.0.0.1:{port}'
 with httpx.Client(base_url=base,follow_redirects=True,headers={'Origin':base,'X-Zova-Request':'1'},timeout=30) as client:
  assert client.get('/fixture/2').status_code==200
  times={k:[] for k in ['upload','save','reopen','navigation']}
  for i in range(5):
   start=time.perf_counter();r=client.post('/api/media',files={'files':('synthetic.jpg',content,'image/jpeg')});assert r.status_code==200,r.text
   times['upload'].append(round((time.perf_counter()-start)*1000,2));asset=r.json()['assets'][0]
   r=client.post('/api/drafts');assert r.status_code==200,r.text
   draft=r.json();did=draft['id']
   start=time.perf_counter();r=client.patch(f'/api/drafts/{did}',json={'brief':'Friday bouquet collection','revision':draft['revision'],'workspace':{'media_asset_ids':[asset['id']],'media':[asset]}});assert r.status_code==200,r.text
   times['save'].append(round((time.perf_counter()-start)*1000,2))
   start=time.perf_counter();r=client.get(f'/api/drafts/{did}');assert r.status_code==200 and r.json()['workspace']['media_asset_ids']==[asset['id']],r.text
   times['reopen'].append(round((time.perf_counter()-start)*1000,2))
   start=time.perf_counter();r=client.get('/campaigns');assert r.status_code==200
   times['navigation'].append(round((time.perf_counter()-start)*1000,2))
  result[label]={k:{'median_ms':statistics.median(v),'samples':v} for k,v in times.items()}
Path('outputs/confidence-media-learning/save-upload-benchmark.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
