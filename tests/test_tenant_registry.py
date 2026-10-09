"""Isolated registry backfill and capability tests; never use customer data."""
import os
import uuid
import pytest
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, text, select, inspect, update
from sqlalchemy.exc import IntegrityError
from nova.tenant_migration import apply_registry, inspect_mapping, verify_registry, MappingError, workspace_key
from nova.capabilities import permits


@pytest.fixture
def registry_db():
    url = os.environ.get('ZOVA_TEST_POSTGRES')
    admin = None
    schema = None
    if url:
        from sqlalchemy.engine import make_url
        parsed = make_url(url)
        assert parsed.host in {'localhost','127.0.0.1'} and parsed.database.startswith('zova_test_')
        admin = create_engine(url)
        schema = 'tenant_registry_' + uuid.uuid4().hex
        with admin.begin() as c:
            c.execute(text(f'CREATE SCHEMA {schema}'))
        engine = create_engine(url, connect_args={'options':f'-csearch_path={schema}'})
    else:
        engine = create_engine('sqlite://')
    metadata = MetaData()
    users = Table('nova_users', metadata, Column('id', Integer, primary_key=True), Column('password_hash', String), Column('auth_version', Integer))
    brands = Table('zova_brands', metadata, Column('id', Integer, primary_key=True), Column('user_id', Integer), Column('name', String))
    drafts = Table('nova_drafts', metadata, Column('id', Integer, primary_key=True), Column('user_id', Integer), Column('brand_id', Integer), Column('content', String))
    tokens = Table('nova_social_connections', metadata, Column('id', Integer, primary_key=True), Column('user_id', Integer), Column('brand_id', Integer), Column('encrypted_access_token', String))
    metadata.create_all(engine)
    with engine.begin() as c:
        c.execute(users.insert(), [{'id':1,'password_hash':'synthetic-hash-one','auth_version':3},{'id':2,'password_hash':'synthetic-hash-two','auth_version':7}])
        c.execute(brands.insert(), [{'id':10,'user_id':1,'name':'First brand'},{'id':20,'user_id':2,'name':'Second brand'}])
        c.execute(drafts.insert(), [{'id':1,'user_id':1,'brand_id':0,'content':'private draft one'},{'id':2,'user_id':2,'brand_id':20,'content':'private draft two'}])
        c.execute(tokens.insert(), [{'id':1,'user_id':1,'brand_id':10,'encrypted_access_token':'synthetic-opaque-token'}])
    try:
        yield engine, metadata
    finally:
        engine.dispose()
        if admin:
            with admin.begin() as c:
                c.execute(text(f'DROP SCHEMA {schema} CASCADE'))
            admin.dispose()


def snapshot(c, metadata):
    return {name:list(c.execute(select(table).order_by(table.c.id))) for name,table in metadata.tables.items()}


def test_dry_run_is_read_only_then_mapping_is_repeatable_and_preserves_all_source_bytes(registry_db):
    engine, metadata = registry_db
    with engine.connect() as c:
        before = snapshot(c, metadata)
        tables = inspect(c).get_table_names()
        report = inspect_mapping(c)
        assert report['expected_workspaces'] == 4 and not report['writes_performed']
        assert inspect(c).get_table_names() == tables
    with pytest.raises(MappingError, match='Pause'):
        apply_registry(engine)
    report = apply_registry(engine, writes_paused=True)
    assert report['verified_workspaces'] == report['verified_owner_memberships'] == 4
    assert not report['authorization_enforced']
    assert apply_registry(engine, writes_paused=True)['already_applied']
    with engine.connect() as c:
        assert snapshot(c, metadata) == before
        rows = c.execute(text('SELECT id,owner_user_id,legacy_brand_id FROM zova_workspaces')).all()
        assert set(rows) == {(workspace_key(uid,bid),uid,bid) for uid,bid in [(1,0),(2,0),(1,10),(2,20)]}
        assert verify_registry(c)['verified_workspaces'] == 4


@pytest.mark.parametrize('user,brand', [(1,20),(1,999),(999,0),(1,-1),(1,None)])
def test_invalid_ownership_stops_before_any_registry_write(registry_db,user,brand):
    engine, metadata = registry_db
    with engine.begin() as c:
        c.execute(metadata.tables['nova_drafts'].update().where(metadata.tables['nova_drafts'].c.id==1).values(user_id=user,brand_id=brand))
    with pytest.raises(MappingError):
        apply_registry(engine,writes_paused=True)
    with engine.connect() as c:
        assert 'zova_workspaces' not in inspect(c).get_table_names()
        assert c.scalar(text('SELECT COUNT(*) FROM nova_users')) == 2


def test_existing_permissions_are_never_repaired_by_repeating_backfill(registry_db):
    engine,_ = registry_db
    apply_registry(engine,writes_paused=True)
    with engine.begin() as c:
        c.execute(text("UPDATE zova_workspace_memberships SET role='viewer' WHERE workspace_id=:id"),{'id':workspace_key(1,0)})
    with pytest.raises(MappingError,match='no automatic privilege repair'):
        apply_registry(engine,writes_paused=True)
    with engine.connect() as c:
        assert c.scalar(text('SELECT role FROM zova_workspace_memberships WHERE workspace_id=:id'),{'id':workspace_key(1,0)}) == 'viewer'


def test_registry_rejects_wrong_mapping_and_unexpected_team_access(registry_db):
    engine,_ = registry_db
    apply_registry(engine,writes_paused=True)
    with engine.begin() as c:
        c.execute(text("INSERT INTO zova_workspace_memberships (workspace_id,user_id,role,active,revision) VALUES (:id,2,'viewer',true,1)"),{'id':workspace_key(1,0)})
    with engine.connect() as c, pytest.raises(MappingError,match='Unexpected membership'):
        verify_registry(c)


def test_unknown_role_is_rejected_by_database(registry_db):
    engine,_ = registry_db
    apply_registry(engine,writes_paused=True)
    with pytest.raises(IntegrityError):
        with engine.begin() as c:
            c.execute(text("UPDATE zova_workspace_memberships SET role='superuser'"))


@pytest.mark.parametrize('role,edit,publish,billing', [
    ('owner',True,True,True),('admin',True,True,False),('publisher',True,True,False),
    ('creator',True,False,False),('analyst',False,False,False),('viewer',False,False,False),('unknown',False,False,False)])
def test_capabilities_fail_closed_for_every_role(role,edit,publish,billing):
    assert permits(role,'posts.edit') == edit
    assert permits(role,'posts.publish') == publish
    assert permits(role,'billing.manage') == billing
    assert not permits(role,'unrecognised.capability')
    assert not permits(role,'posts.read',active=False)


def test_failed_backfill_rolls_back_schema_and_source_data(registry_db,monkeypatch):
    from nova import tenant_migration
    engine,metadata = registry_db
    with engine.connect() as c:
        before = snapshot(c,metadata)
    monkeypatch.setattr(tenant_migration,'verify_registry',lambda c: (_ for _ in ()).throw(MappingError('synthetic interrupted verification')))
    with pytest.raises(MappingError,match='interrupted'):
        apply_registry(engine,writes_paused=True)
    with engine.connect() as c:
        assert 'zova_workspaces' not in inspect(c).get_table_names()
        assert snapshot(c,metadata) == before
