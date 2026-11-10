from datetime import timedelta

from nova import allowances
from nova.campaign_review import caption_date_warning
from nova.db import Brand, SessionLocal, utcnow
from test_account_integrity import account
from test_campaigns import brief
from test_campaign_refinement import plan


def test_resume_scoped_incomplete_brief_and_consume_once(monkeypatch):
    client, uid, *_ = account()
    other, *_ = account()
    monkeypatch.setattr(allowances, 'tier', lambda db, user: 'premium')
    path = '/api/campaign-brief'
    partial = dict(revision=0, idea='Four Saturday slots', timezone='Europe/London')
    assert client.post(path,json=partial).json()=={'revision':1}
    assert client.get(path).json()['brief']['idea']==partial['idea']
    assert other.get(path).json()=={'revision':0,'brief':None}
    with SessionLocal() as db:
        b=Brand(user_id=uid,name='Second');db.add(b);db.commit();brand=b.id
    assert client.get(path,headers={'X-Zova-Brand':str(brand)}).json()['brief'] is None
    assert client.post(path,json=partial).status_code==409
    assert client.post(path,json=dict(partial,revision=1,media=[999999])).status_code==404
    assert client.post('/api/campaigns',json=dict(brief(),brief_revision=0)).status_code==409
    assert client.post('/api/campaigns',json=dict(brief(),brief_revision=1)).status_code==200
    assert client.get(path).json()=={'revision':2,'brief':None}
    assert client.post('/api/campaigns',json=dict(brief(),brief_revision=1)).status_code==409
    assert client.post(path,json=partial).status_code==409
    monkeypatch.setattr(allowances, 'tier', lambda db,user: 'basic')
    assert client.get(path).status_code==402


def test_caption_warning_tracks_local_dates_and_recovers(plan):
    client,_,base,row=plan
    local=row['dates'][0]['local'][:16]
    payload=dict(caption='Tonight at six',platform='facebook',local_time=local,revision=row['revision'])
    first=client.post(base+'/posts/0',json=payload).json()
    assert not first['posts'][0].get('timing_warning')
    moved=(utcnow()+timedelta(days=10)).strftime('%Y-%m-%dT14:00')
    second=client.post(base+'/posts/0',json=dict(payload,local_time=moved,revision=first['revision'])).json()
    assert 'Tonight' in second['posts'][0]['timing_warning']
    client.post(base+'/accept',json={'revision':second['revision']}).raise_for_status()
    saved=client.get(base).json()
    assert 'Tonight' in saved['posts'][0]['timing_warning']
    post=saved['posts'][0]
    fixed=client.post(base+'/posts/0',json=dict(payload,caption='Join our next listening session.',local_time=moved,
        revision=saved['revision'],draft_revision=post['draft_revision'],series_revision=post['series_revision'])).json()
    assert not fixed['posts'][0].get('timing_warning')
    assert not caption_date_warning('Tomorrow at six','2027-03-28T01:30','2027-03-28T14:00')



def test_repetitive_followups_get_one_validated_rewrite(monkeypatch):
    import json
    from nova import ai
    client,*_=account()
    monkeypatch.setattr(allowances,'tier',lambda db,uid:'premium')
    cid=client.post('/api/campaigns',json=brief()).json()['id']
    prompts=[]
    def generate(prompt,**kwargs):
        prompts.append(prompt)
        lines=['Come to our Friday launch.']*2 if len(prompts)==1 else ['Meet the team on Friday.', 'What would you like us to show first?']
        return json.dumps({'posts':[{'caption':text} for text in lines]})
    monkeypatch.setattr(ai,'editorial_response',generate)
    result=client.post(f'/api/ai/campaigns/{cid}/plan',json={'revision':1})
    assert result.status_code==200 and len(prompts)==2
    assert result.json()['posts'][1]['caption']=='What would you like us to show first?'
