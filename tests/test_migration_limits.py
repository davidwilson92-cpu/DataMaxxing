"""Contended migrations must fail and release their transaction, not hang."""
import pytest
from sqlalchemy import text, inspect
from sqlalchemy.exc import DBAPIError
from nova.migration_limits import bound_migration
from nova.tenant_migration import apply_registry
from nova.tenant_references import apply_references
from test_tenant_registry import registry_db


@pytest.mark.parametrize('limits', [
    {'lock_timeout_ms': 0}, {'lock_timeout_ms': True},
    {'lock_timeout_ms': 30001}, {'statement_timeout_ms': 0},
    {'statement_timeout_ms': 600001}, {'statement_timeout_ms': 100},
])
def test_unbounded_or_invalid_limits_rejected_before_schema_changes(registry_db, limits):
    engine, _ = registry_db
    with pytest.raises(ValueError, match='bounded'):
        apply_registry(engine, writes_paused=True, **limits)
    with engine.connect() as c:
        assert 'zova_workspaces' not in inspect(c).get_table_names()


@pytest.mark.parametrize('phase', ['registry', 'references'])
@pytest.mark.parametrize('held_lock', ['advisory', 'table'])
def test_busy_postgres_migration_rolls_back_and_can_be_retried(registry_db, phase, held_lock):
    engine, _ = registry_db
    if engine.dialect.name != 'postgresql':
        pytest.skip('Requires isolated PostgreSQL lock contention')
    if phase == 'references':
        apply_registry(engine, writes_paused=True)
    migrate = apply_registry if phase == 'registry' else apply_references
    with engine.begin() as blocker:
        if held_lock == 'advisory':
            blocker.execute(text('SELECT pg_advisory_xact_lock(61009002)'))
        else:
            blocker.execute(text('LOCK TABLE nova_drafts IN ROW EXCLUSIVE MODE'))
        with pytest.raises(DBAPIError) as caught:
            migrate(engine, writes_paused=True, lock_timeout_ms=100, statement_timeout_ms=2000)
        assert caught.value.orig.sqlstate == '55P03'
    with engine.connect() as c:
        if phase == 'registry':
            assert 'zova_workspaces' not in inspect(c).get_table_names()
        else:
            assert 'workspace_id' not in {col['name'] for col in inspect(c).get_columns('nova_drafts')}
    # Failed transaction returned its connection/locks; a clean retry succeeds.
    migrate(engine, writes_paused=True)


def test_statement_timeout_is_local_and_connection_recovers(registry_db):
    engine, _ = registry_db
    if engine.dialect.name != 'postgresql':
        pytest.skip('Requires PostgreSQL transaction-local timeouts')
    with engine.connect() as c:
        original = (c.scalar(text('SHOW lock_timeout')), c.scalar(text('SHOW statement_timeout')))
        c.rollback()
        with pytest.raises(DBAPIError) as caught:
            with c.begin():
                bound_migration(c, lock_timeout_ms=50, statement_timeout_ms=100)
                c.execute(text('SELECT pg_sleep(1)'))
        assert caught.value.orig.sqlstate == '57014'
        assert (c.scalar(text('SHOW lock_timeout')), c.scalar(text('SHOW statement_timeout'))) == original
        assert c.scalar(text('SELECT 1')) == 1
