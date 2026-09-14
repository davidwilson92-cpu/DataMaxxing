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
