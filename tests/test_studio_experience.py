import json
import re
import pytest
from fastapi import HTTPException
from test_account_integrity import account
from nova.db import SessionLocal, SocialConnection
from nova.workspace import clean_text_history


def test_studio_connection_context_is_owner_scoped_and_escaped():
    client, uid, *_ = account()
    other, other_uid, *_ = account()
    with SessionLocal() as db:
        db.add(SocialConnection(user_id=uid, platform='x', account_id='ours', username='</script><script>unsafe</script>', encrypted_access_token='not-a-real-token'))
        db.add(SocialConnection(user_id=other_uid, platform='x', account_id='private-other', username='other-account', encrypted_access_token='not-a-real-token'))
        db.commit()
    page=client.get('/studio')
    assert page.status_code==200
    raw=re.search(r'<script id="studioConnections" type="application/json">(.*?)</script>',page.text).group(1)
    assert '</script>' not in raw and 'other-account' not in raw and 'not-a-real-token' not in page.text
    assert json.loads(raw)['x']==['</script><script>unsafe</script>']
    assert json.loads(re.search(r'<script id="studioConnections" type="application/json">(.*?)</script>',other.get('/studio').text).group(1))['x']==['other-account']


def test_text_history_is_bounded_and_only_contains_supported_text():
    history=clean_text_history([{'x':{'posts':['a'*6000]*8,'token':'secret'},'untrusted':{'posts':['bad']}}]*8)
    assert len(history)==3
    assert history[0]=={'x':{'posts':['a'*5000]*5}}
    with pytest.raises(HTTPException): clean_text_history({'not':'a list'})


def test_saved_text_history_round_trip_and_ownership():
    client,*_=account()
    other,*_=account()
    draft=client.post('/api/drafts',json={}).json()
    body={'brief':'A saved idea','platforms':['x'],'variants':{'x':{'posts':['New wording']}},'revision':draft['revision'],'workspace':{'text_history':[{'x':{'posts':['Earlier wording']}}]}}
    assert client.patch(f'/api/drafts/{draft["id"]}',json=body).status_code==200
    assert client.get(f'/api/drafts/{draft["id"]}').json()['workspace']['text_history']==body['workspace']['text_history']
    assert other.get(f'/api/drafts/{draft["id"]}').status_code==404


def test_connection_alone_does_not_claim_voice_is_learned():
    client,uid,*_=account()
    with SessionLocal() as db:
        db.add(SocialConnection(user_id=uid,platform='x',account_id='mock',encrypted_access_token='mock'))
        db.commit()
    page=client.get('/onboarding/writing-style')
    assert 'No voice profile is saved yet' in page.text
    assert 'already started analysing' not in page.text
