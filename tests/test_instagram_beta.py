"""Provider fixtures only: token lifecycle, granted scopes and race preservation."""
import json
import secrets
from datetime import timedelta
from types import SimpleNamespace

import pytest
from nova import social
from nova.db import SessionLocal, User, SocialConnection, utcnow
from nova.security import encrypt, decrypt


def response(payload, status=200):
    return SimpleNamespace(status_code=status, json=lambda: payload)


@pytest.mark.parametrize('envelope', [False, True])
def test_exchange_actual_grants_and_envelope(monkeypatch, envelope):
    monkeypatch.setenv('INSTAGRAM_APP_ID','synthetic')
    monkeypatch.setenv('INSTAGRAM_APP_SECRET','synthetic')
    short={'access_token':'short','user_id':'123','permissions':'instagram_business_basic'}
    monkeypatch.setattr(social.httpx,'post',lambda *a,**k:response({'data':[short]} if envelope else short))
    def get(url,**kwargs):
        if url.endswith('/access_token'): return response({'access_token':'long','expires_in':5184000})
        return response({'user_id':'123','username':'synthetic'})
    monkeypatch.setattr(social.httpx,'get',get)
    result=social.instagram_exchange('synthetic')
    assert result['scope']=='instagram_business_basic'
    assert result['long_lived'] is True and result['profile']['id']=='123'
    from nova.publishing_workflow import capability_error
    assert capability_error(SimpleNamespace(platform='instagram',scope=result['scope']),[]) is not None


def connection(db, **metadata):
    user=User(email=f'ig-beta-{secrets.token_hex(6)}@example.test', password_hash='unused')
    db.add(user);db.flush()
    conn=SocialConnection(user_id=user.id, platform='instagram', account_id='synthetic',
        encrypted_access_token=encrypt('original'),scope=social.INSTAGRAM_SCOPES,
        expires_at=utcnow()+timedelta(days=3),active=True,
        metadata_json=json.dumps({'auth_provider':'instagram_login','long_lived':True,
                                 'token_obtained_at':(utcnow()-timedelta(days=57)).timestamp(),**metadata}))
    db.add(conn);db.commit();return conn


def test_refresh_shared_backend_preserves_identity_and_grants(monkeypatch):
    calls=[]
    def get(url,**kwargs):
        calls.append((url,kwargs['params']['grant_type']))
        return response({'access_token':'renewed','expires_in':5184000})
    monkeypatch.setattr(social.httpx,'get',get)
    with SessionLocal() as db:
        conn=connection(db)
        assert social.access_token(conn,db)=='renewed'
        assert social.access_token(conn,db)=='renewed'
        assert len(calls)==1 and calls[0]==('https://graph.instagram.com/refresh_access_token','ig_refresh_token')
        assert conn.account_id=='synthetic' and conn.scope==social.INSTAGRAM_SCOPES
        assert decrypt(conn.encrypted_access_token)=='renewed'


@pytest.mark.parametrize('case',['expired','young','legacy','facebook'])
def test_refresh_eligibility_never_refreshes_wrong_token(case):
    with SessionLocal() as db:
        overrides={'young':{'token_obtained_at':utcnow().timestamp()},'legacy':{'long_lived':False},
                   'facebook':{'auth_provider':'facebook_login'}}.get(case,{})
        conn=connection(db,**overrides)
        if case=='expired':
            conn.expires_at=utcnow()-timedelta(seconds=1);db.commit()
            with pytest.raises(RuntimeError,match='expired'):social.access_token(conn,db)
        else: assert social.access_token(conn,db)=='original'


def test_failed_refresh_preserves_credentials(monkeypatch):
    monkeypatch.setattr(social.httpx,'get',lambda *a,**k:response({'error':'SECRET'},400))
    with SessionLocal() as db:
        conn=connection(db)
        with pytest.raises(RuntimeError,match='could not be renewed') as err: social.access_token(conn,db)
        assert 'SECRET' not in str(err.value)
        db.refresh(conn);assert decrypt(conn.encrypted_access_token)=='original' and conn.active


def test_concurrent_disconnect_cannot_be_undone(monkeypatch):
    with SessionLocal() as db:
        conn=connection(db)
        def get(*args,**kwargs):
            with SessionLocal() as other:
                row=other.get(SocialConnection,conn.id);row.active=False;other.commit()
            return response({'access_token':'renewed','expires_in':5184000})
        monkeypatch.setattr(social.httpx,'get',get)
        with pytest.raises(RuntimeError,match='connection changed'):social.access_token(conn,db)
        db.refresh(conn);assert not conn.active and decrypt(conn.encrypted_access_token)=='original'
