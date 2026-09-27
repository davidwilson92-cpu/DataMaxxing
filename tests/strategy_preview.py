"""Local-only disposable preview. No real accounts, providers or worker loop."""
import os, sys, json
from pathlib import Path
repo=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(repo/'tests'),str(repo)]
import conftest
os.environ.update(PUBLIC_BASE_URL='http://127.0.0.1:8784',STRIPE_MODE='off',PLAN_LIMITS_ENABLED='false',RATE_LIMIT_SCALE='20')
from nova.app import app
from nova import ai, strategy
from nova.db import SessionLocal,User,Draft
from nova.security import hash_password
def mocked_json(uid,instruction,data):
    if 'exactly three' in instruction:
        return {'actions':[{'title':title,'reason':'Help local beginners feel confident enough to try a pottery class.','brief':title,'effort':'10 minutes','needs':'A photo of your clay tools','platform':'instagram','format':'post'} for title in ['Share one tip for centring clay','Explain what beginners need for class','Invite questions about starting pottery']]}
    return {'strategy':{'goal':'Generate pottery class enquiries','audience':'Local beginners','offer':'Beginner pottery classes','voice':'Warm and practical','themes':'Beginner tips, process, common questions','platforms':['instagram'],'rhythm':'Two posts each week','resources':'One hour a week','avoid':'Unsupported claims'},'assumptions':['Two posts weekly fits your available time; please confirm.']}
strategy.model_json=mocked_json
ai.generate_variants=lambda **kw:{p:{'posts':['New to pottery? Start with a small piece of clay and give yourself time to learn. What would you like to try making?']} for p in kw['platforms']}
with SessionLocal() as db:
    user=User(email='strategy@example.test',display_name='Synthetic creator',password_hash=hash_password('Synthetic-preview-2026!'));db.add(user);db.commit()
    db.add(Draft(user_id=user.id,brief='Welcome to our pottery studio',platforms_json='["instagram"]',variants_json='{"instagram":{"posts":["A warm welcome to our pottery studio."]}}'));db.commit()
os.chdir(repo)
import uvicorn
uvicorn.run(app,host='127.0.0.1',port=8784,lifespan='off',access_log=False)
