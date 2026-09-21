import pytest
from nova.conversation import plan_message, ConversationPlan
from test_account_integrity import account


@pytest.mark.parametrize('message',['Do not publish this yet',"Don't schedule this",'Hold off posting; do not send'])
def test_negation_does_not_request_publication(message,monkeypatch):
    import nova.conversation as module
    monkeypatch.setattr(module.ai,'_responses',lambda *a,**k:pytest.fail('Negation must not need a model'))
    assert plan_message(message,{'selected_platforms':['x']}).action=='answer'


def test_creation_about_followers_is_not_analytics():
    result=plan_message('Write a post thanking my followers',{'selected_platforms':['instagram']})
    assert result.action=='create' and result.platforms==['instagram']
    result=plan_message('Write a post for all platforms except x',{'selected_platforms':['x','instagram']})
    assert result.platforms==['instagram']


def test_plan_only_reads_owned_drafts(monkeypatch):
    import nova.conversation as module
    client,_,_,_=account();other,_,_,_=account()
    row=client.post('/api/drafts',json={}).json()
    monkeypatch.setattr(module,'plan_message',lambda *a:ConversationPlan(action='publish',platforms=['x']))
    body={'message':'Publish this','draft_id':row['id'],'selected_platforms':['x']}
    assert other.post('/api/conversation/plan',json=body).status_code==404
    assert client.post('/api/conversation/plan',json=body).json()['action']=='publish'
    assert client.get(f"/api/drafts/{row['id']}").json()['status']=='draft'


@pytest.mark.parametrize('message', ['Why not?', 'yes', 'Go ahead'])
def test_acceptance_proposes_from_prior_topic_without_publishing(message, monkeypatch):
    import nova.conversation as module
    monkeypatch.setattr(module.ai, '_responses', lambda *a, **k: pytest.fail('Known topic can draft directly'))
    result = plan_message(message, {'selected_platforms':['instagram'], 'conversation':[
        {'role':'user','content':'Introduce our new Zova logo'},
        {'role':'assistant','content':'Would you like a first caption?'}]})
    assert result.action == 'create'
    assert result.platforms == ['instagram']
    assert result.brief == 'Introduce our new Zova logo'


def test_planner_keeps_context_and_defaults_to_selected_platform(monkeypatch):
    import nova.conversation as module
    def response(prompt, **kwargs):
        assert 'Instagram audience' in prompt
        assert 'editorial feedback' in prompt
        assert kwargs['max_output_tokens'] >= 3000
        return '{"action":"create","brief":"Introduce the Zova logo to our Instagram audience","reply":"Here is a first proposal."}'
    monkeypatch.setattr(module.ai, '_responses', response)
    result = plan_message('Why not?', {'selected_platforms':['instagram'], 'variants':{'instagram':{'posts':['Our new logo']}}, 'conversation':[{'role':'user','content':'Instagram audience'}]})
    assert result.platforms == ['instagram']
    assert 'Zova logo' in result.brief


def test_verbose_editorial_reply_is_kept_instead_of_failing(monkeypatch):
    import json
    import nova.conversation as module
    monkeypatch.setattr(module.ai,'_responses',lambda *a,**k:json.dumps({'action':'answer','reply':'Useful feedback. '*160}))
    result=plan_message('What will followers think?', {'selected_platforms':['instagram']})
    assert result.action == 'answer'
    assert result.reply.startswith('Useful feedback.') and len(result.reply)<=2000
