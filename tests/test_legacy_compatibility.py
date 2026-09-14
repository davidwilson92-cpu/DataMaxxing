from test_account_integrity import account
from nova.db import SessionLocal, Creator
from nova.security import hash_api_key, encrypt
from nova import app as module


def test_existing_custom_gpt_route_keeps_auth_and_explicit_approval(monkeypatch):
    client, _, _, _ = account()
    with SessionLocal() as db:
        row=Creator(name='Synthetic',x_username='synthetic-legacy',api_key_hash=hash_api_key('synthetic-legacy-key'),encrypted_x_api_key=encrypt('mock'),encrypted_x_api_secret=encrypt('mock'),encrypted_x_access_token=encrypt('mock'),encrypted_x_access_token_secret=encrypt('mock'))
        db.add(row);db.commit()
    headers={'Authorization':'Bearer synthetic-legacy-key'}
    assert client.post('/x/preview',json={'text':'hello'}).status_code==401
    assert client.post('/x/preview',headers=headers,json={'text':'hello'}).status_code==200
    assert client.post('/x/post',headers=headers,json={'text':'hello','approved':False}).status_code==400
    calls=[]
    monkeypatch.setattr(module,'publish_legacy_creator',lambda *args: calls.append(args) or {'post_id':'mock','url':'https://example.test/mock'})
    assert client.post('/x/post',headers=headers,json={'text':'hello','approved':True}).status_code==200
    assert len(calls)==1
