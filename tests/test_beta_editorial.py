import importlib
import json
from types import SimpleNamespace
import pytest
from nova import ai
from nova.conversation import plan_message
from test_account_integrity import account


@pytest.mark.parametrize('message', [
    'Write an Instagram post for a £35 jacket. Do not claim waterproof.',
    'Draft a Facebook post for this Saturday at 10am. Do not include TEST DRAFT.',
    "Write a caption but don't publish it.",
])
def test_drafting_constraints_do_not_cancel_creation(message, monkeypatch):
    monkeypatch.setattr(ai, '_responses', lambda *a, **k: pytest.fail('Explicit drafting needs no intent model'))
    plan = plan_message(message, {'selected_platforms': ['instagram', 'facebook']})
    assert plan.action == 'create' and plan.brief == message


@pytest.mark.parametrize('scope', ['both captions', 'the two versions', 'all versions'])
def test_multi_platform_rewrite_scope(scope, monkeypatch):
    monkeypatch.setattr(ai, '_responses', lambda *a, **k: json.dumps({'action': 'rewrite', 'platforms': ['facebook'], 'brief': 'Shorten'}))
    context = {'selected_platforms':['instagram','facebook'], 'active_platform':'facebook', 'variants':{'instagram':{'posts':['Saturday']},'facebook':{'posts':['Saturday']}}}
    assert plan_message('Make ' + scope + ' under 45 words', context).platforms == ['instagram','facebook']


def test_rewrite_contract_retains_voice_and_exact_count(monkeypatch):
    captured = {}
    def response(prompt, **options):
        captured.update(prompt=prompt, **options)
        return '{"posts":["One £35 jacket. Calling it outfit research. 1, 2 or 3?"]}'
    monkeypatch.setattr(ai, '_responses', response)
    result = ai.rewrite_variant(platform='instagram', posts=['One £35 jacket'], action='instruction', instruction='Make both captions funnier', preferences=SimpleNamespace(example_posts='Calling it outfit research.'))
    assert len(result) == 1
    assert 'Calling it outfit research.' in captured['prompt']
    assert captured['response_schema']['properties']['posts']['maxItems'] == 1


def test_structured_response_keeps_no_storage(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','synthetic')
    def post(*a, **options):
        body = options['json']
        assert body['store'] is False
        assert body['text']['format']['strict'] is True
        assert body['text']['format']['schema']['properties']['posts']['minItems'] == 5
        return SimpleNamespace(status_code=200, json=lambda: {'output_text':'{}'})
    monkeypatch.setattr(ai.httpx,'post',post)
    ai._request_response('Synthetic', max_output_tokens=1000, response_schema=ai._posts_schema(5))


def test_supplied_numbers_can_be_analysed_without_social_connection(monkeypatch):
    module = importlib.import_module('nova.app')
    monkeypatch.setenv('OPENAI_API_KEY','synthetic')
    monkeypatch.setattr(module, 'analytics_for_user', lambda *a: {})
    monkeypatch.setattr(module, 'recent_posts_for_user', lambda *a, **k: {'posts':[]})
    monkeypatch.setattr(ai, 'analyse_performance', lambda **k: 'Based on your supplied figures, B converted 8 of 80 clicks: 10%.')
    client,*_ = account()
    result = client.post('/api/insights',json={'question':'Reel A 100 clicks, 2 sales; B 80 clicks, 8 sales. Compare.'})
    assert result.status_code == 200 and '10%' in result.json()['answer']
    assert result.json()['has_signal'] is False  # Never relabel supplied data as provider evidence.


def test_editorial_model_is_separate_and_restored_after_failure(monkeypatch):
    monkeypatch.setenv('OPENAI_MODEL', 'gpt-5-mini')
    monkeypatch.setenv('OPENAI_CONTENT_MODEL', 'gpt-6.1-terra')
    def fail(*a, **k):
        assert ai._model() == 'gpt-6.1-terra'
        raise RuntimeError('synthetic failure')
    monkeypatch.setattr(ai, '_responses', fail)
    with pytest.raises(RuntimeError): ai.editorial_response('synthetic')
    assert ai._model() == 'gpt-5-mini'


def test_performance_conversation_stays_accessible_without_cluttering_schedule():
    client, *_ = account()
    row = client.post('/api/drafts').json()
    body = {'revision': row['revision'], 'platforms': [], 'variants': {},
            'workspace': {'conversation_kind':'insight', 'conversation':[{'role':'user','content':'Compare my supplied figures'}]}}
    assert client.patch(f'/api/drafts/{row["id"]}',json=body).status_code == 200
    assert next(r for r in client.get('/api/drafts').json() if r['id']==row['id'])['kind'] == 'conversation'
    assert 'Compare my supplied figures' not in client.get('/drafts').text
    stored = client.get(f'/api/drafts/{row["id"]}').json()
    assert stored['workspace']['conversation'][0]['content'] == 'Compare my supplied figures'
    body.update(revision=stored['revision'], platforms=['instagram'], variants={'instagram':{'posts':['A real caption']}})
    assert client.patch(f'/api/drafts/{row["id"]}',json=body).status_code == 200
    assert next(r for r in client.get('/api/drafts').json() if r['id']==row['id'])['kind'] == 'post'
    assert 'A real caption' in client.get('/drafts').text
