from datetime import timedelta
import importlib
from nova.db import utcnow
from nova.analytics_view import dashboard, insight_fallback
from test_account_integrity import account


def test_question_uses_selected_30_day_window_and_preserves_unknowns(monkeypatch):
    module=importlib.import_module('nova.app')
    monkeypatch.setattr(module,'analytics_for_user',lambda *args: {'x':{'connected':True,'followers':None}})
    monkeypatch.setattr(module,'recent_posts_for_user',lambda *args,**kwargs:{'posts':[{'platform':'x','created_at':(utcnow()-timedelta(days=14)).isoformat(),'likes':9,'comments':None,'shares':None,'views':20}]})
    client,*_=account()
    response=client.post('/api/insights',json={'question':'How many likes?','days':30})
    assert response.status_code==200
    assert response.json()['summary']['likes']==9
    assert '30 days' in response.json()['answer'] and '9' in response.json()['answer']
    assert response.json()['summary']['comments'] is None
    recent=client.post('/api/insights',json={'question':'How many likes?','days':7}).json()
    assert recent['summary']['likes'] is None and 'unavailable' in recent['answer']
    assert client.post('/api/insights',json={'question':'likes','days':365}).status_code==422


def test_incomplete_accounts_do_not_become_a_winner_or_fake_zero():
    view=dashboard({'x':{'connected':True},'facebook':{'connected':True}}, {'posts':[], 'unavailable':['facebook']})
    answer=insight_fallback(view,'Which platform is performing best?',7)
    assert 'strongest' not in answer and 'leader' not in answer
    assert 'missing data is not zero' in insight_fallback(view,'views',7)


def test_help_points_to_current_controls_and_clear_account_information():
    client,*_=account()
    help=client.get('/help').text
    assert 'href="/studio?strategy=1"' in help and 'describe your goal' in help
    assert 'href="/drafts"' in help and 'edit its content or cancel' in help
    assert 'A snoozed suggestion returns after 24 hours' not in help
    page=client.get('/account#security').text
    assert 'id="aiPrivacyChoice"' in page
    assert 'Security and sessions' not in page
