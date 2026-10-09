"""Direct database attacks against the reference migration, not ORM-only checks."""
import pytest
from sqlalchemy import text,inspect
from sqlalchemy.exc import DBAPIError
from nova.tenant_migration import apply_registry,workspace_key,MappingError
from nova.tenant_references import apply_references,verify_references
from test_tenant_registry import registry_db,snapshot


def setup_refs(engine):
    apply_registry(engine,writes_paused=True)
    return apply_references(engine,writes_paused=True)


def test_backfill_preserves_source_and_supports_old_insert_contract(registry_db):
    engine,metadata=registry_db
    with engine.connect() as c:before=snapshot(c,metadata)
    with pytest.raises(MappingError,match='Pause'):apply_references(engine)
    result=setup_refs(engine)
    assert result['mapped_table_counts']=={'nova_drafts':2,'nova_social_connections':1}
    assert not result['read_isolation_enforced']
    apply_references(engine,writes_paused=True)
    with engine.begin() as c:
        assert snapshot(c,metadata)==before
        assert c.scalar(text('SELECT workspace_id FROM nova_drafts WHERE id=2'))==workspace_key(2,20)
        c.execute(text("INSERT INTO nova_drafts(id,user_id,brand_id,content) VALUES (3,1,10,'new synthetic draft')"))
        assert c.scalar(text('SELECT workspace_id FROM nova_drafts WHERE id=3'))==workspace_key(1,10)
        c.execute(text("UPDATE nova_drafts SET content='edited synthetic draft' WHERE id=3"))
        assert verify_references(c)['mapped_table_counts']['nova_drafts']==3


@pytest.mark.parametrize('assignment,params',[
    ('user_id=2',{}),('brand_id=10',{}),('workspace_id=:wid',{'wid':workspace_key(2,20)}),
    ('workspace_id=NULL',{}),('user_id=2,brand_id=20,workspace_id=:wid',{'wid':workspace_key(2,20)})])
def test_raw_sql_cannot_reassign_customer_record(registry_db,assignment,params):
    engine,_=registry_db;setup_refs(engine)
    with pytest.raises(DBAPIError):
        with engine.begin() as c:c.execute(text(f'UPDATE nova_drafts SET {assignment} WHERE id=1'),params)
    with engine.connect() as c:
        assert c.execute(text('SELECT user_id,brand_id,workspace_id FROM nova_drafts WHERE id=1')).one()==(1,0,workspace_key(1))


@pytest.mark.parametrize('user,brand,wid',[(1,20,None),(999,0,None),(1,0,workspace_key(2)),(1,999,None)])
def test_raw_sql_cannot_insert_cross_owner_or_forged_reference(registry_db,user,brand,wid):
    engine,_=registry_db;setup_refs(engine)
    with pytest.raises(DBAPIError):
        with engine.begin() as c:
            c.execute(text('INSERT INTO nova_drafts(id,user_id,brand_id,workspace_id) VALUES (3,:uid,:bid,:wid)'),{'uid':user,'bid':brand,'wid':wid})


def test_workspace_mapping_cannot_be_reassigned_or_deleted_under_records(registry_db):
    engine,_=registry_db;setup_refs(engine)
    with pytest.raises(DBAPIError):
        with engine.begin() as c:c.execute(text('UPDATE zova_workspaces SET owner_user_id=2 WHERE id=:wid'),{'wid':workspace_key(1)})
    with pytest.raises(DBAPIError):
        with engine.begin() as c:c.execute(text('DELETE FROM zova_workspaces WHERE id=:wid'),{'wid':workspace_key(1)})


def test_migration_rejects_existing_wrong_reference_without_repair(registry_db):
    engine,_=registry_db;apply_registry(engine,writes_paused=True)
    with engine.begin() as c:
        c.execute(text('ALTER TABLE nova_drafts ADD COLUMN workspace_id VARCHAR(36)'))
        c.execute(text('UPDATE nova_drafts SET workspace_id=:wid'),{'wid':workspace_key(2)})
    with pytest.raises(MappingError,match='invalid canonical'):
        apply_references(engine,writes_paused=True)
    with engine.connect() as c:
        assert c.scalar(text('SELECT workspace_id FROM nova_drafts WHERE id=1'))==workspace_key(2)
        assert 'workspace_id' not in {col['name'] for col in inspect(c).get_columns('nova_social_connections')}


def test_interrupted_backfill_rolls_back_added_columns(registry_db,monkeypatch):
    import nova.tenant_references as module
    engine,metadata=registry_db;apply_registry(engine,writes_paused=True)
    with engine.connect() as c:before=snapshot(c,metadata)
    def interrupted(c):raise MappingError('Synthetic interruption')
    monkeypatch.setattr(module,'verify_references',interrupted)
    with pytest.raises(MappingError,match='interruption'):apply_references(engine,writes_paused=True)
    with engine.connect() as c:
        assert snapshot(c,metadata)==before
        assert 'workspace_id' not in {col['name'] for col in inspect(c).get_columns('nova_drafts')}


def test_new_unclassified_tenant_table_stops_migration(registry_db):
    engine,_=registry_db;apply_registry(engine,writes_paused=True)
    with engine.begin() as c:c.execute(text('CREATE TABLE unexpected_customer_table (id INTEGER,user_id INTEGER,brand_id INTEGER)'))
    with pytest.raises(MappingError,match='Unclassified'):apply_references(engine,writes_paused=True)


def test_manifest_covers_every_current_brand_owned_model():
    from nova.db import Base
    from nova.tenant_references import BRAND_TABLES
    actual={name for name,table in Base.metadata.tables.items() if {'user_id','brand_id'} <= set(table.c.keys())}
    assert actual==BRAND_TABLES


def test_full_application_schema_and_existing_orm_insert_contract(registry_db):
    from sqlalchemy.orm import Session
    from nova.db import Base,User,Brand,Draft,SocialConnection,MediaAsset
    from nova.migrations import run_migrations
    from nova.tenant_references import BRAND_TABLES
    engine,initial=registry_db
    # The fixture owns this isolated database/schema; never touch the app test store.
    initial.drop_all(engine)
    Base.metadata.create_all(engine)
    run_migrations(engine)
    with Session(engine) as db:
        owner=User(email='references@example.test',password_hash='synthetic-password-hash',auth_version=9)
        db.add(owner);db.flush();uid=owner.id
        brand=Brand(user_id=uid,name='Synthetic brand');db.add(brand);db.flush();bid=brand.id
        draft=Draft(user_id=uid,brand_id=bid,brief='Preserve this draft')
        connection=SocialConnection(user_id=uid,brand_id=bid,platform='instagram',account_id='synthetic-account',encrypted_access_token='opaque-synthetic-token')
        media=MediaAsset(user_id=uid,brand_id=bid,filename='synthetic.png',mime_type='image/png',storage_key='private/synthetic.png')
        db.add_all([draft,connection,media]);db.commit()
    report=apply_references(engine,writes_paused=True)
    assert set(report['mapped_table_counts'])==BRAND_TABLES
    with Session(engine) as db:
        row=Draft(user_id=uid,brand_id=bid,brief='Old ORM still writes compatible records')
        db.add(row);db.commit();did=row.id
    with engine.connect() as c:
        assert c.scalar(text('SELECT workspace_id FROM nova_drafts WHERE id=:id'),{'id':did})==workspace_key(uid,bid)
        assert c.execute(text('SELECT password_hash,auth_version FROM nova_users WHERE id=:id'),{'id':uid}).one()==('synthetic-password-hash',9)
        assert c.scalar(text('SELECT encrypted_access_token FROM nova_social_connections'))=='opaque-synthetic-token'
        assert c.scalar(text('SELECT storage_key FROM nova_media_assets'))=='private/synthetic.png'
        verify_references(c)


def test_reference_plan_performs_no_writes(registry_db):
    from nova.tenant_references import plan_references
    engine,_=registry_db;apply_registry(engine,writes_paused=True)
    with engine.connect() as c:
        plan=plan_references(c)
        assert plan['tables_needing_column']==['nova_drafts','nova_social_connections']
        assert not plan['writes_performed']
        assert 'workspace_id' not in {col['name'] for col in inspect(c).get_columns('nova_drafts')}
