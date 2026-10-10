import json
from datetime import timedelta
from io import BytesIO
from types import SimpleNamespace
from urllib.parse import urlsplit
import pytest
from PIL import Image
from sqlalchemy import select
from fastapi.testclient import TestClient
from test_account_integrity import account
from test_strategy_series import PROFILE
from nova import app as app_module, performance, strategy
from nova.app import app
from nova.db import SessionLocal, Draft, MediaAsset, PerformanceSnapshot, Brand, utcnow
from nova.storage import get_public_url
from nova.analytics_view import dashboard








def test_draft_filters_apply_before_pagination_and_preserve_search():
    client,uid,*_=account()
    with SessionLocal() as db:
        for i in range(31):db.add(Draft(user_id=uid,brief=f'New unposted {i}'))
        db.add(Draft(user_id=uid,brief='Older pottery success',status='published',updated_at=utcnow()-timedelta(days=2),variants_json=json.dumps({'instagram':{'posts':['A recognisable caption']}})))
        db.commit()
    html=client.get('/drafts?status=published&q=pottery').text
    assert 'Older pottery success' in html and 'A recognisable caption' in html
    assert 'New unposted' not in html and '1</strong> item on this page' in html
    other,*_=account()
    assert 'Older pottery success' not in other.get('/drafts?status=published').text


def view():
    now=utcnow()
    return dashboard({'instagram':{'connected':True,'followers':None}}, {'posts':[
        {'platform':'instagram','text':'Pottery tip','created_at':now.isoformat(),'likes':12,'comments':2,'shares':None,'views':None},
        {'platform':'instagram','text':'Class invitation','created_at':now.isoformat(),'likes':3,'comments':0,'shares':None,'views':None}]},now)


def test_performance_is_brand_scoped_and_expires():
    client,uid,*_=account()
    with SessionLocal() as db:
        db.info.update(brand_id=0,brand_user_id=uid)
        performance.record(db,uid,view())
        assert performance.context(db,uid)['evidence']['posts'][0]['likes']==12
        db.info['brand_id']=999
        assert performance.context(db,uid)['available'] is False
        db.info['brand_id']=0
        row=db.scalar(select(PerformanceSnapshot).where(PerformanceSnapshot.user_id==uid))
        row.fetched_at=utcnow()-timedelta(hours=25);db.commit()
        assert performance.context(db,uid)['available'] is False
        assert 'evidence' not in performance.context(db,uid)


def test_recommendation_receives_real_evidence_and_review_cannot_publish(monkeypatch):
    client,uid,*_=account()
    client.get('/api/strategy')
    assert client.post('/api/strategy/confirm',json={'strategy':PROFILE,'revision':0}).status_code==200
    with SessionLocal() as db:
        performance.record(db,uid,view())
    captured={}
    def model(uid,instruction,data):
        captured.update(data)
        return {'actions':[{'kind':'review','title':'Review audience questions '+str(i),'reason':'Choose one useful follow-up for beginners','brief':'Open your Instagram post and check for unanswered questions. Decide whether a reply would help.','effort':'5 minutes','platform':'instagram'} for i in range(3)]}
    monkeypatch.setattr(strategy,'model_json',model)
    result=client.post('/api/strategy/recommend',json={})
    assert result.status_code==200,result.text
    assert captured['performance']['evidence']['posts'][0]['likes']==12
    assert captured['performance']['evidence']['platforms']['instagram']['engagement_rate'] is None
    action=result.json()['items'][0]
    assert client.post(f'/api/strategy/actions/{action["id"]}/draft',json={}).status_code==400
    assert client.post(f'/api/strategy/actions/{action["id"]}/feedback',json={'status':'complete'}).status_code==200


def test_analytics_window_and_missing_values_are_truthful():
    now=utcnow()
    post={'platform':'instagram','created_at':(now-timedelta(days=15)).isoformat(),'likes':4,'comments':1}
    assert not dashboard({}, {'posts':[post]},now)['top_posts']
    result=dashboard({'instagram':{'connected':True}}, {'posts':[post]},now,window_days=30)
    assert result['platforms']['instagram']['likes']==4
    assert result['platforms']['instagram']['shares'] is None
    assert '30 days' in result['note']
    with pytest.raises(ValueError):dashboard({}, {'posts':[]},window_days=99)


def test_dashboard_refresh_stores_evidence_for_same_brand(monkeypatch):
    client,uid,*_=account()
    monkeypatch.setattr(app_module,'analytics_for_user',lambda *a:{'instagram':{'connected':True}})
    monkeypatch.setattr(app_module,'recent_posts_for_user',lambda *a,**k:{'posts':view()['top_posts']})
    assert client.get('/api/analytics/dashboard?days=30').status_code==200
    with SessionLocal() as db:
        assert performance.context(db,uid)['available'] is True
    assert client.get('/api/analytics/dashboard?days=999').status_code==400


def test_corrupt_snapshot_falls_back_and_invalid_metrics_are_missing():
    _,uid,*_=account()
    with SessionLocal() as db:
        db.add(PerformanceSnapshot(user_id=uid,payload_json='not-json'));db.commit()
        assert performance.context(db,uid)['available'] is False
    data=view()
    posts=[dict(data['top_posts'][0],likes=True),dict(data['top_posts'][1],likes=float('inf'))]
    result=dashboard({'instagram':{'connected':True,'followers':False}},{'posts':posts})
    assert result['summary']['likes'] is None
    assert result['summary']['followers'] is None
    assert all('Test a follow-up' not in item['title'] for item in result['recommendations'])






def test_recommendation_evidence_age_cannot_be_refreshed_by_new_snapshot(monkeypatch):
    from nova.db import StrategyAction
    from test_strategy_series import setup_strategy
    client,uid,items=setup_strategy(monkeypatch)
    with SessionLocal() as db:
        row=db.get(StrategyAction,items[0]['id'])
        payload=json.loads(row.payload_json)
        payload['performance_evidence']={'available':True,'checked_at':(utcnow()-timedelta(hours=25)).isoformat(),'note':'An old generation snapshot'}
        row.payload_json=json.dumps(payload);db.commit()
        performance.record(db,uid,view())
    action=client.get('/api/strategy/actions').json()['items'][0]
    assert action['stale'] is True
    result=client.post(f'/api/strategy/actions/{action["id"]}/draft',json={})
    assert result.status_code==409 and 'Performance evidence' in result.text




def test_nonfinite_provider_metrics_do_not_break_dashboard_response(monkeypatch):
    client,*_=account()
    monkeypatch.setattr(app_module,'analytics_for_user',lambda *a:{'instagram':{'connected':True}})
    monkeypatch.setattr(app_module,'recent_posts_for_user',lambda *a,**k:{'posts':[{'platform':'instagram','text':'Synthetic','created_at':utcnow().isoformat(),'likes':float('nan'),'comments':float('inf'),'shares':False}]})
    response=client.get('/api/analytics/dashboard')
    assert response.status_code==200
    assert all(response.json()['top_posts'][0][key] is None for key in ('likes','comments','shares'))
