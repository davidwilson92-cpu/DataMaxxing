import pytest
from nova import ai, readiness


def test_budget_exhaustion_retries_once_and_records_both_calls(monkeypatch):
    calls, records = [], []
    def request(prompt, *, max_output_tokens):
        calls.append(max_output_tokens)
        return ('partial', {'status':'incomplete','incomplete_details':{'reason':'max_output_tokens'}}) if len(calls)==1 else ('{"ok":true}', {'status':'completed'})
    monkeypatch.setattr(ai, '_request_response', request)
    monkeypatch.setattr(readiness, 'record_ai', lambda *args: records.append(args))
    assert ai._responses('Synthetic',max_output_tokens=3000) == '{"ok":true}'
    assert calls == [3000,6000]
    assert [r[1] for r in records] == ['incomplete_output','returned']


@pytest.mark.parametrize('payload', [{}, {'status':'incomplete','incomplete_details':{'reason':'content_filter'}}])
def test_other_empty_or_incomplete_output_is_not_retried(monkeypatch,payload):
    calls=[]
    monkeypatch.setattr(ai,'_request_response',lambda *a,**k:(calls.append(1) or '',payload))
    monkeypatch.setattr(readiness,'record_ai',lambda *a:None)
    with pytest.raises(RuntimeError): ai._responses('Synthetic')
    assert len(calls)==1


def test_repeated_budget_exhaustion_does_not_return_partial_json(monkeypatch):
    calls=[]
    monkeypatch.setattr(ai,'_request_response',lambda *a,**k:(calls.append(1) or '{',{'status':'incomplete','incomplete_details':{'reason':'max_output_tokens'}}))
    monkeypatch.setattr(readiness,'record_ai',lambda *a:None)
    with pytest.raises(RuntimeError): ai._responses('Synthetic')
    assert len(calls)==2


@pytest.mark.parametrize('model,expected', [('gpt-5-mini',{'effort':'low'}),('gpt-4.1-mini',None)])
def test_reasoning_setting_is_scoped_to_supported_default(monkeypatch,model,expected):
    monkeypatch.setenv('OPENAI_MODEL',model)
    monkeypatch.setenv('OPENAI_API_KEY','synthetic')
    class Response:
        status_code=200
        def json(self): return {'output_text':'ok'}
    def post(*args,**kwargs):
        assert kwargs['json'].get('reasoning') == expected
        return Response()
    monkeypatch.setattr(ai.httpx,'post',post)
    assert ai._request_response('Synthetic',max_output_tokens=3000)[0]=='ok'
