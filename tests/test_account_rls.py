import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import DBAPIError
from nova import db as models
from nova.account_references import ACCOUNT_TABLES
from nova.account_rls import apply_account_rls,verify_account_policies
from nova.rls import issue_context,bind_context
from nova.tenant_migration import workspace_key
from test_rls import rls_db
from test_tenant_registry import registry_db


@pytest.fixture
def account_rls_db(rls_db):
    admin,runtime,issuer,roles,uids,drafts=rls_db
    with Session(admin) as db:
        for uid in uids:
            creator=models.Creator(name='Synthetic',x_username=f'account-{uid}',api_key_hash=f'synthetic-{uid}',
                encrypted_x_api_key='synthetic',encrypted_x_api_secret='synthetic',
                encrypted_x_access_token='synthetic',encrypted_x_access_token_secret='synthetic')
            db.add(creator);db.flush()
            db.add_all([
                models.Brand(user_id=uid,name='Account fixture'),
                models.UsageEntry(key=f'usage-{uid}',user_id=uid,kind='draft',period='2026-10'),
                models.RecoveryToken(token_hash=f'recovery-{uid}',user_id=uid,auth_version=0,expires_at=models.utcnow()),
                models.AuthIdentity(user_id=uid,provider='apple',subject=f'subject-{uid}'),
                models.CreatorPreferences(user_id=uid,writing_tone=f'private-{uid}'),
                models.UserCreatorLink(user_id=uid,creator_id=creator.id),
                models.BillingAccount(key=f'billing-{uid}',user_id=uid,mode='test'),
                models.AICall(id=f'ai-{uid}',user_id=uid,model='synthetic',status='returned'),
                models.ProductEvent(key=f'event-{uid}',user_id=uid,kind='test'),
                models.EmailVerification(token_hash=f'verify-{uid}',user_id=uid,email=f'{uid}@example.test',expires_at=models.utcnow()),
                models.MfaSettings(user_id=uid,encrypted_secret='synthetic'),
                models.MfaChallenge(token_hash=f'mfa-{uid}',user_id=uid,auth_version=0,expires_at=models.utcnow()),
            ])
        db.commit()
    with admin.begin() as c:
        schema=c.scalar(text('SELECT current_schema()'))
        # Deliberately broad DML tests row policies; not a deployment grant manifest.
        for name in ACCOUNT_TABLES:c.execute(text(f'GRANT SELECT,INSERT,UPDATE,DELETE ON {schema}.{name} TO {roles[0]}'))
    with runtime.connect() as c:
        assert set(c.scalars(text('SELECT user_id FROM nova_creator_preferences')))==set(uids)
    result=apply_account_rls(admin,runtime_roles=[roles[0]],writes_paused=True)
    assert result['protected_tables']==13 and not result['runtime_integrated']
    try:yield admin,runtime,issuer,roles,uids
    finally:
        with admin.begin() as c:
            for name in ACCOUNT_TABLES:c.execute(text(f'DROP POLICY IF EXISTS zova_account_access ON {name}'))


def bound(c,issuer,role,uid,cap='account.read',bid=0):
    token=issue_context(issuer,c,user_id=uid,workspace_id=workspace_key(uid,bid),auth_version=0,
        membership_revision=1,capability=cap,runtime_role=role)
    bind_context(c,token)
    return token


def test_every_account_table_filters_unbound_and_foreign_records(account_rls_db):
    admin,runtime,issuer,roles,uids=account_rls_db
    with runtime.begin() as c:
        for name in ACCOUNT_TABLES:assert c.execute(text(f'SELECT user_id FROM {name}')).all()==[]
        bound(c,issuer,roles[0],uids[0])
        for name in ACCOUNT_TABLES:
            assert set(c.scalars(text(f'SELECT user_id FROM {name}')))=={uids[0]},name
    with runtime.begin() as c:
        bound(c,issuer,roles[0],uids[1])
        for name in ACCOUNT_TABLES:assert set(c.scalars(text(f'SELECT user_id FROM {name}')))=={uids[1]},name


def test_account_edit_cannot_change_security_billing_membership_or_other_user(account_rls_db):
    admin,runtime,issuer,roles,uids=account_rls_db
    with runtime.begin() as c:
        bound(c,issuer,roles[0],uids[0],'account.edit')
        assert c.execute(text('UPDATE nova_creator_preferences SET writing_tone=\'edited\' WHERE user_id=:uid'),{'uid':uids[1]}).rowcount==0
        # UPDATE also requires SELECT visibility in PostgreSQL; editing authority
        # includes read visibility via the policy's explicit read-capability list.
        assert c.execute(text('UPDATE nova_creator_preferences SET writing_tone=\'edited\' WHERE user_id=:uid'),{'uid':uids[0]}).rowcount==1
        for name in ACCOUNT_TABLES-{'nova_creator_preferences','zova_brands'}:
            assert c.execute(text(f'UPDATE {name} SET user_id=user_id WHERE user_id=:uid'),{'uid':uids[0]}).rowcount==0,name
    with admin.connect() as c:
        assert c.scalar(text('SELECT writing_tone FROM nova_creator_preferences WHERE user_id=:uid'),{'uid':uids[0]})=='edited'


def test_account_read_cannot_write_and_foreign_insert_is_rejected(account_rls_db):
    _,runtime,issuer,roles,uids=account_rls_db
    with runtime.begin() as c:
        bound(c,issuer,roles[0],uids[0])
        assert c.execute(text("UPDATE nova_creator_preferences SET writing_tone='blocked' WHERE user_id=:uid"),{'uid':uids[0]}).rowcount==0
    with pytest.raises(DBAPIError) as failure:
        with runtime.begin() as c:
            bound(c,issuer,roles[0],uids[0],'account.edit')
            c.execute(text("INSERT INTO zova_brands(user_id,name,created_at) VALUES(:uid,'Foreign',CURRENT_TIMESTAMP)"),{'uid':uids[1]})
    assert failure.value.orig.sqlstate=='42501'
    assert 'row-level security' in str(failure.value.orig)


@pytest.mark.parametrize('case',['wrong_capability','secondary_brand','replay','revoked'])
def test_account_context_fails_closed(account_rls_db,case):
    admin,runtime,issuer,roles,uids=account_rls_db
    with runtime.begin() as c:
        if case=='secondary_brand':
            with admin.connect() as a:bid=a.scalar(text('SELECT id FROM zova_brands WHERE user_id=:uid ORDER BY id LIMIT 1'),{'uid':uids[0]})
            bound(c,issuer,roles[0],uids[0],bid=bid)
        else:token=bound(c,issuer,roles[0],uids[0],'posts.read' if case=='wrong_capability' else 'account.read')
        if case=='revoked':
            with admin.begin() as a:a.execute(text('UPDATE nova_users SET auth_version=auth_version+1 WHERE id=:uid'),{'uid':uids[0]})
        if case!='replay':assert c.execute(text('SELECT * FROM nova_creator_preferences')).all()==[]
    if case=='replay':
        with runtime.begin() as c:
            bind_context(c,token)
            assert c.execute(text('SELECT * FROM nova_creator_preferences')).all()==[]


def test_permissive_policy_and_forged_helper_actor_cannot_bypass_scope(account_rls_db):
    admin,runtime,issuer,roles,uids=account_rls_db
    with admin.begin() as c:
        owner=c.scalar(text('SELECT current_user'))
        c.execute(text('CREATE POLICY unrelated_allow ON nova_creator_preferences FOR ALL TO PUBLIC USING(true) WITH CHECK(true)'))
    with runtime.begin() as c:
        assert c.scalar(text('SELECT zova_account_allowed(:uid,CAST(:actor AS name),ARRAY[]::text[])'),{'uid':uids[1],'actor':owner}) is True
        assert c.execute(text('SELECT * FROM nova_creator_preferences')).all()==[]
        bound(c,issuer,roles[0],uids[0])
        assert set(c.scalars(text('SELECT user_id FROM nova_creator_preferences')))=={uids[0]}
    with admin.connect() as c,pytest.raises(ValueError,match='manifest'):
        verify_account_policies(c,runtime_roles=[roles[0]])


def test_offline_only_requires_pause():
    with pytest.raises(ValueError,match='Pause'):apply_account_rls(None,runtime_roles=['runtime'])


@pytest.mark.parametrize('change',['disabled','function'])
def test_account_policy_drift_refuses_verification(account_rls_db,change):
    admin,_,_,roles,_=account_rls_db
    with admin.begin() as c:
        if change=='disabled':c.execute(text('ALTER TABLE nova_creator_preferences DISABLE ROW LEVEL SECURITY'))
        else:c.execute(text('ALTER FUNCTION zova_account_allowed(integer,name,text[]) SECURITY INVOKER'))
    with admin.connect() as c,pytest.raises(ValueError):verify_account_policies(c,runtime_roles=[roles[0]])


def test_context_functions_work_with_non_superuser_migration_owner(account_rls_db):
    import secrets
    from sqlalchemy import create_engine
    admin,runtime,issuer,roles,uids=account_rls_db
    owner='zova_account_owner_'+secrets.token_hex(8)
    functions=['zova_issue_context(text,integer,text,integer,integer,text,text,integer,text,integer)',
               'zova_rls_workspace(text[])','zova_account_allowed(integer,name,text[])']
    with admin.begin() as c:
        original,schema=c.execute(text('SELECT current_user,current_schema()')).one()
        c.execute(text(f'CREATE ROLE {owner} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS'))
        c.execute(text(f'GRANT USAGE,CREATE ON SCHEMA {schema} TO {owner}'))
        c.execute(text(f'GRANT SELECT ON nova_users,zova_workspaces TO {owner}'))
        c.execute(text(f'GRANT SELECT,INSERT,DELETE ON zova_db_contexts TO {owner}'))
        # SELECT FOR UPDATE in expired-context cleanup requires UPDATE authority.
        # This is the trusted function owner, never an application runtime role.
        c.execute(text(f'GRANT UPDATE(token_hash) ON zova_db_contexts TO {owner}'))
        c.execute(text(f'GRANT SELECT,INSERT ON zova_schema_migrations TO {owner}'))
        for name in ACCOUNT_TABLES:c.execute(text(f'ALTER TABLE {name} OWNER TO {owner}'))
        for signature in functions:c.execute(text(f'ALTER FUNCTION {signature} OWNER TO {owner}'))
    maintenance=create_engine(admin.url,connect_args={'options':f'-csearch_path={schema} -crole={owner}'})
    try:
        apply_account_rls(maintenance,runtime_roles=[roles[0]],writes_paused=True)
        with runtime.begin() as c:
            bound(c,issuer,roles[0],uids[0])
            assert set(c.scalars(text('SELECT user_id FROM zova_workspace_memberships')))=={uids[0]}
            assert set(c.scalars(text('SELECT user_id FROM nova_creator_preferences')))=={uids[0]}
    finally:
        maintenance.dispose()
        with admin.begin() as c:
            for name in ACCOUNT_TABLES:c.execute(text(f'ALTER TABLE {name} OWNER TO {original}'))
            for signature in functions:c.execute(text(f'ALTER FUNCTION {signature} OWNER TO {original}'))
        apply_account_rls(admin,runtime_roles=[roles[0]],writes_paused=True)
        with admin.begin() as c:
            c.execute(text(f'DROP OWNED BY {owner}'))
            c.execute(text(f'DROP ROLE {owner}'))
