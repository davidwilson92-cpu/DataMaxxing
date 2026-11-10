from datetime import datetime, timedelta, timezone
import json

from nova import ai, allowances, performance
from nova.campaign_timing import suggest
from test_account_integrity import account
from test_campaigns import brief


def test_suggestions_need_comparable_platform_history_and_use_local_time():
    now=datetime(2027,1,15,tzinfo=timezone.utc)
    rows=[dict(platform='x',created_at=f'2027-01-{day:02d}T{hour}:30:00Z',likes=likes,comments=1)
          for day in range(1,4) for hour,likes in [('10',1),('18',7)]]
    dates=[dict(utc='2027-01-18T10:37:00+00:00')]*2
    choices=suggest(['x','instagram'],dates,'Europe/London',dict(available=True,evidence={'posts':rows}),now)
    assert '18:00' in choices[0]['local'] and '3 posting days' in choices[0]['reason']
    assert 'Test window' in choices[1]['reason']
    assert 'Test window' in suggest(['x'],dates,'Europe/London',{'available':False},now)[0]['reason']


def test_named_plan_preserves_owner_edits_and_uses_creator_context(monkeypatch):
    client,uid,*_=account()
    monkeypatch.setattr(allowances,'tier',lambda db,uid:'premium')
    monkeypatch.setattr(performance,'recommendation_context',lambda db,uid:{'available':False})
    prompts=[]
    def generate(prompt,**kwargs):
        prompts.append(prompt)
        return json.dumps(dict(name='Launch week',posts=[dict(caption='Launch day'),dict(caption='Behind the scenes')]))
    monkeypatch.setattr(ai,'editorial_response',generate)
    row=client.post('/api/campaigns',json=dict(brief(),name="Owner launch",recommend_times=True)).json()
    cid=row['id']
    plan=f'/api/ai/campaigns/{cid}/plan'
    row=client.post(plan,json={'revision':1}).json()
    assert row['name']=='Owner launch' and all(d.get('reason') for d in row['dates'])
    context=json.loads(prompts[0].split('\n',1)[1])
    assert context['creator']=='Original' and context['brief']==brief()['idea']
    assert 'voice' in context and 'strategy' in context and 'performance' in context
    rename=f'/api/campaigns/{cid}/name'
    renamed=client.post(rename,json={'revision':2,'name':'My autumn launch'}).json()
    assert renamed['name']=='My autumn launch'
    assert client.post(rename,json={'revision':2,'name':'Stale'}).status_code==409
    revised=client.post(plan,json={'revision':3,'feedback':'Keep it warm.'}).json()
    assert revised['name']==renamed['name'] and revised['dates']==row['dates']
    saved=client.post(f'/api/campaigns/{cid}/accept',json={'revision':4}).json()
    assert client.post(rename,json={'revision':saved['revision'],'name':'Live campaign'}).json()['name']=='Live campaign'
