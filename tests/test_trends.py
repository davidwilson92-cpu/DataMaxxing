import json
from datetime import datetime, timedelta, timezone
import pytest
from nova import trends, strategy, ai
from nova.db import SessionLocal, StrategyAction
from test_account_integrity import account
from test_strategy_series import PROFILE

NOW = datetime.now(timezone.utc)
URL = "https://example.org/pottery-news"

def evidence(**updates):
    return {"id":"source-1", "url":URL, "title":"Pottery event", "summary":"A local pottery discussion", "published_at":NOW.date().isoformat(), "checked_at":NOW.isoformat(), "kind":"web", **updates}

def provider(topic=None, cited=True, searched=True):
    topic = topic or evidence()
    return {"status":"completed", "output":[
        {"type":"web_search_call", "status":"completed" if searched else "failed", "action":{"sources":[{"url":URL}] if cited else []}},
        {"type":"message", "content":[{"type":"output_text", "text":json.dumps({"topics":[topic]})}]}]}

def wire(monkeypatch, payload):
    calls=[]
    class Response:
        def raise_for_status(self): pass
        def json(self): return payload
    def post(url, **kw): calls.append((url,kw)); return Response()
    monkeypatch.setattr(trends.httpx,'post',post)
    monkeypatch.setattr(ai,'_api_key',lambda:'synthetic-key')
    monkeypatch.setattr('nova.readiness.record_ai',lambda *args:None)
    return calls

def test_search_forces_live_tool_and_limits_private_context(monkeypatch):
    calls=wire(monkeypatch,provider())
    r=trends.discover('Pottery public themes',123)
    assert r['topics'][0]['url']==URL
    assert len(calls)==2
    bodies=[c[1]['json'] for c in calls]
    assert all(b['store'] is False and b['tool_choice']=='required' and b['max_tool_calls']==2 for b in bodies)
    assert all(b['tools'][0]['external_web_access'] for b in bodies)
    assert sum('filters' in b['tools'][0] for b in bodies)==1
    assert all(b['include']==['web_search_call.action.sources'] for b in bodies)
    assert all(json.loads(b['input'][1]['content'])=={'public_content_themes':'Pottery public themes'} for b in bodies)

@pytest.mark.parametrize('topic,cited,searched',[
    (evidence(url='https://fabricated.example/news'),True,True),
    (evidence(),False,True),(evidence(),True,False),
    (evidence(published_at=(NOW-timedelta(days=15)).date().isoformat()),True,True),
    (evidence(published_at=(NOW+timedelta(days=1)).date().isoformat()),True,True),
    (evidence(published_at=''),True,True)])
def test_rejects_uncited_undated_stale_or_unsearched_evidence(monkeypatch,topic,cited,searched):
    wire(monkeypatch,provider(topic,cited,searched))
    assert not trends._search('pottery','web',NOW,1)['items']

@pytest.mark.parametrize('url',['javascript:alert(1)','http://example.com','https://127.0.0.1/a','https://user:pass@example.com','https://localhost/a','https://foo.internal/a','https://example.com:8443/a',None])
def test_source_links_reject_unsafe_urls(url): assert not trends.safe_url(url)

def test_freshness_expires_after_24_hours():
    assert trends.source_is_fresh(evidence(),NOW)
    assert not trends.source_is_fresh(evidence(),NOW+timedelta(hours=25))

def test_partial_search_outage_keeps_web_evidence(monkeypatch):
    monkeypatch.setattr(ai,'_api_key',lambda:'synthetic')
    monkeypatch.setattr(trends,'_search',lambda themes,channel,now,uid: {'status':'checked','items':[evidence()]} if channel=='web' else {'status':'unavailable','items':[]})
    r=trends.discover('pottery',1)
    assert r['topics'] and 'social search unavailable' in r['note']

def prepared(monkeypatch, source_id='source-1'):
    c,uid,*_=account()
    rev=c.get('/api/strategy').json()['revision']
    c.post('/api/strategy/confirm',json={'strategy':PROFILE,'revision':rev})
    captured=[]
    monkeypatch.setattr(trends,'discover',lambda themes,uid:{'topics':[evidence()], 'note':'Web checked; Public social search checked.', 'checked_at':NOW.isoformat()})
    def response(uid,instruction,data):
        captured.append(data)
        return {'actions':[{'title':'Useful pottery move '+str(i),'reason':'Help beginners and generate class enquiries','brief':'Explain a pottery technique','effort':'5 minutes','platform':'instagram','source_id':source_id if i==0 else ''} for i in range(3)]}
    monkeypatch.setattr(strategy,'model_json',response)
    return c,uid,captured

def test_strategy_evidence_draft_grounding_and_expiry(monkeypatch):
    c,uid,captured=prepared(monkeypatch)
    r=c.post('/api/strategy/recommend',json={});assert r.status_code==200,r.text
    items=r.json()['items']; first=items[0]
    assert first['source']['url']==URL and not first['stale']
    assert not items[1]['source']
    assert captured[0]['strategy']['goal']==PROFILE['goal']
    assert captured[0]['recent_topics'][0]['url']==URL
    generated=[]
    def generate(**kw): generated.append(kw);return {'instagram':{'posts':['Synthetic grounded text']}}
    monkeypatch.setattr(ai,'generate_variants',generate)
    assert c.post(f'/api/strategy/actions/{first["id"]}/draft',json={}).status_code==200
    assert URL in generated[0]['instruction'] and PROFILE['goal'] in generated[0]['instruction']
    # An unlinked stale card cannot trigger another AI generation.
    with SessionLocal() as db:
        row=db.get(StrategyAction,items[1]['id']);p=json.loads(row.payload_json)
        p['source']=evidence(checked_at=(NOW-timedelta(days=2)).isoformat());row.payload_json=json.dumps(p);db.commit()
    assert c.get('/api/strategy/actions').json()['items'][1]['stale']
    assert c.post(f'/api/strategy/actions/{items[1]["id"]}/draft',json={}).status_code==409
    assert len(generated)==1

def test_invented_source_id_preserves_previous_actions(monkeypatch):
    c,uid,_=prepared(monkeypatch,'fabricated-source')
    assert c.post('/api/strategy/recommend',json={}).status_code==502
    assert not c.get('/api/strategy/actions').json()['items']

def test_refresh_identical_evidence_deduplicates_without_timestamp_key(monkeypatch):
    c,uid,_=prepared(monkeypatch)
    first=c.post('/api/strategy/recommend',json={}).json()['items']
    monkeypatch.setattr(trends,'discover',lambda *a:{'topics':[evidence(checked_at=(NOW+timedelta(seconds=1)).isoformat())],'note':'Checked again','checked_at':(NOW+timedelta(seconds=1)).isoformat()})
    second=c.post('/api/strategy/recommend',json={}).json()['items']
    assert [a['id'] for a in first]==[a['id'] for a in second]
    assert second[0]['source']['checked_at']!=first[0]['source']['checked_at']


def test_search_outage_is_explicit_and_no_key_makes_no_http(monkeypatch):
    def fail_key(): raise RuntimeError('No synthetic key')
    monkeypatch.setattr(ai,'_api_key',fail_key)
    assert 'not connected' in trends.discover('pottery',1)['note']
    calls=wire(monkeypatch,{'status':'incomplete','output':[]})
    result=trends.discover('pottery',1)
    assert not result['topics'] and 'unavailable' in result['note']
    assert len(calls)==2


def test_social_evidence_requires_actual_social_domain(monkeypatch):
    social=evidence(url='https://www.instagram.com/p/example/')
    payload=provider(social)
    payload['output'][0]['action']['sources']=[{'url':social['url']}]
    wire(monkeypatch,payload)
    result=trends._search('pottery','social',NOW,1)
    assert result['items'][0]['kind']=='public_social'
    wire(monkeypatch,provider())
    assert not trends._search('pottery','social',NOW,1)['items']
