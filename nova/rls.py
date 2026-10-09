"""Offline PostgreSQL tenant policies and short-lived server-only DB contexts.

Not activated by application startup. Web/worker context rollout is separate.
"""
import hashlib
import json
import re
import secrets
from textwrap import dedent
from sqlalchemy import text, String
from sqlalchemy.exc import SQLAlchemyError
from .capabilities import ROLE_CAPABILITIES
from .migration_limits import bound_migration
from .tenant_references import BRAND_TABLES, verify_references

VERSION = '20261009_workspace_rls'
WRITE_CAPABILITIES = {
    'zova_brand_voices': {'posts.edit'},
    'nova_social_connections': {'connections.create','connections.delete','posts.publish','posts.schedule','analytics.read'},
    'nova_oauth_states': {'connections.create'},
    'nova_drafts': {'posts.create','posts.edit','posts.delete','posts.publish','posts.schedule','posts.cancel'},
    'zova_publish_reviews': {'posts.publish','posts.schedule'},
    'zova_publications': {'posts.publish','posts.schedule','posts.cancel'},
    'nova_media_assets': {'media.create','media.delete','posts.publish'},
    'nova_scheduled_posts': {'posts.publish','posts.schedule','posts.cancel'},
    'nova_activity': {'posts.publish','posts.schedule','posts.cancel','connections.create','connections.delete'},
    'zova_pending_connections': {'connections.create'},
    'zova_performance_snapshots': {'analytics.read'},
    'zova_strategies': {'posts.edit'},
    'zova_strategy_actions': {'posts.edit'},
    'zova_content_series': {'posts.edit','posts.publish','posts.cancel'},
    'zova_series_occurrences': {'posts.edit','posts.publish','posts.cancel','posts.schedule'},
    'zova_series_approvals': {'posts.publish'},
}

# Deleting an unsubmitted draft removes its review and detaches linked plans.
# Do not grant this capability to all writes on these tables: deleting a draft
# must not confer permission to create approval records or delete whole plans.
OPERATION_EXTRAS = {
    ('zova_publish_reviews', 'delete'): {'posts.delete'},
    ('zova_strategy_actions', 'update'): {'posts.delete'},
    ('zova_series_occurrences', 'update'): {'posts.delete'},
}


def operation_capabilities(table, operation):
    if operation not in {'insert', 'update', 'delete'}:
        raise ValueError('Unsupported row mutation')
    return WRITE_CAPABILITIES[table] | OPERATION_EXTRAS.get((table, operation), set())


def issue_context(issuer_engine, runtime_connection, *, user_id, workspace_id, auth_version,
                  membership_revision, capability, runtime_role, ttl_seconds=60):
    """Caller must obtain identity/versions from validated authentication, never a request body."""
    if type(ttl_seconds) is not int or not 1 <= ttl_seconds <= 300:
        raise ValueError('Database context lifetime must be 1–300 seconds')
    if runtime_connection.dialect.name != 'postgresql':raise RuntimeError('Database contexts require PostgreSQL')
    if runtime_connection.scalar(text('SHOW transaction_isolation')) != 'read committed':
        raise RuntimeError('Database contexts require read committed transactions')
    transaction, backend = runtime_connection.execute(text('SELECT pg_current_xact_id()::text,pg_backend_pid()')).one()
    token = secrets.token_urlsafe(32)
    with issuer_engine.begin() as c:
        if c.dialect.name != 'postgresql':raise RuntimeError('Database contexts require PostgreSQL')
        c.execute(text('SELECT zova_issue_context(:digest,:uid,:wid,:version,:revision,:cap,:aud,:ttl,:transaction,:backend)'),
                  {'digest':hashlib.sha256(token.encode()).hexdigest(), 'uid':user_id,
                   'wid':workspace_id,'version':auth_version,'revision':membership_revision,
                   'cap':capability,'aud':runtime_role,'ttl':ttl_seconds,'transaction':transaction,'backend':backend})
    return token


def bind_context(connection, token):
    if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}',token):
        raise ValueError('Invalid database context')
    if connection.dialect.name != 'postgresql':raise RuntimeError('Database contexts require PostgreSQL')
    # Transaction-local: commit/rollback must clear authority before pool reuse.
    try:
        connection.execute(text("SELECT set_config('zova.workspace_context',:token,true)"),{'token':token})
    except SQLAlchemyError:
        # SQLAlchemy errors can contain bound parameters. Do not propagate the
        # server-only bearer into ordinary application exception diagnostics.
        raise RuntimeError('Database workspace context could not be bound') from None


def context_function_definitions(c, runtime_roles):
    """One source for offline installation and read-only definition verification."""
    schema = c.dialect.identifier_preparer.quote(c.scalar(text('SELECT current_schema()')))
    literal = String().literal_processor(c.dialect)
    caps=literal(json.dumps({role:sorted(values) for role,values in ROLE_CAPABILITIES.items()}))
    audiences='ARRAY['+','.join(literal(role) for role in sorted(set(runtime_roles)))+']::text[]'
    issue = f'''CREATE OR REPLACE FUNCTION {schema}.zova_issue_context(
        p_digest text, p_uid integer, p_wid text, p_version integer, p_revision integer,
        p_cap text, p_audience text, p_ttl integer, p_transaction_id text, p_backend integer) RETURNS void
        LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,{schema} AS $$
        BEGIN
          IF p_ttl IS NULL OR p_ttl < 1 OR p_ttl > 300 OR p_digest IS NULL OR p_digest !~ '^[0-9a-f]{{64}}$'
            OR p_audience IS NULL OR NOT (p_audience=ANY({audiences}))
            OR p_transaction_id IS NULL OR p_transaction_id !~ '^[0-9]+$' OR p_backend IS NULL OR p_backend < 1
            OR NOT EXISTS (SELECT 1 FROM {schema}.zova_workspace_memberships m
              JOIN {schema}.nova_users u ON u.id=m.user_id
              JOIN {schema}.zova_workspaces w ON w.id=m.workspace_id
              WHERE m.user_id=p_uid AND m.workspace_id=p_wid AND w.owner_user_id=p_uid
              AND u.active AND m.active AND u.auth_version=p_version AND m.revision=p_revision
              AND ({caps}::jsonb -> m.role) ? p_cap) THEN
            RAISE EXCEPTION 'Database workspace authority denied' USING ERRCODE='42501';
          END IF;
          DELETE FROM {schema}.zova_db_contexts WHERE token_hash IN (
            SELECT token_hash FROM {schema}.zova_db_contexts WHERE expires_at < clock_timestamp()
            ORDER BY expires_at LIMIT 1000 FOR UPDATE SKIP LOCKED);
          INSERT INTO {schema}.zova_db_contexts VALUES
            (p_digest,p_uid,p_wid,p_version,p_revision,p_cap,p_audience,clock_timestamp()+p_ttl*interval '1 second',p_transaction_id,p_backend);
        END $$'''
    resolve = f'''CREATE OR REPLACE FUNCTION {schema}.zova_rls_workspace(allowed text[] DEFAULT NULL)
        RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,{schema} AS $$
        SELECT d.workspace_id FROM {schema}.zova_db_contexts d
        JOIN {schema}.nova_users u ON u.id=d.user_id
        JOIN {schema}.zova_workspace_memberships m ON m.user_id=d.user_id AND m.workspace_id=d.workspace_id
        JOIN {schema}.zova_workspaces w ON w.id=d.workspace_id AND w.owner_user_id=d.user_id
        WHERE d.token_hash=encode(sha256(convert_to(current_setting('zova.workspace_context',true),'UTF8')),'hex')
        AND d.runtime_role=session_user AND d.expires_at > statement_timestamp()
        AND d.transaction_id=pg_current_xact_id_if_assigned()::text AND d.backend_pid=pg_backend_pid()
        AND u.active AND m.active AND u.auth_version=d.auth_version AND m.revision=d.membership_revision
        AND ({caps}::jsonb -> m.role) ? d.capability
        AND (allowed IS NULL OR d.capability=ANY(allowed))
        $$'''
    return {'issue': issue, 'resolve': resolve}


def verify_context_functions(c, *, runtime_roles):
    """Read catalog definitions; never execute, repair or trust a stored digest.

    This validates the two context functions, not the complete table-policy or
    service-grant manifest. It belongs alongside those separate checks.
    """
    if c.dialect.name != 'postgresql':
        raise ValueError('Context verification requires PostgreSQL')
    schema = c.dialect.identifier_preparer.quote(c.scalar(text('SELECT current_schema()')))
    specs = {
        'issue': ('zova_issue_context(text,integer,text,integer,integer,text,text,integer,text,integer)',
                  'plpgsql', 'v', 'void',
                  ['p_digest','p_uid','p_wid','p_version','p_revision','p_cap',
                   'p_audience','p_ttl','p_transaction_id','p_backend'], None),
        'resolve': ('zova_rls_workspace(text[])', 'sql', 's', 'text', ['allowed'], 'NULL::text[]'),
    }
    for purpose, definition in context_function_definitions(c, runtime_roles).items():
        signature, language, volatility, result, arguments, default = specs[purpose]
        row = c.execute(text('''SELECT p.prosrc, l.lanname, p.provolatile,
            p.prorettype=CAST(:result AS regtype) AS return_type_matches,
            p.prosecdef, p.proleakproof, p.proisstrict, p.proretset, p.prokind,
            p.proparallel, p.prosupport=0 AS no_support, p.proconfig,
            p.proargnames, p.proargmodes, p.pronargdefaults,
            pg_get_expr(p.proargdefaults,0) AS argument_defaults
            FROM pg_proc p JOIN pg_language l ON l.oid=p.prolang
            WHERE p.oid=to_regprocedure(:signature)'''),
            {'signature': f'{schema}.{signature}', 'result': result}).mappings().first()
        expected_body = dedent(definition.split('$$')[1]).strip()
        if (row is None or dedent(row['prosrc']).strip() != expected_body
                or row['lanname'] != language or row['provolatile'] != volatility
                or not row['return_type_matches'] or not row['prosecdef']
                or row['proleakproof'] or row['proisstrict'] or row['proretset']
                or row['prokind'] != 'f' or row['proparallel'] != 'u' or not row['no_support']
                or row['proconfig'] != [f'search_path=pg_catalog, {schema}']
                or row['proargnames'] != arguments or row['proargmodes'] is not None
                or row['pronargdefaults'] != (1 if default else 0)
                or row['argument_defaults'] != default):
            raise ValueError('Database context function definition does not match the reviewed implementation')


def apply_rls(engine, *, runtime_roles, issuer_roles, writes_paused=False):
    if not writes_paused:raise ValueError('Pause application and worker writes before RLS migration')
    if not runtime_roles or not issuer_roles or set(runtime_roles) & set(issuer_roles):
        raise ValueError('Separate runtime and context-issuer identities are required')
    if set(WRITE_CAPABILITIES) != BRAND_TABLES:raise RuntimeError('RLS table manifest is incomplete')
    with engine.begin() as c:
        if c.dialect.name != 'postgresql':raise RuntimeError('RLS migration requires PostgreSQL')
        bound_migration(c)
        c.execute(text('SELECT pg_advisory_xact_lock(61009002)'))
        q = c.dialect.identifier_preparer.quote
        schema = q(c.scalar(text('SELECT current_schema()')))
        literal = String().literal_processor(c.dialect)
        for role in set(runtime_roles) | set(issuer_roles):
            row=c.execute(text('SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=:role'),{'role':role}).first()
            if not row or any(row):raise ValueError('RLS service identities must exist without administrative attributes')
            broad=c.scalar(text('''SELECT EXISTS (SELECT 1 FROM pg_roles r
                WHERE pg_has_role(:role,r.oid,'MEMBER') AND
                (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls OR r.rolname LIKE 'pg_%'))'''),{'role':role})
            owns=c.scalar(text('''SELECT EXISTS (SELECT 1 FROM pg_class t JOIN pg_namespace n ON n.oid=t.relnamespace
                WHERE n.nspname=current_schema() AND pg_has_role(:role,t.relowner,'MEMBER'))'''),{'role':role})
            creates=c.scalar(text("SELECT has_schema_privilege(:role,current_schema(),'CREATE') OR has_database_privilege(:role,current_database(),'CREATE')"),{'role':role})
            if broad or owns or creates:raise ValueError('RLS service identities must not inherit administrative or owner authority')
            for name in BRAND_TABLES:
                if c.scalar(text("SELECT has_table_privilege(:role,:table,'TRUNCATE,TRIGGER,REFERENCES')"),{'role':role,'table':f'{schema}.{q(name)}'}):
                    raise ValueError('RLS service identities must not bypass row policies with destructive table privileges')
        for runtime in runtime_roles:
            for issuer in issuer_roles:
                if c.scalar(text("SELECT pg_has_role(:runtime,:issuer,'MEMBER') OR pg_has_role(:issuer,:runtime,'MEMBER')"),{'runtime':runtime,'issuer':issuer}):
                    raise ValueError('Runtime and issuer role membership must be separate')
            for protected in ('nova_users','zova_workspaces','zova_workspace_memberships','zova_schema_migrations'):
                if c.scalar(text("SELECT has_table_privilege(:role,:table,'INSERT,UPDATE,DELETE,TRUNCATE')"),{'role':runtime,'table':f'{schema}.{q(protected)}'}):
                    raise ValueError('Runtime must not directly mutate workspace authority or migration records')
        for name in sorted(BRAND_TABLES):
            c.execute(text(f'LOCK TABLE {schema}.{q(name)} IN ACCESS EXCLUSIVE MODE'))
        verify_references(c)
        # Only hashes are retained; the runtime role cannot enumerate or mint contexts.
        c.execute(text(f'''CREATE TABLE IF NOT EXISTS {schema}.zova_db_contexts (
            token_hash VARCHAR(64) PRIMARY KEY CHECK (token_hash ~ '^[0-9a-f]{{64}}$'),
            user_id INTEGER NOT NULL REFERENCES {schema}.nova_users(id),
            workspace_id VARCHAR(36) NOT NULL REFERENCES {schema}.zova_workspaces(id),
            auth_version INTEGER NOT NULL, membership_revision INTEGER NOT NULL,
            capability TEXT NOT NULL, runtime_role TEXT NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL, transaction_id TEXT NOT NULL, backend_pid INTEGER NOT NULL)'''))
        c.execute(text(f'CREATE INDEX IF NOT EXISTS zova_db_context_expiry ON {schema}.zova_db_contexts(expires_at)'))
        for definition in context_function_definitions(c, runtime_roles).values():
            c.execute(text(definition))
        issue=f'{schema}.zova_issue_context(text,integer,text,integer,integer,text,text,integer,text,integer)'
        resolve=f'{schema}.zova_rls_workspace(text[])'
        identities=','.join(q(role) for role in sorted(set(runtime_roles)|set(issuer_roles)))
        c.execute(text(f'REVOKE ALL ON {schema}.zova_db_contexts FROM PUBLIC,{identities}'))
        for role in set(runtime_roles)|set(issuer_roles):
            if c.scalar(text("SELECT has_table_privilege(:role,:table,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE')"),{'role':role,'table':f'{schema}.zova_db_contexts'}):
                raise ValueError('Service identities must not inherit direct database context access')
        for function in (issue,resolve):
            previous=c.scalars(text('''SELECT r.rolname FROM pg_proc p
                CROSS JOIN LATERAL aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) a
                JOIN pg_roles r ON r.oid=a.grantee
                WHERE p.oid=to_regprocedure(:signature) AND a.grantee<>p.proowner'''),{'signature':function}).all()
            revoke=','.join(q(role) for role in sorted(set(previous)|set(runtime_roles)|set(issuer_roles)))
            c.execute(text(f'REVOKE ALL ON FUNCTION {function} FROM PUBLIC,{revoke}'))
        c.execute(text(f'GRANT EXECUTE ON FUNCTION {issue} TO '+','.join(q(role) for role in issuer_roles)))
        c.execute(text(f'GRANT EXECUTE ON FUNCTION {resolve} TO '+','.join(q(role) for role in runtime_roles)))
        for name in sorted(BRAND_TABLES):
            table=f'{schema}.{q(name)}'
            read=f'workspace_id=(SELECT {schema}.zova_rls_workspace(NULL))'
            # Restrictive policies prevent an unrelated permissive policy from
            # turning this boundary into an OR-condition that leaks other tenants.
            for operation in ('select','insert','update','delete'):
                if operation == 'select':
                    clause=f'USING ({read})'
                else:
                    write_caps='ARRAY['+','.join(literal(cap) for cap in sorted(operation_capabilities(name,operation)))+']::text[]'
                    write=f'workspace_id=(SELECT {schema}.zova_rls_workspace({write_caps}))'
                    clause={'insert':f'WITH CHECK ({write})','update':f'USING ({write}) WITH CHECK ({write})',
                            'delete':f'USING ({write})'}[operation]
                policy='zova_tenant_'+operation
                c.execute(text(f'DROP POLICY IF EXISTS {policy} ON {table}'))
                c.execute(text(f'CREATE POLICY {policy} ON {table} AS RESTRICTIVE FOR {operation.upper()} TO PUBLIC {clause}'))
            c.execute(text(f'DROP POLICY IF EXISTS zova_runtime_access ON {table}'))
            c.execute(text(f'CREATE POLICY zova_runtime_access ON {table} AS PERMISSIVE FOR ALL TO '+','.join(q(role) for role in runtime_roles)+' USING (true) WITH CHECK (true)'))
            c.execute(text(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY'))
            c.execute(text(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY'))
        c.execute(text('INSERT INTO zova_schema_migrations(version,applied_at) VALUES (:version,CURRENT_TIMESTAMP) ON CONFLICT(version) DO NOTHING'),{'version':VERSION})
    return {'version':VERSION,'protected_tables':len(BRAND_TABLES),'runtime_integrated':False}
