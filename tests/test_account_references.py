import pytest
from sqlalchemy import text, inspect
from sqlalchemy.exc import DBAPIError
from nova.account_references import ACCOUNT_TABLES, apply_accounts, plan_accounts
from nova.tenant_migration import MappingError
from test_tenant_registry import registry_db


@pytest.fixture
def account_db(registry_db):
    engine,_=registry_db
    with engine.begin() as c:
        for name in sorted(ACCOUNT_TABLES-{'zova_brands'}):
            c.execute(text(f'CREATE TABLE {name} (id INTEGER PRIMARY KEY,user_id INTEGER,value VARCHAR(100))'))
            c.execute(text(f"INSERT INTO {name}(id,user_id,value) VALUES(1,1,'synthetic-preserved')"))
    return engine


@pytest.mark.parametrize('table',sorted(ACCOUNT_TABLES))
def test_raw_sql_cannot_reassign_account_record(account_db,table):
    # Reproduce the current schema's missing invariant before migration.
    with account_db.begin() as c:
        identity=c.scalar(text(f'SELECT id FROM {table} WHERE user_id=1'))
        c.execute(text(f'UPDATE {table} SET user_id=2 WHERE id=:id'),{'id':identity})
        assert c.scalar(text(f'SELECT user_id FROM {table} WHERE id=:id'),{'id':identity})==2
        c.execute(text(f'UPDATE {table} SET user_id=1 WHERE id=:id'),{'id':identity})
    apply_accounts(account_db,writes_paused=True)
    with pytest.raises(DBAPIError):
        with account_db.begin() as c:c.execute(text(f'UPDATE {table} SET user_id=2 WHERE user_id=1'))
    with account_db.connect() as c:assert c.scalar(text(f'SELECT COUNT(*) FROM {table} WHERE user_id=1'))==1


def test_plan_and_repeat_preserve_records_and_allow_ordinary_updates(account_db):
    with account_db.connect() as c:
        before=plan_accounts(c)
        assert not before['writes_performed']
        assert 'zova_schema_migrations' not in inspect(c).get_table_names()
    with pytest.raises(MappingError,match='Pause'):apply_accounts(account_db)
    apply_accounts(account_db,writes_paused=True);apply_accounts(account_db,writes_paused=True)
    with account_db.begin() as c:
        assert plan_accounts(c)==before
        assert c.scalar(text('SELECT value FROM nova_creator_preferences WHERE id=1'))=='synthetic-preserved'
        c.execute(text("UPDATE nova_creator_preferences SET value='edited' WHERE id=1"))
        c.execute(text("INSERT INTO zova_ai_calls(id,user_id,value) VALUES(2,NULL,'anonymous')"))
    with pytest.raises(DBAPIError):
        with account_db.begin() as c:c.execute(text('UPDATE zova_ai_calls SET user_id=2 WHERE id=2'))


@pytest.mark.parametrize('owner',[None,999])
def test_new_preferences_require_valid_owner(account_db,owner):
    apply_accounts(account_db,writes_paused=True)
    with pytest.raises(DBAPIError):
        with account_db.begin() as c:c.execute(text('INSERT INTO nova_creator_preferences(id,user_id) VALUES(2,:uid)'),{'uid':owner})


def test_owner_cannot_be_deleted_while_account_records_remain(account_db):
    apply_accounts(account_db,writes_paused=True)
    with pytest.raises(DBAPIError):
        with account_db.begin() as c:c.execute(text('DELETE FROM nova_users WHERE id=1'))


def test_orphan_preflight_rolls_back_without_reassigning(account_db):
    with account_db.begin() as c:c.execute(text('UPDATE nova_creator_preferences SET user_id=999 WHERE id=1'))
    with pytest.raises(MappingError,match='invalid account'):apply_accounts(account_db,writes_paused=True)
    with account_db.connect() as c:
        assert c.scalar(text('SELECT user_id FROM nova_creator_preferences WHERE id=1'))==999
        assert 'zova_schema_migrations' not in inspect(c).get_table_names()


def test_manifest_covers_current_account_owned_models():
    from nova.db import Base
    from nova.tenant_references import BRAND_TABLES
    assert {n for n,t in Base.metadata.tables.items() if 'user_id' in t.c and n not in BRAND_TABLES}==ACCOUNT_TABLES


def test_unknown_account_table_requires_review(account_db):
    with account_db.begin() as c:c.execute(text('CREATE TABLE unexpected_private_data(id INTEGER,user_id INTEGER)'))
    with pytest.raises(MappingError,match='Unclassified'):apply_accounts(account_db,writes_paused=True)


def test_interrupted_migration_rolls_back_guards_and_version(account_db,monkeypatch):
    from nova import account_references as module
    def fail(c):raise MappingError('Synthetic interruption')
    monkeypatch.setattr(module,'verify_accounts',fail)
    with pytest.raises(MappingError,match='interruption'):apply_accounts(account_db,writes_paused=True)
    with account_db.begin() as c:
        assert 'zova_schema_migrations' not in inspect(c).get_table_names()
        c.execute(text('UPDATE nova_creator_preferences SET user_id=2 WHERE id=1'))


def test_verifier_rejects_removed_guard_without_repair(account_db):
    from nova.account_references import verify_accounts
    apply_accounts(account_db,writes_paused=True)
    with account_db.begin() as c:
        if c.dialect.name=='postgresql':c.execute(text('DROP TRIGGER zova_account_owner_guard ON nova_creator_preferences'))
        else:c.execute(text('DROP TRIGGER nova_creator_preferences_account_update'))
    with account_db.connect() as c:
        with pytest.raises(MappingError,match='guards'):verify_accounts(c)
