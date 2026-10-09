import secrets
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from nova import db as models
from nova.database_services import create_services, RECOVERY_TABLE_GRANTS, RECOVERY_COLUMN_GRANTS
from test_authentication_pool import authentication_pool
from test_database_services import service_pools
from test_rls import rls_db
from test_tenant_registry import registry_db


@pytest.fixture
def recovery_pool(authentication_pool):
    _,authentication,identity,admin,runtime,issuer,_,uids=authentication_pool
    role='zova_recovery_'+secrets.token_hex(8)
    password=secrets.token_hex(24)
    engine=None
    with admin.begin() as c:
        schema=c.scalar(text('SELECT current_schema()'))
        c.execute(text(f"CREATE ROLE {role} LOGIN PASSWORD '{password}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS"))
    try:
        with admin.begin() as c:
            c.execute(text(f'GRANT USAGE ON SCHEMA {schema} TO {role}'))
            for table,operations in RECOVERY_TABLE_GRANTS.items():
                c.execute(text(f'GRANT {",".join(sorted(operations))} ON {schema}.{table} TO {role}'))
            for (table,operation),columns in RECOVERY_COLUMN_GRANTS.items():
                c.execute(text(f'GRANT {operation} ({",".join(sorted(columns))}) ON {schema}.{table} TO {role}'))
        engine=create_engine(admin.url.set(username=role,password=password).update_query_dict(
            {'options':f'-csearch_path={schema}'}),hide_parameters=True,pool_size=2,max_overflow=0)
        services=create_services(identity,runtime,issuer,authentication_engine=authentication,recovery_engine=engine)
        yield services,engine,admin,uids
    finally:
        if engine:engine.dispose()
        with admin.begin() as c:
            c.execute(text(f'DROP OWNED BY {role}'))
            c.execute(text(f'DROP ROLE {role}'))


def test_recovery_grants_do_not_include_mfa_billing_or_content():
    assert RECOVERY_COLUMN_GRANTS[('nova_users','UPDATE')]=={'password_hash','auth_version','updated_at'}
    assert set(RECOVERY_TABLE_GRANTS)=={'nova_users','zova_recovery_tokens','zova_mail_deliveries'}
    assert models.engine.hide_parameters


def test_restricted_recovery_lifecycle_and_delivery_failure(recovery_pool,monkeypatch):
    from nova.app import app
    from nova import security, recovery, request_security, readiness
    services,engine,admin,uids=recovery_pool
    for sql in ("UPDATE zova_mfa_settings SET enabled=false","UPDATE nova_users SET subscription_status='active'",
                "UPDATE nova_users SET email='forged@example.test'",'SELECT * FROM nova_social_connections'):
        with pytest.raises(DBAPIError) as caught:
            with engine.begin() as c:c.execute(text(sql))
        assert caught.value.orig.sqlstate=='42501'
    password='Original-synthetic-password!'
    with Session(admin) as db:
        user=db.get(models.User,uids[0]);user.password_hash=security.hash_password(password)
        email=user.email;db.commit()
    previous=getattr(app.state,'database_services',None)
    app.state.database_services=services
    def forbidden(*args,**kwargs):raise AssertionError('Shared credentials must not be used')
    for module in (models,security,recovery,request_security):monkeypatch.setattr(module,'SessionLocal',forbidden)
    monkeypatch.setattr(readiness,'event',lambda *args,**kwargs:None)
    monkeypatch.setattr(recovery,'recovery_ready',lambda:True)
    sent=[]
    monkeypatch.setattr(recovery,'smtp_message',lambda email,subject,body:sent.append((email,body)))
    def client():return TestClient(app,headers={'origin':'http://testserver'},follow_redirects=False)
    try:
        owner=client()
        old=security.make_user_session(uids[0],session_factory=services.identity_sessions)
        owner.cookies.set('nova_session',old)
        replacement='Changed-synthetic-password!'
        changed=owner.post('/account/password',data={'current_password':password,
            'new_password':replacement,'new_password_confirmation':replacement})
        assert changed.status_code==303 and changed.headers['location']=='/account?saved=password',changed.text
        assert security.user_from_session(old,session_factory=services.identity_sessions) is None
        assert owner.get('/api/drafts').status_code==200
        before_reset=owner.cookies.get('nova_session')
        known=owner.post('/forgot-password',data={'email':email})
        missing=owner.post('/forgot-password',data={'email':'missing@example.test'})
        assert known.status_code==missing.status_code==303
        assert known.headers['location']==missing.headers['location']
        assert len(sent)==1 and sent[0][0]==email
        token=sent[0][1].split('#token=',1)[1].split()[0]
        with Session(admin) as db:
            assert db.get(models.RecoveryToken,token) is None
            assert db.get(models.RecoveryToken,security.hash_api_key(token)) is not None
            assert db.scalar(select(models.MailDelivery.status))=='sent'
        body={'token':token,'password':'Recovered-synthetic-password!','confirmation':'Recovered-synthetic-password!'}
        first,second=client(),client()
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes=list(pool.map(lambda c:c.post('/reset-password',data=body).status_code,[first,second]))
        assert sorted(outcomes)==[303,400]
        assert security.user_from_session(before_reset,session_factory=services.identity_sessions) is None
        signed_in=client()
        assert signed_in.post('/login',data={'email':email,'password':body['password']}).status_code==303
        assert signed_in.get('/api/drafts').status_code==200
        def failed_delivery(address,subject,message):
            sent.append((address,message))
            raise RuntimeError('Synthetic delivery failure')
        monkeypatch.setattr(recovery,'smtp_message',failed_delivery)
        assert owner.post('/forgot-password',data={'email':email}).headers['location']==known.headers['location']
        failed_token=sent[-1][1].split('#token=',1)[1].split()[0]
        with Session(admin) as db:
            assert db.get(models.RecoveryToken,security.hash_api_key(failed_token)).used
            assert sorted(db.scalars(select(models.MailDelivery.status)))==['failed','sent']
            assert db.get(models.User,uids[1]).auth_version==0
        assert client().post('/reset-password',data={**body,'token':failed_token}).status_code==400
    finally:
        if previous is None:del app.state.database_services
        else:app.state.database_services=previous
