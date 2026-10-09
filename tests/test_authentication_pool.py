import re
import secrets
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from nova import db as models
from nova.database_services import create_services, AUTH_TABLE_GRANTS, AUTH_COLUMN_GRANTS
from test_database_services import service_pools
from test_rls import rls_db
from test_tenant_registry import registry_db


@pytest.fixture
def authentication_pool(service_pools):
    _,identity,admin,runtime,issuer,_,uids,drafts=service_pools
    role='zova_auth_'+secrets.token_hex(8)
    password=secrets.token_hex(24)
    engine=None
    with admin.begin() as c:
        schema=c.scalar(text('SELECT current_schema()'))
        c.execute(text(f"CREATE ROLE {role} LOGIN PASSWORD '{password}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS"))
    try:
        with admin.begin() as c:
            c.execute(text(f'GRANT USAGE ON SCHEMA {schema} TO {role}'))
            for table,operations in AUTH_TABLE_GRANTS.items():
                c.execute(text(f'GRANT {",".join(sorted(operations))} ON {schema}.{table} TO {role}'))
            for (table,operation),columns in AUTH_COLUMN_GRANTS.items():
                c.execute(text(f'GRANT {operation} ({",".join(sorted(columns))}) ON {schema}.{table} TO {role}'))
        engine=create_engine(admin.url.set(username=role,password=password).update_query_dict(
            {'options':f'-csearch_path={schema}'}),hide_parameters=True,pool_size=2,max_overflow=0)
        services=create_services(identity,runtime,issuer,authentication_engine=engine)
        yield services,engine,identity,admin,runtime,issuer,role,uids
    finally:
        if engine:engine.dispose()
        with admin.begin() as c:
            c.execute(text(f'DROP OWNED BY {role}'))
            c.execute(text(f'DROP ROLE {role}'))


def test_authentication_manifest_does_not_grant_password_or_workspace_mutation():
    assert AUTH_TABLE_GRANTS['nova_users']=={'SELECT'}
    assert AUTH_COLUMN_GRANTS[('nova_users','UPDATE')]=={'last_login_at','auth_version','updated_at'}
    assert 'zova_workspace_memberships' not in AUTH_TABLE_GRANTS


def test_authentication_pool_rejects_excess_column_grants(authentication_pool):
    _,engine,identity,admin,runtime,issuer,role,uids=authentication_pool
    for sql in ('SELECT * FROM nova_drafts',"UPDATE nova_users SET password_hash='forged'",
                "UPDATE nova_users SET email='forged@example.test'",'UPDATE nova_users SET active=false',
                "UPDATE zova_workspace_memberships SET role='owner'",'DELETE FROM zova_mfa_settings'):
        with pytest.raises(DBAPIError) as caught:
            with engine.begin() as c:c.execute(text(sql))
        assert caught.value.orig.sqlstate=='42501'
    with admin.begin() as c:
        schema=c.scalar(text('SELECT current_schema()'))
        c.execute(text(f'GRANT UPDATE (password_hash) ON {schema}.nova_users TO {role}'))
    with pytest.raises(ValueError,match='column grants'):
        create_services(identity,runtime,issuer,authentication_engine=engine)


def test_login_optional_mfa_recovery_logout_with_no_shared_pool(authentication_pool,monkeypatch):
    from nova.app import app
    from nova import security, request_security, readiness, mfa
    services,_,_,admin,_,_,_,uids=authentication_pool
    password='Synthetic-passphrase-2026!'
    with Session(admin) as db:
        user=db.get(models.User,uids[0]);user.password_hash=security.hash_password(password)
        email=user.email;db.commit()
    previous=getattr(app.state,'database_services',None)
    app.state.database_services=services
    def forbidden(*args,**kwargs):raise AssertionError('Shared credentials must not be used')
    for module in (models,security,request_security):monkeypatch.setattr(module,'SessionLocal',forbidden)
    monkeypatch.setattr(readiness,'event',lambda *args,**kwargs:None)
    now=int(mfa.time.time())
    monkeypatch.setattr(mfa.time,'time',lambda:now)
    def client():return TestClient(app,headers={'origin':'http://testserver'},follow_redirects=False)
    def password_login():
        user=client()
        response=user.post('/login',data={'email':email,'password':password,'next':'/api/drafts'})
        assert response.status_code==303,response.text
        return user,response
    try:
        owner=client()
        assert owner.get('/login').status_code==200
        assert owner.get('/mfa/setup').status_code==401
        invalid=owner.post('/login',data={'email':email,'password':'invalid'})
        assert invalid.status_code==303 and 'Incorrect' in invalid.headers['location']
        assert 'nova_session' not in owner.cookies
        owner,response=password_login()
        assert response.headers['location']=='/api/drafts'
        assert owner.get('/api/drafts').status_code==200
        original_cookie=owner.cookies.get('nova_session')
        # No automatic enrollment: an existing password-only account still works.
        with Session(admin) as db:assert db.get(models.MfaSettings,uids[0]) is None
        assert owner.post('/mfa/setup',data={'password':password}).status_code==200
        with Session(admin) as db:secret=security.decrypt(db.get(models.MfaSettings,uids[0]).encrypted_secret)
        response=owner.post('/mfa/enable',data={'code':mfa.totp(secret,now//30)})
        assert response.status_code==200,response.text
        codes=re.findall(r'<code>([0-9a-f-]{23})</code>',response.text)
        assert len(codes)==10
        assert security.user_from_session(original_cookie,session_factory=services.identity_sessions) is None
        assert owner.get('/api/drafts').status_code==200
        with Session(admin) as db:
            assert db.get(models.User,uids[1]).auth_version==0
            assert db.get(models.MfaSettings,uids[1]) is None
        pending,response=password_login()
        assert response.headers['location']=='/mfa/challenge'
        assert 'nova_session' not in pending.cookies
        assert pending.get('/api/drafts').status_code==401
        assert 'invalid or already used' in pending.post('/mfa/challenge',data={'code':'wrong'}).text
        response=pending.post('/mfa/challenge',data={'code':mfa.totp(secret,now//30+1)})
        assert response.status_code==303,response.text
        assert pending.get('/api/drafts').status_code==200
        assert pending.post('/mfa/challenge',data={'code':codes[0]}).status_code==400
        first,_=password_login();second,_=password_login()
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes=list(pool.map(lambda c:c.post('/mfa/challenge',data={'code':codes[0]}).status_code,[first,second]))
        assert sorted(outcomes)==[200,303]
        logged_in=first if outcomes[0]==303 else second
        token=logged_in.cookies.get('nova_session')
        assert logged_in.post('/logout').status_code==303
        assert 'nova_session' not in logged_in.cookies
        assert security.user_from_session(token,session_factory=services.identity_sessions) is None
        assert owner.post('/mfa/disable',data={'password':password,'code':codes[1]}).status_code==303
        with Session(admin) as db:assert not db.get(models.MfaSettings,uids[0]).enabled
        plain,response=password_login()
        assert response.headers['location']=='/api/drafts'
        assert plain.get('/api/drafts').status_code==200
    finally:
        if previous is None:del app.state.database_services
        else:app.state.database_services=previous
