"""Offline immutable account ownership. This is not account-level read isolation."""
from sqlalchemy import MetaData, inspect, text
from .tenant_migration import MappingError
from .tenant_references import BRAND_TABLES

VERSION='20261010_account_references'
ACCOUNT_TABLES=frozenset({
    'zova_brands','zova_usage_entries','zova_recovery_tokens','zova_auth_identities',
    'nova_creator_preferences','nova_user_creator_links','zova_billing_accounts',
    'zova_ai_calls','zova_product_events','zova_email_verifications',
    'zova_mfa_settings','zova_mfa_challenges','zova_workspace_memberships',
})
NULLABLE=frozenset({'zova_ai_calls'})
# Ephemeral issuer-owned capability records have separate RLS function controls.
SERVER_CONTEXT_TABLES=frozenset({'zova_db_contexts'})
GUARD_BODY="""BEGIN
                  IF NEW.user_id IS DISTINCT FROM OLD.user_id THEN
                    RAISE EXCEPTION 'Account ownership is immutable' USING ERRCODE='23514';
                  END IF;
                  RETURN NEW;
                END"""


def _q(c,name):return c.dialect.identifier_preparer.quote(name)


def sqlite_guard_definitions(c,name):
    table=_q(c,name)
    invalid="NEW.user_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM nova_users WHERE id=NEW.user_id)"
    if name not in NULLABLE:invalid='NEW.user_id IS NULL OR ('+invalid+')'
    return {
        name+'_account_insert':f'''CREATE TRIGGER {_q(c,name+'_account_insert')} BEFORE INSERT ON {table}
                    WHEN {invalid} BEGIN SELECT RAISE(ABORT,'Invalid account ownership'); END''',
        name+'_account_update':f'''CREATE TRIGGER {_q(c,name+'_account_update')} BEFORE UPDATE ON {table}
                    WHEN NEW.user_id IS NOT OLD.user_id BEGIN SELECT RAISE(ABORT,'Account ownership is immutable'); END''',
        name+'_account_delete_user':f'''CREATE TRIGGER {_q(c,name+'_account_delete_user')} BEFORE DELETE ON nova_users
                    WHEN EXISTS (SELECT 1 FROM {table} WHERE user_id=OLD.id)
                    BEGIN SELECT RAISE(ABORT,'Account contains customer records'); END''',
    }


def plan_accounts(c):
    metadata=MetaData();metadata.reflect(bind=c)
    if 'nova_users' not in metadata.tables:raise MappingError('Account identity table is missing')
    discovered={name for name,t in metadata.tables.items() if 'user_id' in t.c and name not in BRAND_TABLES|SERVER_CONTEXT_TABLES}
    if discovered-ACCOUNT_TABLES:raise MappingError('Unclassified account-owned tables require review')
    counts={}
    for name in sorted(discovered):
        table=_q(c,name)
        null='s.user_id IS NULL OR' if name not in NULLABLE else ''
        invalid=c.scalar(text(f'''SELECT COUNT(*) FROM {table} s LEFT JOIN nova_users u
            ON u.id=s.user_id WHERE {null} (s.user_id IS NOT NULL AND u.id IS NULL)'''))
        if invalid:raise MappingError(f'{name}: invalid account references')
        counts[name]=c.scalar(text(f'SELECT COUNT(*) FROM {table}'))
    return {'version':VERSION,'table_counts':counts,'writes_performed':False,'read_isolation_enforced':False}


def apply_accounts(engine,*,writes_paused=False,lock_timeout_ms=5000,statement_timeout_ms=120000):
    if not writes_paused:raise MappingError('Pause application and worker writes before account migration')
    with engine.begin() as c:
        from .migration_limits import bound_migration
        bound_migration(c,lock_timeout_ms=lock_timeout_ms,statement_timeout_ms=statement_timeout_ms)
        if c.dialect.name=='sqlite':c.exec_driver_sql('BEGIN IMMEDIATE')
        elif c.dialect.name=='postgresql':c.execute(text('SELECT pg_advisory_xact_lock(61010001)'))
        else:raise MappingError('Unsupported migration database')
        report=plan_accounts(c)
        tables=sorted(report['table_counts'])
        if c.dialect.name=='postgresql':
            for name in sorted([*tables,'nova_users']):
                c.execute(text(f'LOCK TABLE {_q(c,name)} IN ACCESS EXCLUSIVE MODE'))
            report=plan_accounts(c)
            schema=_q(c,c.scalar(text('SELECT current_schema()')))
            fn=f'{schema}.zova_guard_account_owner'
            c.execute(text(f'''CREATE OR REPLACE FUNCTION {fn}() RETURNS trigger
                LANGUAGE plpgsql SET search_path = pg_catalog, {schema} AS $$ {GUARD_BODY} $$'''))
            for name in tables:
                table=f'{schema}.{_q(c,name)}'
                keys=inspect(c).get_foreign_keys(name)
                if not any(k['constrained_columns']==['user_id'] and k['referred_table']=='nova_users'
                           and k['referred_columns']==['id'] and k['referred_schema'] in (None,c.scalar(text('SELECT current_schema()'))) for k in keys):
                    c.execute(text(f'ALTER TABLE {table} ADD CONSTRAINT {_q(c,name+"_account_fk")} FOREIGN KEY (user_id) REFERENCES {schema}.nova_users(id)'))
                if name not in NULLABLE:c.execute(text(f'ALTER TABLE {table} ALTER COLUMN user_id SET NOT NULL'))
                c.execute(text(f'DROP TRIGGER IF EXISTS zova_account_owner_guard ON {table}'))
                c.execute(text(f'CREATE TRIGGER zova_account_owner_guard BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION {fn}()'))
        else:
            for name in tables:
                for trigger,definition in sqlite_guard_definitions(c,name).items():
                    c.exec_driver_sql(f'DROP TRIGGER IF EXISTS {_q(c,trigger)}')
                    c.exec_driver_sql(definition)
        c.execute(text('CREATE TABLE IF NOT EXISTS zova_schema_migrations (version VARCHAR(100) PRIMARY KEY, applied_at TIMESTAMP NOT NULL)'))
        c.execute(text('INSERT INTO zova_schema_migrations(version,applied_at) VALUES (:version,CURRENT_TIMESTAMP) ON CONFLICT(version) DO NOTHING'),{'version':VERSION})
        report=verify_accounts(c)
        report['writes_performed']=True
        return report


def verify_accounts(c):
    report=plan_accounts(c)
    verify_account_guards(c,report['table_counts'])
    report['ownership_immutable']=True
    return report


def verify_account_guards(c,tables=ACCOUNT_TABLES):
    """Catalog-only verification: requires no access to customer row contents."""
    tables=set(tables)
    if not tables<=ACCOUNT_TABLES:raise MappingError('Unknown account guard manifest')
    if not tables<=set(inspect(c).get_table_names()):raise MappingError('Account tables missing')
    if c.dialect.name=='postgresql':
        fn=c.execute(text('''SELECT p.prosrc,p.prosecdef,p.proconfig,p.prorettype='trigger'::regtype AS trigger_result,
            p.prokind,p.provolatile,p.proisstrict,p.proleakproof,l.lanname
            FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
            JOIN pg_language l ON l.oid=p.prolang
            WHERE n.nspname=current_schema() AND p.proname='zova_guard_account_owner' AND p.pronargs=0''')).mappings().one_or_none()
        schema=_q(c,c.scalar(text('SELECT current_schema()')))
        if (not fn or fn['prosrc'].strip()!=GUARD_BODY or fn['prosecdef'] or not fn['trigger_result']
            or fn['proconfig']!=[f'search_path=pg_catalog, {schema}'] or fn['lanname']!='plpgsql'
            or fn['prokind']!='f' or fn['provolatile']!='v' or fn['proisstrict'] or fn['proleakproof']):
            raise MappingError('Account ownership function differs from migration source')
        guards=set(c.execute(text('''SELECT t.relname FROM pg_trigger g
            JOIN pg_class t ON t.oid=g.tgrelid JOIN pg_namespace n ON n.oid=t.relnamespace
            JOIN pg_proc p ON p.oid=g.tgfoid
            WHERE n.nspname=current_schema() AND p.pronamespace=n.oid
              AND g.tgname='zova_account_owner_guard' AND p.proname='zova_guard_account_owner'
              AND g.tgenabled IN ('O','A') AND g.tgtype=19 AND g.tgqual IS NULL
              AND g.tgnargs=0 AND g.tgattr=''::int2vector AND NOT g.tgisinternal''')).scalars())
        if not tables<=guards:raise MappingError('Account ownership guards missing or disabled')
        for name in tables:
            columns={col['name']:col for col in inspect(c).get_columns(name)}
            if 'user_id' not in columns or columns['user_id']['nullable']!=(name in NULLABLE):
                raise MappingError('Account reference nullability differs from manifest')
            safe=c.scalar(text('''SELECT COALESCE(bool_and(
                  k.convalidated AND NOT k.condeferrable AND NOT k.condeferred
                  AND k.confdeltype IN ('a','r') AND k.confupdtype IN ('a','r')
                  AND EXISTS(SELECT 1 FROM pg_trigger g WHERE g.tgconstraint=k.oid)
                  AND NOT EXISTS(SELECT 1 FROM pg_trigger g WHERE g.tgconstraint=k.oid AND g.tgenabled NOT IN ('O','A'))),false)
                FROM pg_constraint k
                JOIN pg_class t ON t.oid=k.conrelid JOIN pg_namespace n ON n.oid=t.relnamespace
                JOIN pg_attribute a ON a.attrelid=t.oid AND a.attname='user_id'
                JOIN pg_class u ON u.oid=k.confrelid AND u.relnamespace=n.oid AND u.relname='nova_users'
                JOIN pg_attribute ua ON ua.attrelid=u.oid AND ua.attname='id'
                WHERE n.nspname=current_schema() AND t.relname=:table AND k.contype='f'
                  AND t.relkind='r' AND k.conkey=ARRAY[a.attnum] AND k.confkey=ARRAY[ua.attnum]'''),{'table':name})
            if not safe:raise MappingError('Account reference foreign key missing or weakened')
    elif c.dialect.name=='sqlite':
        triggers=dict(c.execute(text("SELECT name,sql FROM sqlite_master WHERE type='trigger'" )).all())
        expected={key:value for name in tables for key,value in sqlite_guard_definitions(c,name).items()}
        if not set(expected)<=set(triggers):
            raise MappingError('Account ownership guards missing')
        normalize=lambda sql:' '.join(sql.strip().rstrip(';').split())
        if any(normalize(triggers[key])!=normalize(sql) for key,sql in expected.items()):
            raise MappingError('Account ownership guard definition differs from migration source')
    else:raise MappingError('Unsupported migration database')
