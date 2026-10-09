import asyncio
import secrets
from contextlib import contextmanager
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text, select, func
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from nova import db as models, readiness
from nova.database_services import create_services
from nova.service_permissions import TELEMETRY_COLUMN_GRANTS
from test_database_services import service_pools
from test_rls import rls_db
from test_tenant_registry import registry_db


@pytest.fixture
def telemetry_pool(service_pools):
    _,identity,admin,runtime,issuer,_,uids,drafts=service_pools
    role='zova_metrics_'+secrets.token_hex(8)
    password=secrets.token_hex(24)
    engine=None
    with admin.begin() as c:
        schema=c.scalar(text('SELECT current_schema()'))
        c.execute(text(f"CREATE ROLE {role} LOGIN PASSWORD '{password}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS"))
    try:
        with admin.begin() as c:
            c.execute(text(f'GRANT USAGE ON SCHEMA {schema} TO {role}'))
            for (table,operation),columns in TELEMETRY_COLUMN_GRANTS.items():
                c.execute(text(f'GRANT {operation} ({",".join(sorted(columns))}) ON {schema}.{table} TO {role}'))
        engine=create_engine(admin.url.set(username=role,password=password).update_query_dict(
            {'options':f'-csearch_path={schema}'}),hide_parameters=True,pool_size=2,max_overflow=0)
        services=create_services(identity,runtime,issuer,telemetry_engine=engine)
        yield services,engine,identity,admin,runtime,issuer,role,uids
    finally:
        if engine:engine.dispose()
        with admin.begin() as c:
            c.execute(text(f'DROP OWNED BY {role}'))
            c.execute(text(f'DROP ROLE {role}'))


def test_telemetry_role_is_append_only_and_startup_rejects_read_grants(telemetry_pool):
    services,engine,identity,admin,runtime,issuer,role,uids=telemetry_pool
    for attack in ('SELECT * FROM zova_ai_calls','SELECT * FROM zova_product_events',
                   'SELECT * FROM nova_users','SELECT * FROM nova_social_connections',
                   "UPDATE zova_product_events SET kind='published'",'DELETE FROM zova_ai_calls'):
        with pytest.raises(DBAPIError) as caught:
            with engine.begin() as c:c.execute(text(attack))
        assert caught.value.orig.sqlstate=='42501'
    with admin.begin() as c:
        c.execute(text(f'GRANT SELECT (user_id) ON zova_product_events TO {role}'))
    with pytest.raises(ValueError,match='manifest'):
        create_services(identity,runtime,issuer,telemetry_engine=engine)


def test_real_draft_save_records_metadata_and_survives_telemetry_outage(telemetry_pool,monkeypatch):
    from nova.app import app
    from nova import security,request_security
    services,engine,identity,admin,runtime,issuer,role,uids=telemetry_pool
    monkeypatch.setenv('PRODUCT_METRICS_ENABLED','true')
    attempts=[]
    def old_pool(*args,**kwargs):
        attempts.append(True)
        raise AssertionError('Shared credential fallback')
    for module in (models,security,request_security,readiness):monkeypatch.setattr(module,'SessionLocal',old_pool)
    previous=getattr(app.state,'database_services',None)
    app.state.database_services=services
    try:
        client=TestClient(app)
        client.headers['origin']='http://testserver'
        client.cookies.set('nova_session',security.make_user_session(uids[0],session_factory=services.identity_sessions))
        did=client.post('/api/drafts').json()['id']
        saved=client.patch(f'/api/drafts/{did}',json={'revision':0,'brief':'Private synthetic campaign'})
        assert saved.status_code==200,saved.text
        with Session(admin) as db:
            rows=db.scalars(select(models.ProductEvent)).all()
            assert [(r.key,r.user_id,r.kind) for r in rows]==[(f'{uids[0]}:revised:{did}:1',uids[0],'revised')]
        # A duplicate event is harmless, and its isolated transaction cannot
        # roll back the already committed content transaction.
        with readiness.telemetry_scope(services.telemetry_sessions):
            readiness.event(uids[0],'revised',f'{did}:1')
        with Session(admin) as db:assert db.scalar(select(func.count()).select_from(models.ProductEvent))==1
        failures=[]
        def unavailable():
            failures.append(True)
            raise RuntimeError('Synthetic measurement outage')
        app.state.database_services=replace(services,telemetry_sessions=unavailable)
        saved=client.patch(f'/api/drafts/{did}',json={'revision':1,'brief':'Saved despite telemetry outage'})
        assert saved.status_code==200 and saved.json()['revision']==2,saved.text
        assert client.get(f'/api/drafts/{did}').json()['brief']=='Saved despite telemetry outage'
        assert failures==[True] and attempts==[]
        with Session(admin) as db:assert db.scalar(select(func.count()).select_from(models.ProductEvent))==1
    finally:
        if previous is None:del app.state.database_services
        else:app.state.database_services=previous


def test_ai_metadata_uses_restricted_writer_without_storing_output(telemetry_pool,monkeypatch):
    from nova import ai
    services,engine,identity,admin,runtime,issuer,role,uids=telemetry_pool
    calls=[]
    payload={'status':'completed','output_text':'Private synthetic output',
             'usage':{'input_tokens':13,'output_tokens':7,'input_tokens_details':{'cached_tokens':2}}}
    def provider(*args,**kwargs):
        calls.append(True)
        return 'Private synthetic output',payload
    monkeypatch.setattr(ai,'_request_response',provider)
    monkeypatch.setattr(readiness,'SessionLocal',lambda:pytest.fail('Shared telemetry fallback'))
    token=readiness.ai_user.set(uids[0])
    try:
        with readiness.telemetry_scope(services.telemetry_sessions):
            assert ai._responses('Private synthetic prompt')=='Private synthetic output'
    finally:readiness.ai_user.reset(token)
    assert calls==[True]
    with Session(admin) as db:
        row=db.scalars(select(models.AICall)).one()
        assert (row.user_id,row.status,row.input_tokens,row.output_tokens,row.cached_tokens)==(uids[0],'returned',13,7,2)
        assert 'Private synthetic' not in str({column.name:getattr(row,column.name) for column in models.AICall.__table__.columns})


def test_request_background_work_keeps_the_restricted_telemetry_factory(telemetry_pool,monkeypatch):
    from fastapi import FastAPI, BackgroundTasks
    from nova.request_security import SecurityMiddleware
    services,engine,identity,admin,runtime,issuer,role,uids=telemetry_pool
    monkeypatch.setenv('PRODUCT_METRICS_ENABLED','true')
    monkeypatch.setattr(readiness,'SessionLocal',lambda:pytest.fail('Background shared-pool fallback'))
    test_app=FastAPI()
    test_app.state.database_services=services
    test_app.add_middleware(SecurityMiddleware)
    @test_app.get('/health')
    def background_probe(background: BackgroundTasks):
        background.add_task(readiness.event,uids[0],'visit','synthetic-background')
        return {'ok':True}
    assert TestClient(test_app).get('/health').status_code==200
    with Session(admin) as db:
        row=db.get(models.ProductEvent,f'{uids[0]}:visit:synthetic-background')
        assert row and row.user_id==uids[0]


def test_telemetry_failure_does_not_repeat_successful_ai_request(monkeypatch,caplog):
    from nova import ai
    calls=[]
    def provider(*args,**kwargs):
        calls.append(True)
        return 'Useful output',{'status':'completed','usage':{'input_tokens':1,'output_tokens':1}}
    monkeypatch.setattr(ai,'_request_response',provider)
    def unavailable():raise RuntimeError('Private diagnostic must not appear in log')
    with readiness.telemetry_scope(unavailable):
        assert ai._responses('Private prompt')=='Useful output'
    assert calls==[True]
    assert 'AI usage recording unavailable' in caplog.text
    assert 'Private diagnostic' not in caplog.text and 'Private prompt' not in caplog.text


def test_telemetry_scope_isolated_between_tasks_and_restored_after_errors(monkeypatch):
    monkeypatch.setenv('PRODUCT_METRICS_ENABLED','true')
    collected={1:[],2:[],3:[]}
    def factory(key):
        @contextmanager
        def session():
            class DB:
                def add(self,row):collected[key].append(row.user_id)
                def commit(self):pass
            yield DB()
        return session
    monkeypatch.setattr(readiness,'SessionLocal',factory(3))
    async def task(uid):
        with readiness.telemetry_scope(factory(uid)):
            await asyncio.sleep(0)
            readiness.event(uid,'visit','synthetic')
            with pytest.raises(RuntimeError):
                with readiness.telemetry_scope(readiness.unavailable_telemetry):
                    raise RuntimeError('Synthetic handler error')
            await asyncio.sleep(0)
            readiness.event(uid,'visit','after-error')
    async def run():await asyncio.gather(task(1),task(2))
    asyncio.run(run())
    readiness.event(3,'visit','outside-scope')
    assert collected=={1:[1,1],2:[2,2],3:[3]}
