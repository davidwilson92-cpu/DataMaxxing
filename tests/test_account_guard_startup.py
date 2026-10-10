import pytest
from sqlalchemy import text, inspect
from nova.account_references import apply_accounts,verify_accounts
from nova.tenant_migration import MappingError
from nova.schema_startup import verify_runtime_schema
from nova.db import Base
from test_tenant_registry import registry_db
from test_schema_startup import initialize
from test_account_references import account_db


def test_runtime_rejects_missing_account_guard_without_repair(registry_db):
    engine,initial=registry_db
    initialize(engine,initial);apply_accounts(engine,writes_paused=True)
    with engine.begin() as c:
        if c.dialect.name=='postgresql':c.execute(text('DROP TRIGGER zova_account_owner_guard ON nova_creator_preferences'))
        else:c.execute(text('DROP TRIGGER nova_creator_preferences_account_update'))
    with engine.connect() as c,pytest.raises(RuntimeError,match='account'):
        verify_runtime_schema(c,Base.metadata)


def test_sqlite_verifier_rejects_same_name_weakened_trigger(account_db):
    if account_db.dialect.name!='sqlite':pytest.skip('SQLite catalog definition regression')
    apply_accounts(account_db,writes_paused=True)
    with account_db.begin() as c:
        c.execute(text('DROP TRIGGER nova_creator_preferences_account_update'))
        c.execute(text('CREATE TRIGGER nova_creator_preferences_account_update BEFORE UPDATE ON nova_creator_preferences BEGIN SELECT 1; END'))
    with account_db.connect() as c,pytest.raises(MappingError,match='definition'):
        verify_accounts(c)


def test_populated_database_requires_explicit_offline_preparation(tmp_path):
    import os,sys,subprocess
    from sqlalchemy import create_engine
    url='sqlite:///'+(tmp_path/'populated.db').as_posix()
    env=dict(os.environ,DATABASE_URL=url,ZOVA_MIGRATION_DATABASE_URL=url)
    env.pop('ZOVA_OFFLINE_ACCOUNT_PREPARATION',None)
    prepare=[sys.executable,'-B','scripts/prepare_database.py','--apply','--writes-paused']
    assert subprocess.run(prepare,env=env,capture_output=True,text=True,timeout=30).returncode==0
    engine=create_engine(url)
    with engine.begin() as c:
        c.execute(text("INSERT INTO nova_users(id,email,password_hash,active,auth_version,display_name,default_brand_name,country_code,subscription_status,marketing_consent,created_at,updated_at) VALUES(1,'preserved@example.test','preserved-hash',1,7,'Name','Brand','GB','none',0,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
        from nova.tenant_migration import workspace_key
        c.execute(text('INSERT INTO zova_workspaces(id,owner_user_id,legacy_brand_id) VALUES(:wid,1,0)'),{'wid':workspace_key(1)})
        c.execute(text('DROP TRIGGER nova_creator_preferences_account_update'))
        c.execute(text("DELETE FROM zova_schema_migrations WHERE version='20261010_account_references'"))
    for mode in ('bootstrap','verify'):
        result=subprocess.run([sys.executable,'-B','-c','import nova.db'],env={**env,'ZOVA_SCHEMA_MODE':mode},capture_output=True,text=True,timeout=30)
        assert result.returncode!=0
    assert subprocess.run(prepare,env=env,capture_output=True,text=True,timeout=30).returncode==0
    with engine.connect() as c:
        assert c.execute(text('SELECT email,password_hash,auth_version FROM nova_users WHERE id=1')).one()==('preserved@example.test','preserved-hash',7)
        verify_runtime_schema(c,Base.metadata)
    engine.dispose()


@pytest.mark.parametrize('corruption',['cascade','additional_cascade','deferred','not_valid','disabled_fk','function','conditional_trigger'])
def test_postgres_rejects_weakened_account_constraints(account_db,corruption):
    if account_db.dialect.name!='postgresql':pytest.skip('PostgreSQL constraint catalog regression')
    apply_accounts(account_db,writes_paused=True)
    with account_db.begin() as c:
        if corruption in {'cascade','additional_cascade','deferred','not_valid'}:
            name=inspect(c).get_foreign_keys('nova_creator_preferences')[0]['name']
            if corruption!='additional_cascade':c.execute(text(f'ALTER TABLE nova_creator_preferences DROP CONSTRAINT "{name}"'))
            suffix={'cascade':'ON DELETE CASCADE','additional_cascade':'ON DELETE CASCADE','deferred':'DEFERRABLE INITIALLY DEFERRED','not_valid':'NOT VALID'}[corruption]
            c.execute(text('ALTER TABLE nova_creator_preferences ADD CONSTRAINT altered_owner FOREIGN KEY(user_id) REFERENCES nova_users(id) '+suffix))
        elif corruption=='disabled_fk':c.execute(text('ALTER TABLE nova_creator_preferences DISABLE TRIGGER ALL'))
        elif corruption=='function':c.execute(text('ALTER FUNCTION zova_guard_account_owner() SECURITY DEFINER'))
        else:
            c.execute(text('DROP TRIGGER zova_account_owner_guard ON nova_creator_preferences'))
            c.execute(text('CREATE TRIGGER zova_account_owner_guard BEFORE UPDATE OF value ON nova_creator_preferences FOR EACH ROW EXECUTE FUNCTION zova_guard_account_owner()'))
    with account_db.connect() as c,pytest.raises(MappingError):verify_accounts(c)
