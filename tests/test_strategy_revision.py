"""Synthetic regression journeys for replacement strategies and late requests."""
import json
from fastapi import HTTPException
from sqlalchemy import select
from nova import strategy, ai
from nova.db import SessionLocal, Strategy, StrategyAction, Draft, Brand
from test_strategy_series import setup_strategy, PROFILE
from test_account_integrity import account


RESTAURANT = {**PROFILE, 'goal':'Fill weekday restaurant tables',
    'audience':'Local diners', 'themes':'Seasonal restaurant dishes',
    'description':'I now run a restaurant and want more weekday bookings.'}


def ideas(prefix='Restaurant'):
    return {'actions':[{'title':f'{prefix} idea {i}', 'reason':'Help local diners choose a weekday meal',
        'brief':f'Show the preparation of dish {i}', 'effort':'10 minutes',
        'needs':'A photo of your dish', 'platform':'instagram', 'format':'post'} for i in range(3)]}


def test_replacement_description_does_not_reuse_old_business_context(monkeypatch):
    c,uid,old=setup_strategy(monkeypatch)
    seen=[]
    def model(uid,instruction,data):
        seen.append(data)
        return {'strategy':RESTAURANT,'assumptions':['You can photograph your own dishes.']}
    monkeypatch.setattr(strategy,'model_json',model)
    revision=c.get('/api/strategy').json()['revision']
    proposal=c.post('/api/strategy/propose',json={'brief':RESTAURANT['description'],'revision':revision})
    assert proposal.status_code==200,proposal.text
    assert 'confirmed' not in seen[0] and 'topics' not in seen[0] and 'audience' not in seen[0]
    assert seen[0]['brief']==RESTAURANT['description']
    proposed=proposal.json()
    assert proposed['proposal']['strategy']['description']==RESTAURANT['description']
    saved=c.post('/api/strategy/confirm',json={'strategy':proposed['proposal']['strategy'],'revision':proposed['revision']})
    assert saved.status_code==200,saved.text
    assert c.get('/api/strategy').json()['confirmed']['description']==RESTAURANT['description']
    assert c.get('/api/strategy/actions').json()['items']==[]
    assert c.post(f'/api/strategy/actions/{old[0]["id"]}/draft',json={}).status_code==409
    with SessionLocal() as db:
        assert db.get(StrategyAction,old[0]['id']).status=='replaced'
    def restaurant_model(uid,instruction,data):
        assert data['strategy']['goal']==RESTAURANT['goal']
        assert data['feedback']==[], 'Old business recommendations must not steer the replacement plan'
        return ideas()
    monkeypatch.setattr(strategy,'model_json',restaurant_model)
    refreshed=c.post('/api/strategy/recommend',json={'revision':saved.json()['revision']})
    assert refreshed.status_code==200,refreshed.text
    assert all(a['title'].startswith('Restaurant') for a in refreshed.json()['items'])


def test_saving_strategy_preserves_draft_and_other_brand(monkeypatch):
    c,uid,old=setup_strategy(monkeypatch)
    monkeypatch.setattr(ai,'generate_variants',lambda **kw:{'instagram':{'posts':['Saved before the strategy changed.']}})
    drafted=c.post(f'/api/strategy/actions/{old[0]["id"]}/draft',json={}).json()['draft_id']
    with SessionLocal() as db:
        brand=Brand(user_id=uid,name='Second brand');db.add(brand);db.commit();bid=brand.id
    other_headers={'X-Zova-Brand':str(bid)}
    other=c.get('/api/strategy',headers=other_headers).json()
    c.post('/api/strategy/confirm',json={'strategy':PROFILE,'revision':other['revision']},headers=other_headers)
    assert c.post('/api/strategy/confirm',json={'strategy':RESTAURANT,'revision':1}).status_code==200
    assert c.get('/api/drafts/'+str(drafted)).json()['variants']['instagram']['posts']==['Saved before the strategy changed.']
    assert c.get('/api/strategy',headers=other_headers).json()['confirmed']['goal']==PROFILE['goal']
    assert c.get('/api/strategy').json()['confirmed']['goal']==RESTAURANT['goal']


def test_late_generation_cannot_attach_to_changed_strategy(monkeypatch):
    c,uid,old=setup_strategy(monkeypatch)
    def model(*args):
        changed=c.post('/api/strategy/confirm',json={'strategy':RESTAURANT,'revision':1})
        assert changed.status_code==200,changed.text
        return ideas('Old gym')
    monkeypatch.setattr(strategy,'model_json',model)
    response=c.post('/api/strategy/recommend',json={'revision':1})
    assert response.status_code==409,response.text
    assert c.get('/api/strategy/actions').json()['items']==[]
    with SessionLocal() as db:
        assert not any('Old gym' in a.payload_json for a in db.scalars(select(StrategyAction).where(StrategyAction.user_id==uid)))


def test_late_recommendation_cannot_replace_a_newer_batch(monkeypatch):
    c,uid,old=setup_strategy(monkeypatch)
    called=False
    def model(*args):
        nonlocal called
        if called:return ideas('Newer')
        called=True
        newer=c.post('/api/strategy/recommend',json={'revision':1})
        assert newer.status_code==200,newer.text
        return ideas('Older response')
    monkeypatch.setattr(strategy,'model_json',model)
    late=c.post('/api/strategy/recommend',json={'revision':1})
    assert late.status_code==409,late.text
    assert all(a['title'].startswith('Newer') for a in c.get('/api/strategy/actions').json()['items'])


def test_one_off_next_move_is_saved_without_silently_creating_strategy(monkeypatch):
    c,uid,*_=account();c.get('/api/strategy')
    captured=[]
    def model(uid,instruction,data):
        captured.append(data)
        return ideas('One-off')
    monkeypatch.setattr(strategy,'model_json',model)
    response=c.post('/api/strategy/recommend',json={'revision':0,'brief':'Show our new lunch menu','platforms':['instagram']})
    assert response.status_code==200,response.text
    assert c.get('/api/strategy').json()['confirmed']=={}
    assert captured[0]['strategy']['one_off'] is True
    rows=c.get('/api/strategy/actions').json()['items']
    assert len(rows)==3 and rows[0]['strategy_context']['goal']=='Show our new lunch menu'
    def draft(**kw):
        assert 'Show our new lunch menu' in kw['instruction']
        return {'instagram':{'posts':['A caption for the lunch menu.']}}
    monkeypatch.setattr(ai,'generate_variants',draft)
    ready=c.post(f'/api/strategy/actions/{rows[0]["id"]}/draft',json={})
    assert ready.status_code==200,ready.text
    assert c.get('/api/drafts/'+str(ready.json()['draft_id'])).json()['status']=='draft'


def test_one_off_needs_platform_and_preserves_saved_strategy(monkeypatch):
    c,uid,*_=setup_strategy(monkeypatch)
    assert c.post('/api/strategy/recommend',json={'brief':'A lunch menu'}).status_code==400
    assert c.post('/api/strategy/recommend',json={'revision':0}).status_code==409
    monkeypatch.setattr(strategy,'model_json',lambda *args:ideas())
    assert c.post('/api/strategy/recommend',json={'brief':'A lunch menu','platforms':['instagram']}).status_code==200
    assert c.get('/api/strategy').json()['confirmed']['goal']==PROFILE['goal']


def test_provider_http_failure_is_not_changed_to_generic_generation_error(monkeypatch):
    def unavailable(*args,**kwargs):
        raise HTTPException(403,'Enable AI assistance in Account to find ideas.')
    monkeypatch.setattr(ai,'_responses',unavailable)
    try:
        strategy.model_json(1,'Synthetic instruction',{})
    except HTTPException as error:
        assert error.status_code==403 and 'Enable AI' in error.detail
    else:
        assert False,'Expected the existing permission failure'


def test_unavailable_discovery_still_returns_honest_strategy_led_ideas(monkeypatch):
    c,uid,*_=setup_strategy(monkeypatch)
    def unavailable(*args):raise RuntimeError('Synthetic search outage')
    monkeypatch.setattr(strategy.trends,'discover',unavailable)
    monkeypatch.setattr(strategy,'model_json',lambda *args:ideas())
    response=c.post('/api/strategy/recommend',json={'revision':1})
    assert response.status_code==200,response.text
    assert 'unavailable' in response.json()['source_note']
    assert all(item['source'] is None for item in response.json()['items'])
