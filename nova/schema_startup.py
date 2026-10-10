"""Read-only runtime schema checks, independent of the application model import."""
import os
from sqlalchemy import inspect, text
from .migrations import MIGRATIONS
from .tenant_references import BRAND_TABLES, VERSION as REFERENCE_VERSION
from .account_references import VERSION as ACCOUNT_VERSION,verify_account_guards
from .identity_guards import VERSION as IDENTITY_VERSION,verify_identities
from .tenant_migration import MappingError


def schema_mode(engine):
    mode = os.environ.get('ZOVA_SCHEMA_MODE')
    if mode is None:
        mode = 'verify' if engine.dialect.name == 'postgresql' else 'bootstrap'
    if mode not in {'verify', 'bootstrap'}:
        raise RuntimeError('ZOVA_SCHEMA_MODE must be verify or bootstrap')
    return mode


def verify_runtime_role(c):
    if c.dialect.name != 'postgresql':
        return
    # Membership matters even when privileges are not inherited: SET ROLE must
    # not provide a route back to a privileged or table-owning identity.
    privileged = c.scalar(text('''SELECT EXISTS (
        SELECT 1 FROM pg_roles r WHERE (pg_has_role(current_user,r.oid,'MEMBER') OR pg_has_role(session_user,r.oid,'MEMBER'))
        AND (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls
             OR r.rolname LIKE 'pg_%'))'''))
    owns_database = c.scalar(text('''SELECT EXISTS (
        SELECT 1 FROM pg_database d WHERE d.datname=current_database()
        AND (pg_has_role(current_user,d.datdba,'MEMBER') OR pg_has_role(session_user,d.datdba,'MEMBER')))'''))
    owns_tables = c.scalar(text('''SELECT EXISTS (
        SELECT 1 FROM pg_class t JOIN pg_namespace n ON n.oid=t.relnamespace
        WHERE n.nspname=current_schema() AND t.relkind IN ('r','p')
        AND (pg_has_role(current_user,t.relowner,'MEMBER') OR pg_has_role(session_user,t.relowner,'MEMBER')))'''))
    creates = c.scalar(text("SELECT has_schema_privilege(current_user,current_schema(),'CREATE') OR has_schema_privilege(session_user,current_schema(),'CREATE')"))
    creates_schema = c.scalar(text("SELECT has_database_privilege(current_user,current_database(),'CREATE') OR has_database_privilege(session_user,current_database(),'CREATE')"))
    truncates = c.scalar(text('''SELECT EXISTS (
        SELECT 1 FROM pg_class t JOIN pg_namespace n ON n.oid=t.relnamespace
        WHERE n.nspname=current_schema() AND t.relkind IN ('r','p')
        AND (has_table_privilege(current_user,t.oid,'TRUNCATE') OR has_table_privilege(session_user,t.oid,'TRUNCATE')))'''))
    if privileged or owns_database or owns_tables or creates or creates_schema or truncates:
        raise RuntimeError('Runtime database identity has administrative, schema-owner or destructive privileges')


def verify_runtime_schema(c, metadata):
    inspector = inspect(c)
    tables = set(inspector.get_table_names())
    if not (set(metadata.tables) | {'zova_schema_migrations'}) <= tables:
        raise RuntimeError('Runtime schema is incomplete; apply the offline migration')
    for name, table in metadata.tables.items():
        columns = {column['name'] for column in inspector.get_columns(name)}
        if not set(table.c.keys()) <= columns:
            raise RuntimeError(f'{name}: runtime columns are incomplete; apply the offline migration')
    versions = set(c.scalars(text('SELECT version FROM zova_schema_migrations')))
    required = {version for version, _ in MIGRATIONS} | {
        REFERENCE_VERSION, ACCOUNT_VERSION, IDENTITY_VERSION, '20261009_optional_mfa', '20260929_legacy_publication_queue'}
    if not required <= versions:
        raise RuntimeError('Runtime schema migration versions are incomplete')
    try:verify_account_guards(c)
    except MappingError as exc:
        raise RuntimeError('Runtime account guards are missing or differ from the migration') from exc
    try:verify_identities(c)
    except MappingError as exc:
        raise RuntimeError('Runtime identity guards are missing or differ from the migration') from exc
    if c.dialect.name == 'postgresql':
        guards = set(c.execute(text('''SELECT t.relname,g.tgname,p.proname
            FROM pg_trigger g JOIN pg_class t ON t.oid=g.tgrelid
            JOIN pg_namespace n ON n.oid=t.relnamespace
            JOIN pg_proc p ON p.oid=g.tgfoid
            WHERE n.nspname=current_schema() AND p.pronamespace=n.oid
            AND NOT g.tgisinternal AND g.tgenabled IN ('O','A')''')))
        expected = {(name, 'zova_workspace_guard', 'zova_guard_workspace_reference') for name in BRAND_TABLES}
        expected.add(('zova_workspaces','zova_workspace_identity_guard','zova_guard_workspace_identity'))
        if not expected <= guards:
            raise RuntimeError('Runtime workspace guards are missing or disabled')
        for name in BRAND_TABLES:
            columns = {col['name']:col for col in inspector.get_columns(name)}
            keys = inspector.get_foreign_keys(name)
            if columns['workspace_id']['nullable'] or not any(
                    key['constrained_columns'] == ['workspace_id']
                    and key['referred_table'] == 'zova_workspaces'
                    and key['referred_columns'] == ['id']
                    and key['referred_schema'] in (None, inspector.default_schema_name) for key in keys):
                raise RuntimeError('Runtime workspace constraints are incomplete')
    elif c.dialect.name == 'sqlite':
        triggers = set(c.scalars(text("SELECT name FROM sqlite_master WHERE type='trigger'")))
        expected = {name + '_workspace_' + suffix for name in BRAND_TABLES
                    for suffix in ('insert','fill','update','delete_workspace')}
        if not (expected | {'zova_workspace_identity_guard'}) <= triggers:
            raise RuntimeError('Runtime workspace guards are missing')
    else:
        raise RuntimeError('Unsupported runtime database')
