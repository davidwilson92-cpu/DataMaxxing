"""Offline canonical references and immutable database ownership guards.

These write constraints are a prerequisite for RLS, not a substitute for it.
"""
from sqlalchemy import MetaData, inspect, text
from .tenant_migration import MappingError, inspect_mapping

VERSION = '20261009_workspace_references'
BRAND_TABLES = frozenset({
    'zova_brand_voices','nova_social_connections','nova_oauth_states','nova_drafts',
    'zova_publish_reviews','zova_publications','nova_media_assets','nova_scheduled_posts',
    'nova_activity','zova_pending_connections','zova_performance_snapshots','zova_strategies',
    'zova_strategy_actions','zova_content_series','zova_series_occurrences','zova_series_approvals',
})


def _inventory(c):
    metadata=MetaData();metadata.reflect(bind=c)
    if 'zova_workspaces' not in metadata.tables:
        raise MappingError('Apply and verify the workspace registry first')
    discovered={name for name,table in metadata.tables.items() if {'user_id','brand_id'} <= set(table.c.keys())}
    if discovered-BRAND_TABLES:
        raise MappingError('Unclassified brand-owned tables require explicit migration review')
    return sorted(discovered)


def _q(c,name):
    return c.dialect.identifier_preparer.quote(name)


def plan_references(c):
    tables=_inventory(c)
    inspect_mapping(c)
    missing=[]
    for name in tables:
        quoted=_q(c,name)
        if 'workspace_id' not in {col['name'] for col in inspect(c).get_columns(name)}:
            missing.append(name)
        invalid=c.scalar(text(f"SELECT COUNT(*) FROM {quoted} s LEFT JOIN zova_workspaces w ON w.owner_user_id=s.user_id AND w.legacy_brand_id=s.brand_id WHERE w.id IS NULL"))
        if invalid:raise MappingError(f'{name}: canonical ownership mapping is missing')
    return {'version':VERSION,'tables':tables,'tables_needing_column':missing,'writes_performed':False,'read_isolation_enforced':False}


def verify_references(c):
    tables=_inventory(c)
    counts={}
    for name in tables:
        if 'workspace_id' not in {col['name'] for col in inspect(c).get_columns(name)}:
            raise MappingError(f'{name}: canonical workspace reference is missing')
        quoted=_q(c,name)
        invalid=c.scalar(text(f'''SELECT COUNT(*) FROM {quoted} AS source
            LEFT JOIN zova_workspaces AS workspace ON workspace.id=source.workspace_id
            AND workspace.owner_user_id=source.user_id AND workspace.legacy_brand_id=source.brand_id
            WHERE workspace.id IS NULL'''))
        if invalid:raise MappingError(f'{name}: {invalid} invalid canonical references')
        counts[name]=c.scalar(text(f'SELECT COUNT(*) FROM {quoted}'))
    return {'version':VERSION,'mapped_table_counts':counts,'read_isolation_enforced':False}


def _postgres_guards(c,tables):
    schema=_q(c,c.scalar(text('SELECT current_schema()')))
    registry=f'{schema}.zova_workspaces'
    fn=f'{schema}.zova_guard_workspace_reference'
    c.execute(text(f'''CREATE OR REPLACE FUNCTION {fn}() RETURNS trigger LANGUAGE plpgsql
        SET search_path = pg_catalog, {schema} AS $$
        DECLARE expected varchar(36);
        BEGIN
          IF TG_OP = 'UPDATE' AND (NEW.user_id IS DISTINCT FROM OLD.user_id
              OR NEW.brand_id IS DISTINCT FROM OLD.brand_id
              OR NEW.workspace_id IS DISTINCT FROM OLD.workspace_id) THEN
            RAISE EXCEPTION 'Workspace ownership is immutable' USING ERRCODE='23514';
          END IF;
          SELECT id INTO expected FROM {registry}
            WHERE owner_user_id=NEW.user_id AND legacy_brand_id=NEW.brand_id;
          IF expected IS NULL OR (NEW.workspace_id IS NOT NULL AND NEW.workspace_id <> expected) THEN
            RAISE EXCEPTION 'Invalid workspace ownership' USING ERRCODE='23514';
          END IF;
          NEW.workspace_id := expected;
          RETURN NEW;
        END $$'''))
    for name in tables:
        table=f'{schema}.{_q(c,name)}'
        c.execute(text(f'DROP TRIGGER IF EXISTS zova_workspace_guard ON {table}'))
        c.execute(text(f'CREATE TRIGGER zova_workspace_guard BEFORE INSERT OR UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION {fn}()'))
        c.execute(text(f'ALTER TABLE {table} ALTER COLUMN workspace_id SET NOT NULL'))
    c.execute(text(f'''CREATE OR REPLACE FUNCTION {schema}.zova_guard_workspace_identity() RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog, {schema} AS $$
        BEGIN
          IF NEW.id IS DISTINCT FROM OLD.id OR NEW.owner_user_id IS DISTINCT FROM OLD.owner_user_id
             OR NEW.legacy_brand_id IS DISTINCT FROM OLD.legacy_brand_id THEN
            RAISE EXCEPTION 'Workspace identity is immutable' USING ERRCODE='23514';
          END IF;
          RETURN NEW;
        END $$'''))
    c.execute(text(f'DROP TRIGGER IF EXISTS zova_workspace_identity_guard ON {registry}'))
    c.execute(text(f'CREATE TRIGGER zova_workspace_identity_guard BEFORE UPDATE ON {registry} FOR EACH ROW EXECUTE FUNCTION {schema}.zova_guard_workspace_identity()'))


def _sqlite_guards(c,tables):
    for name in tables:
        table=_q(c,name)
        match='SELECT id FROM zova_workspaces WHERE owner_user_id=NEW.user_id AND legacy_brand_id=NEW.brand_id'
        for suffix in ('insert','fill','update','delete_workspace'):
            c.exec_driver_sql(f'DROP TRIGGER IF EXISTS {_q(c,name+"_workspace_"+suffix)}')
        c.exec_driver_sql(f'''CREATE TRIGGER {_q(c,name+'_workspace_insert')} BEFORE INSERT ON {table}
          BEGIN
            SELECT CASE WHEN NOT EXISTS ({match}) OR
              (NEW.workspace_id IS NOT NULL AND NEW.workspace_id IS NOT ({match}))
              THEN RAISE(ABORT,'Invalid workspace ownership') END;
          END''')
        c.exec_driver_sql(f'''CREATE TRIGGER {_q(c,name+'_workspace_fill')} AFTER INSERT ON {table}
          WHEN NEW.workspace_id IS NULL BEGIN
            UPDATE {table} SET workspace_id=({match}) WHERE rowid=NEW.rowid;
          END''')
        c.exec_driver_sql(f'''CREATE TRIGGER {_q(c,name+'_workspace_update')} BEFORE UPDATE ON {table}
          BEGIN
            SELECT CASE WHEN NEW.user_id IS NOT OLD.user_id OR NEW.brand_id IS NOT OLD.brand_id
              OR (OLD.workspace_id IS NOT NULL AND NEW.workspace_id IS NOT OLD.workspace_id)
              THEN RAISE(ABORT,'Workspace ownership is immutable') END;
            SELECT CASE WHEN NEW.workspace_id IS NULL OR NEW.workspace_id IS NOT ({match})
              THEN RAISE(ABORT,'Invalid workspace ownership') END;
          END''')
        # Enforce parent deletion even when an old SQLite client has foreign_keys disabled.
        c.exec_driver_sql(f'''CREATE TRIGGER {_q(c,name+'_workspace_delete_workspace')} BEFORE DELETE ON zova_workspaces
          WHEN EXISTS (SELECT 1 FROM {table} WHERE workspace_id=OLD.id)
          BEGIN SELECT RAISE(ABORT,'Workspace contains customer records'); END''')
    c.exec_driver_sql('DROP TRIGGER IF EXISTS zova_workspace_identity_guard')
    c.exec_driver_sql('''CREATE TRIGGER zova_workspace_identity_guard BEFORE UPDATE ON zova_workspaces
        WHEN NEW.id IS NOT OLD.id OR NEW.owner_user_id IS NOT OLD.owner_user_id OR NEW.legacy_brand_id IS NOT OLD.legacy_brand_id
        BEGIN SELECT RAISE(ABORT,'Workspace identity is immutable'); END''')


def apply_references(engine, *, writes_paused=False):
    if not writes_paused:raise MappingError('Pause application and worker writes before applying references')
    with engine.begin() as c:
        if c.dialect.name=='sqlite':c.exec_driver_sql('BEGIN IMMEDIATE')
        elif c.dialect.name=='postgresql':c.execute(text('SELECT pg_advisory_xact_lock(61009002)'))
        else:raise MappingError('Unsupported migration database')
        tables=_inventory(c)
        if c.dialect.name=='postgresql':
            for name in sorted([*tables,'zova_workspaces','nova_users','zova_brands']):
                c.execute(text(f'LOCK TABLE {_q(c,name)} IN ACCESS EXCLUSIVE MODE'))
        inspect_mapping(c)
        for name in tables:
            quoted=_q(c,name)
            invalid=c.scalar(text(f'''SELECT COUNT(*) FROM {quoted} s LEFT JOIN zova_workspaces w
                ON w.owner_user_id=s.user_id AND w.legacy_brand_id=s.brand_id WHERE w.id IS NULL'''))
            if invalid:raise MappingError(f'{name}: canonical ownership mapping is missing')
        for name in tables:
            quoted=_q(c,name)
            columns={col['name'] for col in inspect(c).get_columns(name)}
            if 'workspace_id' not in columns:
                c.execute(text(f'ALTER TABLE {quoted} ADD COLUMN workspace_id VARCHAR(36) REFERENCES zova_workspaces(id)'))
                c.execute(text(f'''UPDATE {quoted} SET workspace_id=(SELECT id FROM zova_workspaces w
                    WHERE w.owner_user_id={quoted}.user_id AND w.legacy_brand_id={quoted}.brand_id)'''))
            # Never repair a supplied/stale canonical reference by silently reassigning it.
            c.execute(text(f'CREATE INDEX IF NOT EXISTS {_q(c,name+"_workspace_idx")} ON {quoted} (workspace_id)'))
        if c.dialect.name=='postgresql':
            for name in tables:
                keys=inspect(c).get_foreign_keys(name)
                if not any(key['constrained_columns']==['workspace_id'] and key['referred_table']=='zova_workspaces' and key['referred_columns']==['id'] for key in keys):
                    c.execute(text(f'ALTER TABLE {_q(c,name)} ADD CONSTRAINT {_q(c,name+"_workspace_fk")} FOREIGN KEY (workspace_id) REFERENCES zova_workspaces(id)'))
        report=verify_references(c)
        (_postgres_guards if c.dialect.name=='postgresql' else _sqlite_guards)(c,tables)
        c.execute(text('INSERT INTO zova_schema_migrations (version,applied_at) VALUES (:version,CURRENT_TIMESTAMP) ON CONFLICT (version) DO NOTHING'),{'version':VERSION})
        return report
