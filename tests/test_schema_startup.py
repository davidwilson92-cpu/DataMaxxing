import os
import secrets
import subprocess
import sys
import pytest
from sqlalchemy import create_engine, text, inspect, event
from sqlalchemy.orm import Session
from sqlalchemy.exc import DBAPIError
from nova.db import Base, User, Draft, LegacyPublication, MfaSettings, MfaChallenge
from nova.migrations import run_migrations, run_legacy_queue_migration, run_mfa_migration
from nova.tenant_references import apply_references
from nova.schema_startup import schema_mode, verify_runtime_schema, verify_runtime_role
from test_tenant_registry import registry_db


def initialize(engine, initial):
    initial.drop_all(engine)
    Base.metadata.create_all(engine)
    run_migrations(engine)
    run_legacy_queue_migration(engine, LegacyPublication.__table__)
    run_mfa_migration(engine, (MfaSettings.__table__, MfaChallenge.__table__))
    apply_references(engine, writes_paused=True)


def test_postgres_defaults_to_verification_and_unknown_mode_refuses(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.delenv('ZOVA_SCHEMA_MODE', raising=False)
    assert schema_mode(SimpleNamespace(dialect=SimpleNamespace(name='postgresql'))) == 'verify'
    assert schema_mode(SimpleNamespace(dialect=SimpleNamespace(name='sqlite'))) == 'bootstrap'
    monkeypatch.setenv('ZOVA_SCHEMA_MODE','anything')
    with pytest.raises(RuntimeError,match='must be'): schema_mode(None)


def test_schema_verification_is_read_only_and_rejects_missing_guards(registry_db):
    engine, initial = registry_db
    initialize(engine, initial)
    statements = []
    def capture(conn, cursor, sql, parameters, context, many): statements.append(sql)
    event.listen(engine,'before_cursor_execute',capture)
    try:
        with engine.connect() as c: verify_runtime_schema(c,Base.metadata)
    finally:
        event.remove(engine,'before_cursor_execute',capture)
    assert not any(sql.lstrip().upper().startswith(('CREATE','ALTER','INSERT','UPDATE','DELETE','DROP')) for sql in statements)
    with engine.begin() as c:
        if engine.dialect.name == 'postgresql':
            c.execute(text('ALTER TABLE nova_drafts DISABLE TRIGGER zova_workspace_guard'))
        else:
            c.execute(text('DROP TRIGGER nova_drafts_workspace_update'))
    with engine.connect() as c, pytest.raises(RuntimeError,match='guards'):
        verify_runtime_schema(c,Base.metadata)


@pytest.mark.parametrize('corruption', ['column','version','table'])
def test_incomplete_schema_refuses_without_repair(registry_db, corruption):
    engine, initial = registry_db
    initialize(engine, initial)
    with engine.begin() as c:
        if corruption == 'column': c.execute(text('ALTER TABLE nova_drafts DROP COLUMN title'))
        elif corruption == 'table': c.execute(text('DROP TABLE zova_mfa_challenges'))
        else: c.execute(text("DELETE FROM zova_schema_migrations WHERE version='20261009_optional_mfa'"))
    with engine.connect() as c, pytest.raises(RuntimeError,match='incomplete'):
        verify_runtime_schema(c,Base.metadata)


def test_verify_mode_empty_database_does_not_create_tables(tmp_path):
    path = tmp_path/'empty.db'
    env = dict(os.environ,DATABASE_URL='sqlite:///'+path.as_posix(),ZOVA_SCHEMA_MODE='verify')
    result = subprocess.run([sys.executable,'-B','-c','import nova.db'],env=env,capture_output=True,text=True,timeout=30)
    assert result.returncode != 0 and 'Runtime schema is incomplete' in result.stderr
    engine=create_engine(env['DATABASE_URL'])
    assert inspect(engine).get_table_names() == []
    engine.dispose()


def test_offline_preparation_requires_explicit_credentials_and_flags(tmp_path):
    path=tmp_path/'prepared.db'
    url='sqlite:///'+path.as_posix()
    env=dict(os.environ,DATABASE_URL=url)
    env.pop('ZOVA_MIGRATION_DATABASE_URL',None)
    command=[sys.executable,'-B','scripts/prepare_database.py']
    result=subprocess.run(command+['--apply','--writes-paused'],env=env,capture_output=True,text=True,timeout=30)
    assert result.returncode != 0 and 'explicitly' in result.stderr
    assert not path.exists()
    env['ZOVA_MIGRATION_DATABASE_URL']=url
    result=subprocess.run(command+['--apply'],env=env,capture_output=True,text=True,timeout=30)
    assert result.returncode != 0 and 'writes-paused' in result.stderr
    assert not path.exists()
    result=subprocess.run(command+['--apply','--writes-paused'],env=env,capture_output=True,text=True,timeout=30)
    assert result.returncode == 0, result.stderr
    env['ZOVA_SCHEMA_MODE']='verify'
    result=subprocess.run([sys.executable,'-B','-c','import nova.db'],env=env,capture_output=True,text=True,timeout=30)
    assert result.returncode == 0, result.stderr


def test_real_restricted_postgres_login_can_run_app_but_not_change_schema(registry_db):
    engine, initial = registry_db
    if engine.dialect.name != 'postgresql':pytest.skip('Requires isolated PostgreSQL role permissions')
    initialize(engine,initial)
    role='zova_runtime_'+secrets.token_hex(8)
    password=secrets.token_hex(24)  # Synthetic, confined to the disposable loopback CI database.
    with engine.begin() as c:
        schema=c.scalar(text('SELECT current_schema()'))
        c.execute(text(f"CREATE ROLE {role} LOGIN PASSWORD '{password}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS"))
    restricted=None
    try:
        with engine.begin() as c:
            c.execute(text(f'GRANT USAGE ON SCHEMA {schema} TO {role}'))
            for name in Base.metadata.tables:
                c.execute(text(f'GRANT SELECT,INSERT,UPDATE,DELETE ON {schema}.{name} TO {role}'))
            c.execute(text(f'GRANT SELECT ON {schema}.zova_schema_migrations TO {role}'))
            c.execute(text(f'GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA {schema} TO {role}'))
        url=engine.url.set(username=role,password=password).update_query_dict({'options':f'-csearch_path={schema}'})
        restricted=create_engine(url)
        with restricted.connect() as c:
            verify_runtime_role(c);verify_runtime_schema(c,Base.metadata)
        # Verify the actual import and authenticated draft read under that login.
        env=dict(os.environ,DATABASE_URL=url.render_as_string(hide_password=False),ZOVA_SCHEMA_MODE='verify')
        code="""from nova.db import SessionLocal,User,Draft
from nova.security import make_user_session
from nova.app import app
from fastapi.testclient import TestClient
with SessionLocal() as db:
    user=User(email='restricted@example.test',password_hash='synthetic')
    db.add(user);db.flush()
    draft=Draft(user_id=user.id,brief='Restricted runtime draft')
    db.add(draft);db.commit();uid=user.id;did=draft.id
client=TestClient(app)
client.cookies.set('nova_session',make_user_session(uid))
assert client.get('/api/drafts/'+str(did)).status_code==200
"""
        result=subprocess.run([sys.executable,'-B','-c',code],env=env,capture_output=True,text=True,timeout=45)
        assert result.returncode == 0, result.stderr
        for attack in ('ALTER TABLE nova_drafts ADD COLUMN forbidden INTEGER',
                       'ALTER TABLE nova_drafts DISABLE TRIGGER zova_workspace_guard',
                       'DROP TABLE nova_drafts', 'TRUNCATE nova_drafts',
                       'CREATE TABLE forbidden_table (id INTEGER)',
                       'DELETE FROM zova_schema_migrations'):
            with pytest.raises(DBAPIError) as caught:
                with restricted.begin() as c:c.execute(text(attack))
            assert caught.value.orig.sqlstate == '42501'
        with engine.connect() as c, pytest.raises(RuntimeError,match='privileges'):
            verify_runtime_role(c)
        # A privileged session cannot disguise its ability to RESET ROLE.
        with engine.begin() as c:
            c.execute(text(f'SET LOCAL ROLE {role}'))
            with pytest.raises(RuntimeError,match='privileges'):verify_runtime_role(c)
        with engine.begin() as c:c.execute(text(f'GRANT pg_read_all_data TO {role}'))
        with restricted.connect() as c, pytest.raises(RuntimeError,match='privileges'):
            verify_runtime_role(c)
        with engine.begin() as c:c.execute(text(f'REVOKE pg_read_all_data FROM {role}'))
        with engine.begin() as c:c.execute(text(f'GRANT CREATE ON SCHEMA {schema} TO {role}'))
        with restricted.connect() as c, pytest.raises(RuntimeError,match='privileges'):
            verify_runtime_role(c)
    finally:
        if restricted:restricted.dispose()
        with engine.begin() as c:
            c.execute(text(f'DROP OWNED BY {role}'))
            c.execute(text(f'DROP ROLE {role}'))
