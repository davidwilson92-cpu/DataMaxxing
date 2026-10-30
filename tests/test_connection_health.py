import json
from types import SimpleNamespace
import httpx
import pytest
from nova import connection_health as health, social
from nova.db import SessionLocal, SocialConnection
from nova.security import encrypt
from test_account_integrity import account


@pytest.mark.parametrize('platform,status,payload,expected', [
    ('facebook',400,{'error':{'code':190}},'reconnect'),
    ('instagram',400,{'error':{'code':102}},'reconnect'),
    ('tiktok',200,{'error':{'code':'access_token_invalid'}},'reconnect'),
    ('x',401,{},'reconnect'),
    ('x',429,{},'unavailable'),
    ('facebook',503,{},'unavailable'),
    ('instagram',200,{'id':'123'},'connected'),
    ('tiktok',200,{'data':{'user':{'open_id':'123'}},'error':{'code':'ok'}},'connected'),
])
def test_only_explicit_auth_failures_require_reconnect(monkeypatch,platform,status,payload,expected):
    monkeypatch.setattr(health.httpx,'get',lambda *a,**k:SimpleNamespace(status_code=status,json=lambda:payload))
    assert health.probe(platform,'https://provider.example.test','synthetic',{}) == expected


def test_network_failure_does_not_invalidate_credentials(monkeypatch):
    monkeypatch.setattr(health.httpx,'get',lambda *a,**k:(_ for _ in ()).throw(httpx.ReadTimeout('synthetic')))
    assert health.probe('instagram','https://provider.example.test','synthetic',{}) == 'unavailable'


def test_check_is_owned_cached_and_blocks_known_revoked_publication(monkeypatch):
    client,uid,*_ = account(); other,other_uid,*_ = account()
    with SessionLocal() as db:
        row=SocialConnection(user_id=uid,platform='instagram',account_id='synthetic',encrypted_access_token=encrypt('test-token'))
        stranger=SocialConnection(user_id=other_uid,platform='x',account_id='other',encrypted_access_token=encrypt('other-token'))
        db.add_all([row,stranger]); db.commit(); cid=row.id; other_id=stranger.id
    calls=[]
    monkeypatch.setattr(health,'probe',lambda *a: calls.append(a[0]) or 'reconnect')
    data=client.post('/api/connections/check',json={}).json()
    assert data == {'connections':[{'id':cid,'platform':'instagram','status':'reconnect'}]}
    assert client.post('/api/connections/check',json={}).status_code == 200 and calls == ['instagram']
    with SessionLocal() as db:
        assert json.loads(db.get(SocialConnection,other_id).metadata_json).get('connection_health') is None
        with pytest.raises(RuntimeError,match='Reconnect'):
            social.selected_connection(db,uid,'instagram',cid)
        assert db.get(SocialConnection,cid).encrypted_access_token  # No destructive credential deletion.


def test_refresh_does_not_overwrite_a_new_grant(monkeypatch):
    client,uid,*_ = account()
    with SessionLocal() as db:
        row=SocialConnection(user_id=uid,platform='x',account_id='synthetic',encrypted_access_token=encrypt('old'))
        db.add(row);db.commit();cid=row.id
    def replaced(*args):
        with SessionLocal() as db:
            row=db.get(SocialConnection,cid);row.encrypted_access_token=encrypt('new');row.metadata_json='{"new_grant":true}';db.commit()
        return 'reconnect'
    monkeypatch.setattr(health,'probe',replaced)
    client.post('/api/connections/check',json={})
    with SessionLocal() as db: assert json.loads(db.get(SocialConnection,cid).metadata_json) == {'new_grant':True}
