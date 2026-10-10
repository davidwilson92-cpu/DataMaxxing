"""Offline identity/issued-token invariants, also verified without reading rows."""
from sqlalchemy import inspect,text
from .migration_limits import bound_migration
from .tenant_migration import MappingError

VERSION='20261010_identity_guards'
FIELDS={
    'zova_auth_identities':('id','user_id','provider','subject'),
    'nova_user_creator_links':('id','user_id','creator_id'),
    'zova_recovery_tokens':('token_hash','user_id','auth_version','expires_at'),
    'zova_email_verifications':('token_hash','user_id','email','expires_at'),
    'zova_mfa_challenges':('token_hash','user_id','auth_version','destination','expires_at'),
}
CONSUMABLE=frozenset({'zova_recovery_tokens','zova_email_verifications','zova_mfa_challenges'})


def body():
    clauses=[]
    for name,columns in sorted(FIELDS.items()):
        mismatch=' OR '.join(f"to_jsonb(NEW)->'{col}' IS DISTINCT FROM to_jsonb(OLD)->'{col}'" for col in columns)
        if name in CONSUMABLE:mismatch+=" OR (to_jsonb(OLD)->'used'='true'::jsonb AND to_jsonb(NEW)->'used' IS DISTINCT FROM 'true'::jsonb)"
        clauses.append(f"IF TG_TABLE_NAME='{name}' AND ({mismatch}) THEN RAISE EXCEPTION 'Issued identity authority is immutable' USING ERRCODE='23514'; END IF;")
    return 'BEGIN\n'+'\n'.join(clauses)+'\nRETURN NEW;\nEND'


def sqlite_definition(c,name):
    q=c.dialect.identifier_preparer.quote
    mismatch=' OR '.join(f'NEW.{q(col)} IS NOT OLD.{q(col)}' for col in FIELDS[name])
    if name in CONSUMABLE:mismatch+=' OR (OLD.used=1 AND NEW.used IS NOT 1)'
    return f"CREATE TRIGGER {q(name+'_identity_guard')} BEFORE UPDATE ON {q(name)} WHEN {mismatch} BEGIN SELECT RAISE(ABORT,'Issued identity authority is immutable'); END"


def verify_columns(c):
    schema=inspect(c)
    if not set(FIELDS)<=set(schema.get_table_names()):raise MappingError('Identity authority tables missing')
    for name,fields in FIELDS.items():
        required=set(fields)|({'used'} if name in CONSUMABLE else set())
        columns={v['name']:v for v in schema.get_columns(name)}
        if not required<=columns.keys() or any(columns[col]['nullable'] for col in required):
            raise MappingError('Identity authority columns missing or nullable')


def verify_identities(c):
    verify_columns(c)
    if c.dialect.name=='sqlite':
        actual=dict(c.execute(text("SELECT name,sql FROM sqlite_master WHERE type='trigger'")).all())
        norm=lambda value:' '.join(value.strip().rstrip(';').split())
        for name in FIELDS:
            value=actual.get(name+'_identity_guard')
            if not value or norm(value)!=norm(sqlite_definition(c,name)):
                raise MappingError('Identity authority guard missing or changed')
    elif c.dialect.name=='postgresql':
        schema=c.dialect.identifier_preparer.quote(c.scalar(text('SELECT current_schema()')))
        row=c.execute(text('''SELECT p.prosrc,p.prosecdef,p.proconfig,p.provolatile,p.proisstrict,p.proleakproof,
            p.prokind,p.proretset,p.prorettype='trigger'::regtype AS result,p.pronargs,l.lanname
            FROM pg_proc p JOIN pg_language l ON l.oid=p.prolang
            WHERE p.oid=to_regprocedure(:signature)'''),{'signature':f'{schema}.zova_guard_identity()'}).mappings().first()
        if (not row or row['prosrc'].strip()!=body() or row['prosecdef']
            or row['proconfig']!=[f'search_path=pg_catalog, {schema}'] or row['provolatile']!='v'
            or row['proisstrict'] or row['proleakproof'] or row['prokind']!='f' or row['proretset']
            or not row['result'] or row['pronargs'] or row['lanname']!='plpgsql'):
            raise MappingError('Identity authority function missing or changed')
        guards=set(c.scalars(text('''SELECT t.relname FROM pg_trigger g
            JOIN pg_class t ON t.oid=g.tgrelid JOIN pg_namespace n ON n.oid=t.relnamespace
            WHERE n.nspname=current_schema() AND t.relkind='r'
            AND g.tgfoid=to_regprocedure(:signature) AND g.tgname='zova_identity_guard'
            AND g.tgenabled IN ('O','A') AND g.tgtype=19 AND g.tgqual IS NULL
            AND g.tgnargs=0 AND g.tgattr=''::int2vector AND NOT g.tgisinternal'''),{'signature':f'{schema}.zova_guard_identity()'}))
        if not set(FIELDS)<=guards:raise MappingError('Identity authority guards missing or changed')
    else:raise MappingError('Unsupported identity migration database')
    return {'version':VERSION,'protected_tables':len(FIELDS),'writes_performed':False}


def plan_identities(c):
    verify_columns(c)
    q=c.dialect.identifier_preparer.quote
    return {'version':VERSION,'writes_performed':False,
            'table_counts':{name:c.scalar(text(f'SELECT COUNT(*) FROM {q(name)}')) for name in sorted(FIELDS)}}


def apply_identities(engine,*,writes_paused=False):
    if not writes_paused:raise MappingError('Pause application and worker writes before identity migration')
    with engine.begin() as c:
        bound_migration(c)
        q=c.dialect.identifier_preparer.quote
        if c.dialect.name=='sqlite':c.exec_driver_sql('BEGIN IMMEDIATE')
        elif c.dialect.name=='postgresql':
            c.execute(text('SELECT pg_advisory_xact_lock(61010003)'))
            for name in sorted(FIELDS):c.execute(text(f'LOCK TABLE {q(name)} IN ACCESS EXCLUSIVE MODE'))
        else:raise MappingError('Unsupported identity migration database')
        verify_columns(c)
        if c.dialect.name=='postgresql':
            schema=q(c.scalar(text('SELECT current_schema()')))
            fn=f'{schema}.zova_guard_identity'
            c.execute(text(f'CREATE OR REPLACE FUNCTION {fn}() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,{schema} AS $$ {body()} $$'))
            for name in FIELDS:
                table=f'{schema}.{q(name)}'
                c.execute(text(f'DROP TRIGGER IF EXISTS zova_identity_guard ON {table}'))
                c.execute(text(f'CREATE TRIGGER zova_identity_guard BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION {fn}()'))
        else:
            for name in FIELDS:
                c.exec_driver_sql(f'DROP TRIGGER IF EXISTS {q(name+"_identity_guard")}')
                c.exec_driver_sql(sqlite_definition(c,name))
        c.execute(text('INSERT INTO zova_schema_migrations(version,applied_at) VALUES(:version,CURRENT_TIMESTAMP) ON CONFLICT(version) DO NOTHING'),{'version':VERSION})
        report=verify_identities(c)
        return {**report,'writes_performed':True}
