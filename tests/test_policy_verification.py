import pytest
from sqlalchemy import text

from nova import database_services
from nova.rls import apply_rls, verify_workspace_policies
from test_database_services import service_pools
from test_rls import rls_db
from test_tenant_registry import registry_db


def test_installed_policy_manifest_is_readable_without_admin(rls_db):
    admin,runtime,issuer,roles,uids,drafts = rls_db
    with runtime.connect() as c:
        try:
            verify_workspace_policies(c,runtime_roles=[roles[0]])
        except ValueError:
            # Synthetic schema only: expose canonical SQL for diagnosing a
            # PostgreSQL deparser/version incompatibility, never customer rows.
            expressions=c.execute(text('''SELECT polname,
                pg_get_expr(polqual,polrelid,false),pg_get_expr(polwithcheck,polrelid,false)
                FROM pg_policy WHERE polrelid='nova_drafts'::regclass ORDER BY polname''')).all()
            raise AssertionError(f'Synthetic policy canonical expressions: {expressions}') from None
        assert c.scalar(text('SELECT count(*) FROM nova_drafts')) == 0


@pytest.mark.parametrize('alteration', [
    'ALTER TABLE nova_drafts DISABLE ROW LEVEL SECURITY',
    'ALTER TABLE nova_drafts NO FORCE ROW LEVEL SECURITY',
    'DROP POLICY zova_tenant_select ON nova_drafts',
    'ALTER POLICY zova_tenant_select ON nova_drafts USING (true)',
    'ALTER POLICY zova_tenant_update ON nova_drafts WITH CHECK (true)',
    'ALTER POLICY zova_tenant_insert ON nova_drafts WITH CHECK (false)',
    'ALTER POLICY zova_runtime_access ON nova_drafts TO PUBLIC',
    'CREATE POLICY extra_access ON nova_drafts USING (true)',
])
def test_service_startup_rejects_policy_drift(service_pools,monkeypatch,alteration):
    services,identity,admin,runtime,issuer,role,uids,drafts = service_pools
    with admin.begin() as c:
        c.execute(text(alteration))
    # Prior function/grant checks did not prove that table policies were active.
    with monkeypatch.context() as patch:
        patch.setattr(database_services,'verify_workspace_policies',lambda *a,**k:None)
        database_services.create_services(identity,runtime,issuer)
    if alteration.endswith('DISABLE ROW LEVEL SECURITY') or alteration.endswith('USING (true)'):
        # Adding an unrelated permissive policy alone must NOT bypass the
        # existing restrictive boundary; removing it/loosening it does.
        with runtime.connect() as c:
            count=c.scalar(text('SELECT count(*) FROM nova_drafts'))
            assert count == (0 if alteration.startswith('CREATE POLICY') else 3)
    with pytest.raises(ValueError,match='Workspace'):
        database_services.create_services(identity,runtime,issuer)
    with pytest.raises(ValueError,match='Workspace'):
        database_services.create_services(identity,runtime,issuer)
    # Restoration remains an explicit offline action. Unknown policies are not
    # silently dropped by the migration, so their disposition needs a review.
    if alteration.startswith('CREATE POLICY'):
        with admin.begin() as c:c.execute(text('DROP POLICY extra_access ON nova_drafts'))
    with issuer.connect() as c:issuer_role=c.scalar(text('SELECT session_user'))
    apply_rls(admin,runtime_roles=[services.runtime_role],issuer_roles=[issuer_role],writes_paused=True)
    database_services.create_services(identity,runtime,issuer)
