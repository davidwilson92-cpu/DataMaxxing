"""Offline account row policies; authentication/worker routing is not activated."""
import re
from textwrap import dedent
from sqlalchemy import text,String
from .account_references import ACCOUNT_TABLES,verify_account_guards
from .migration_limits import bound_migration
from .rls import verify_context_functions

VERSION='20261010_account_rls'
# Authority, billing and measurement writes need dedicated service integration.
EDITABLE=frozenset({'nova_creator_preferences','zova_brands'})


def caps(table,operation):
    if operation=='select':return ['account.edit','account.read'] if table in EDITABLE else ['account.read']
    return ['account.edit'] if table in EDITABLE else []


def definition(c):
    q=c.dialect.identifier_preparer.quote
    schema=q(c.scalar(text('SELECT current_schema()')))
    return f'''CREATE OR REPLACE FUNCTION {schema}.zova_account_allowed(
        p_user integer,p_actor name,allowed text[]) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,{schema} AS $$
        SELECT CASE WHEN p_actor=current_user THEN true ELSE EXISTS (
            SELECT 1 FROM {schema}.zova_workspaces w
            WHERE w.id=(SELECT {schema}.zova_rls_workspace(allowed))
              AND w.legacy_brand_id=0 AND w.owner_user_id=p_user) END
        $$'''


def verify_runtime_authority(c,*,runtime_roles,owner):
    """Recheck effective role authority after installation, without changing it."""
    q=c.dialect.identifier_preparer.quote
    schema=q(c.scalar(text('SELECT current_schema()')))
    for role in set(runtime_roles):
        attributes=c.execute(text('SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=:role'),{'role':role}).first()
        if not attributes or any(attributes):raise ValueError('Restricted account runtime roles required')
        dangerous=c.scalar(text('''SELECT EXISTS(SELECT 1 FROM pg_roles r WHERE pg_has_role(:role,r.oid,'MEMBER')
            AND (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls OR r.rolname LIKE 'pg_%'))
            OR pg_has_role(:role,:owner,'MEMBER')
            OR has_schema_privilege(:role,current_schema(),'CREATE')
            OR has_database_privilege(:role,current_database(),'CREATE')'''),{'role':role,'owner':owner})
        if dangerous:raise ValueError('Account runtime inherits privileged authority')
        for name in ACCOUNT_TABLES:
            if c.scalar(text("SELECT has_table_privilege(:role,:table,'TRUNCATE,TRIGGER,REFERENCES')"),{'role':role,'table':f'{schema}.{q(name)}'}):
                raise ValueError('Account runtime has destructive privileges')


def verify_account_policies(c,*,runtime_roles):
    if c.dialect.name!='postgresql' or not runtime_roles:raise ValueError('Account policies require PostgreSQL runtime roles')
    q=c.dialect.identifier_preparer.quote
    schema=q(c.scalar(text('SELECT current_schema()')))
    signature=f'{schema}.zova_account_allowed(integer,name,text[])'
    row=c.execute(text('''SELECT p.prosrc,p.prosecdef,p.provolatile,p.proisstrict,p.proleakproof,
        p.proconfig,p.proargnames,p.proargmodes,p.pronargdefaults,p.prokind,p.proretset,p.proparallel,
        p.prosupport=0 AS no_support,p.prorettype='boolean'::regtype AS result,l.lanname,p.proowner::bigint AS owner
        FROM pg_proc p JOIN pg_language l ON l.oid=p.prolang
        WHERE p.oid=to_regprocedure(:signature)'''),{'signature':signature}).mappings().first()
    if (not row or dedent(row['prosrc']).strip()!=dedent(definition(c).split('$$')[1]).strip()
        or not row['prosecdef'] or row['provolatile']!='s' or row['proisstrict'] or row['proleakproof']
        or row['proconfig']!=[f'search_path=pg_catalog, {schema}'] or row['lanname']!='sql'
        or not row['result'] or row['proargnames']!=['p_user','p_actor','allowed']
        or row['proargmodes'] is not None or row['pronargdefaults'] or row['prokind']!='f'
        or row['proretset'] or row['proparallel']!='u' or not row['no_support']):
        raise ValueError('Account policy function differs from source')
    ids=dict(c.execute(text('SELECT rolname,oid::bigint FROM pg_roles')).all())
    if not set(runtime_roles)<=ids.keys():raise ValueError('Account runtime roles missing')
    owner=next(name for name,oid in ids.items() if oid==row['owner'])
    verify_runtime_authority(c,runtime_roles=runtime_roles,owner=owner)
    expected_roles=sorted({ids[r] for r in runtime_roles}|{row['owner']})
    grants=set(c.execute(text('''SELECT a.grantee::bigint,a.is_grantable FROM pg_proc p
        CROSS JOIN LATERAL aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) a
        WHERE p.oid=to_regprocedure(:signature) AND a.privilege_type='EXECUTE' '''),{'signature':signature}))
    if ({oid for oid,_ in grants}!=set(expected_roles)
        or any(grantable and oid!=row['owner'] for oid,grantable in grants)):
        raise ValueError('Account policy function execution grants differ')
    literal=String().literal_processor(c.dialect)
    for name in sorted(ACCOUNT_TABLES):
        table=f'{schema}.{q(name)}'
        flags=c.execute(text('SELECT relkind,relrowsecurity,relforcerowsecurity,relowner::bigint FROM pg_class WHERE oid=CAST(:table AS regclass)'),{'table':table}).one()
        if tuple(flags)!=('r',True,True,row['owner']):raise ValueError('Account policies disabled or owner differs')
        expected={'zova_account_access':('*',True,expected_roles,'true','true')}
        for operation,command in [('select','r'),('insert','a'),('update','w'),('delete','d')]:
            values=caps(name,operation)
            arg=('ARRAY['+', '.join(literal(v)+'::text' for v in values)+']') if values else 'ARRAY[]::text[]'
            expr=f'zova_account_allowed(user_id, CURRENT_USER, {arg})'
            expected['zova_account_'+operation]=(command,False,[0],None if operation=='insert' else expr,expr if operation in {'insert','update'} else None)
        actual={}
        for p in c.execute(text('''SELECT polname,polcmd,polpermissive,
            ARRAY(SELECT r::bigint FROM unnest(polroles) r ORDER BY 1),
            pg_get_expr(polqual,polrelid,false),pg_get_expr(polwithcheck,polrelid,false)
            FROM pg_policy WHERE polrelid=CAST(:table AS regclass)'''),{'table':table}):
            norm=lambda v:re.sub(r'\s+',' ',v).strip() if v is not None else None
            actual[p[0]]=(p[1],p[2],p[3],norm(p[4]),norm(p[5]))
        if actual!=expected:raise ValueError('Account policy definitions differ from manifest')


def apply_account_rls(engine,*,runtime_roles,writes_paused=False):
    if not writes_paused:raise ValueError('Pause application and worker writes before account RLS')
    if not runtime_roles:raise ValueError('Explicit runtime roles required')
    with engine.begin() as c:
        if c.dialect.name!='postgresql':raise ValueError('Account RLS requires PostgreSQL')
        bound_migration(c)
        c.execute(text('SELECT pg_advisory_xact_lock(61010002)'))
        verify_account_guards(c)
        verify_context_functions(c,runtime_roles=runtime_roles)
        q=c.dialect.identifier_preparer.quote
        owner,schema_name=c.execute(text('SELECT current_user,current_schema()')).one()
        schema=q(schema_name)
        for signature in ('zova_issue_context(text,integer,text,integer,integer,text,text,integer,text,integer)','zova_rls_workspace(text[])'):
            if c.scalar(text('SELECT pg_get_userbyid(proowner) FROM pg_proc WHERE oid=to_regprocedure(:signature)'),{'signature':f'{schema}.{signature}'})!=owner:
                raise ValueError('Account and workspace policy functions must share the trusted migration owner')
        verify_runtime_authority(c,runtime_roles=runtime_roles,owner=owner)
        for name in sorted(ACCOUNT_TABLES):
            table=f'{schema}.{q(name)}'
            if c.scalar(text('SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid=CAST(:table AS regclass)'),{'table':table})!=owner:
                raise ValueError('Account migration must use the table owner')
            c.execute(text(f'LOCK TABLE {table} IN ACCESS EXCLUSIVE MODE'))
        c.execute(text(definition(c)))
        signature=f'{schema}.zova_account_allowed(integer,name,text[])'
        prior=c.scalars(text('''SELECT r.rolname FROM pg_proc p
            CROSS JOIN LATERAL aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) a
            JOIN pg_roles r ON r.oid=a.grantee WHERE p.oid=to_regprocedure(:signature) AND a.grantee<>p.proowner'''),{'signature':signature}).all()
        roles=','.join(q(r) for r in sorted(set(runtime_roles)|set(prior)))
        c.execute(text(f'REVOKE ALL ON FUNCTION {signature} FROM PUBLIC,{roles}'))
        c.execute(text(f'GRANT EXECUTE ON FUNCTION {signature} TO '+','.join(q(r) for r in sorted(set(runtime_roles)))))
        literal=String().literal_processor(c.dialect)
        for name in sorted(ACCOUNT_TABLES):
            table=f'{schema}.{q(name)}'
            for operation in ('select','insert','update','delete'):
                values='ARRAY['+','.join(literal(v) for v in caps(name,operation))+']::text[]'
                expr=f'{schema}.zova_account_allowed(user_id,CURRENT_USER,{values})'
                clause={'select':f'USING ({expr})','insert':f'WITH CHECK ({expr})',
                    'update':f'USING ({expr}) WITH CHECK ({expr})','delete':f'USING ({expr})'}[operation]
                c.execute(text(f'DROP POLICY IF EXISTS zova_account_{operation} ON {table}'))
                c.execute(text(f'CREATE POLICY zova_account_{operation} ON {table} AS RESTRICTIVE FOR {operation.upper()} TO PUBLIC {clause}'))
            c.execute(text(f'DROP POLICY IF EXISTS zova_account_access ON {table}'))
            c.execute(text(f'CREATE POLICY zova_account_access ON {table} AS PERMISSIVE FOR ALL TO '+','.join(q(r) for r in sorted(set(runtime_roles)|{owner}))+' USING (true) WITH CHECK (true)'))
            c.execute(text(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY'))
            c.execute(text(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY'))
        verify_account_policies(c,runtime_roles=runtime_roles)
        c.execute(text('INSERT INTO zova_schema_migrations(version,applied_at) VALUES (:version,CURRENT_TIMESTAMP) ON CONFLICT(version) DO NOTHING'),{'version':VERSION})
    return {'version':VERSION,'protected_tables':len(ACCOUNT_TABLES),'runtime_integrated':False}
