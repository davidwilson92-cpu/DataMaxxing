"""Local-only disposable preview. No real accounts, providers or worker loop."""
import os, sys, json
from pathlib import Path
repo=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(repo/'tests'),str(repo)]
import conftest
os.environ.update(PUBLIC_BASE_URL='http://127.0.0.1:8784',STRIPE_MODE='off',PLAN_LIMITS_ENABLED='false',RATE_LIMIT_SCALE='20')
from nova.app import app
from nova import ai, strategy, trends, connection_health
from datetime import datetime, timezone, timedelta
from nova.db import SessionLocal,User,Draft,MediaAsset,SocialConnection,PublishReview,Publication,ScheduledPost
from nova.security import hash_password,encrypt

# pytest's autouse fixture does not run when this module is launched as a server.
# This preview must fail closed if a route unexpectedly reaches a real provider.
import httpx
def blocked_provider(*args,**kwargs):
    raise RuntimeError('External provider access is disabled in the local preview')
for method in ('get','post','put','patch','delete'):
    setattr(httpx,method,blocked_provider)
connection_health.probe = lambda *args: 'connected'  # Synthetic grants, never provider calls.
preview_batch=0
def mocked_json(uid,instruction,data):
    global preview_batch
    restaurant='restaurant' in (data.get('brief') or json.dumps(data.get('strategy',{}))).lower()
    if 'exactly three' in instruction:
        preview_batch+=1
        titles=['Share the restaurant dish guests keep asking about','Show how your restaurant prepares fresh pasta','Invite questions about the restaurant menu'] if restaurant else ['Share one tip for centring clay','Explain what beginners need for class','Invite questions about starting pottery']
        return {'actions':[{'kind':'draft' if data.get('post_only') else ('review' if title.startswith('Invite') else 'draft'),'title':title+(f' — angle {preview_batch}' if preview_batch>1 else ''),'reason':'Help local diners picture their next meal and book a table.' if restaurant else 'Help local beginners feel confident enough to try a pottery class.','brief':title,'effort':'10 minutes','needs':'A photo of a restaurant dish' if restaurant else 'A photo of your clay tools','platform':data.get('allowed_platforms',['instagram'])[0],'format':'post','source_id':'source-1' if title.startswith('Share') else ''} for title in titles]}
    return {'strategy':{'goal':'Generate restaurant table bookings' if restaurant else 'Generate pottery class enquiries','audience':'Local diners' if restaurant else 'Local beginners','offer':'Fresh seasonal restaurant dishes' if restaurant else 'Beginner pottery classes','voice':'Warm and practical','themes':'Restaurant dishes, seasonal ingredients, behind the kitchen' if restaurant else 'Beginner pottery tips, clay process, common questions','platforms':data.get('default_platforms') or ['instagram'],'rhythm':'Two posts each week','resources':'One hour a week','avoid':'Unsupported claims'},'assumptions':['Two posts weekly fits your available time; please confirm.']}
strategy.model_json=mocked_json
trends.discover=lambda themes,uid:{'topics':[{'id':'source-1','title':'Synthetic example: diners discuss restaurant menus' if 'restaurant' in themes.lower() else 'Synthetic example: beginners discuss pottery','summary':'A mocked public discussion for visual testing only','url':'https://example.org/restaurants' if 'restaurant' in themes.lower() else 'https://example.org/pottery','published_at':datetime.now(timezone.utc).date().isoformat(),'checked_at':datetime.now(timezone.utc).isoformat(),'kind':'public_social'}],'checked_at':datetime.now(timezone.utc).isoformat(),'note':'Synthetic preview: source cards are mocked. No real web or social search was made.'}
ai.generate_variants=lambda **kw:{p:{'posts':['Come behind the scenes at our restaurant. Fresh ingredients, carefully prepared. What would you order first?' if 'restaurant' in (kw.get('brief','')+kw.get('instruction','')).lower() else 'New to pottery? Start with a small piece of clay and give yourself time to learn. What would you like to try making?']} for p in kw['platforms']}
with SessionLocal() as db:
    user=User(email='strategy@example.test',studio_intro_pending=False,display_name='Synthetic creator',password_hash=hash_password('Synthetic-preview-2026!'));db.add(user);db.commit()
    from PIL import Image
    from nova.storage import UPLOAD_DIR
    UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
    Image.new('RGB',(80,80),(131,76,174)).save(UPLOAD_DIR/'creator-synthetic.png')
    media=MediaAsset(user_id=user.id,filename='Synthetic colour sample.png',mime_type='image/png',storage_key=str(UPLOAD_DIR/'creator-synthetic.png'),public_url='http://127.0.0.1:8784/media/raw/creator-synthetic.png',size_bytes=(UPLOAD_DIR/'creator-synthetic.png').stat().st_size)
    db.add(media);db.flush()
    db.add(Draft(user_id=user.id,workspace_json=json.dumps({'media_asset_ids':[media.id],'media':[{'id':media.id,'kind':'image','url':f'/media/preview/{media.id}','filename':'Synthetic colour sample.png'}]}),brief='Welcome to our pottery studio',title='A warm welcome to the studio',platforms_json='["instagram"]',variants_json='{"instagram":{"posts":["A warm welcome to our pottery studio."]}}'));db.flush()
    connections={}
    for platform,scope in [('instagram','instagram_business_basic,instagram_business_content_publish'),('facebook','pages_manage_posts,pages_read_engagement'),('x','tweet.write,tweet.read,users.read'),('tiktok','video.publish,user.info.basic')]:
        conn=SocialConnection(user_id=user.id,platform=platform,account_id='synthetic-'+platform,username='clayandkind',display_name='Clay & Kind',scope=scope,encrypted_access_token=encrypt('synthetic-never-valid'),metadata_json=json.dumps({'auth_provider':'instagram_login'} if platform=='instagram' else {}))
        db.add(conn);db.flush();connections[platform]=conn
    now=datetime.now(timezone.utc)
    fixtures=[]
    for title,caption,platforms,offset,status in [
        ('Three tips for your first pottery class','A little patience, a little clay. Save these three tips for your first class.',['instagram','facebook'],1,'scheduled'),
        ('What would you make first?','A mug, a bowl or something wonderfully wonky? Tell us your first pottery project.',['x'],2,'scheduled'),
        ('A quiet moment at the wheel','A slower moment in the studio. Watch a simple cylinder take shape.',['tiktok'],4,'scheduled'),
        ('Our weekend class is open','Our weekend beginners class is open for bookings. Bring your curiosity.',['facebook'],-2,'failed'),
        ('A small studio update','A look at the pieces our beginners made this week.',['instagram'],-1,'unknown'),
    ]:
        due=(now+timedelta(days=offset)).replace(hour=17 if offset%2 else 10,minute=30,second=0,microsecond=0)
        variants={p:{'posts':[caption]} for p in platforms}
        draft=Draft(user_id=user.id,title=title,brief=caption,platforms_json=json.dumps(platforms),variants_json=json.dumps(variants),status='needs_review' if status=='unknown' else status,revision=1,workspace_json=json.dumps({'media_asset_ids':[media.id] if 'instagram' in platforms else [],'instagram_format':'post'}))
        db.add(draft);db.flush()
        code=f'synthetic-review-{draft.id}'
        payload={'draft_id':draft.id,'revision':draft.revision,'platforms':platforms,'variants':variants,'media_asset_ids':[media.id] if 'instagram' in platforms else [],'link_url':'','publish_options':{'instagram':{'format':'post'}} if 'instagram' in platforms else {},'scheduled_utc':due.isoformat(),'timezone':'Europe/London','targets':{p:{'connection_id':connections[p].id,'account_id':connections[p].account_id,'posts':[caption],'link':''} for p in platforms}}
        db.add(PublishReview(code=code,user_id=user.id,draft_id=draft.id,revision=draft.revision,payload_json=json.dumps(payload),status='submitted',expires_at=now+timedelta(minutes=15)))
        for platform in platforms:
            result={'error':'Synthetic preview: this delivery failed before sending.'} if status=='failed' else {'error':'Synthetic preview: provider outcome is unconfirmed.'} if status=='unknown' else {}
            publication=Publication(user_id=user.id,draft_id=draft.id,platform=platform,connection_id=connections[platform].id,review_code=code,status=status,result_json=json.dumps(result))
            db.add(publication);db.flush()
            job=ScheduledPost(user_id=user.id,draft_id=draft.id,platform=platform,connection_id=connections[platform].id,content_json=json.dumps({'publication_id':publication.id,'review_code':code,'posts':[caption]}),media_asset_ids_json=json.dumps(payload['media_asset_ids']),scheduled_at=due,status=status,error=result.get('error'))
            db.add(job);db.flush();fixtures.append({'schedule':job.id,'draft':draft.id,'platform':platform,'status':status})
    for title,caption,platform in [('Meet the maker','The story behind our small pottery studio.','instagram'),('The question everyone asks','Do I need to be artistic to try pottery? Not at all.','x')]:
        db.add(Draft(user_id=user.id,title=title,brief=caption,platforms_json=json.dumps([platform]),variants_json=json.dumps({platform:{'posts':[caption]}})))
    db.commit()
    print('SYNTHETIC SCHEDULE FIXTURES '+json.dumps(fixtures),flush=True)
os.chdir(repo)
import uvicorn
uvicorn.run(app,host='127.0.0.1',port=8784,lifespan='off',access_log=False)
