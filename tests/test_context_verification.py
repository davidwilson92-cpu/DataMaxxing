import pytest
from sqlalchemy import text

from nova import database_services
from nova.rls import context_function_definitions
from test_database_services import service_pools
from test_rls import rls_db
from test_tenant_registry import registry_db


@pytest.mark.parametrize('purpose,before,after', [
    ('issue', 'AND u.active AND m.active', 'AND u.active'),
    ('resolve', 'AND d.backend_pid=pg_backend_pid()', ''),
    ('resolve', 'SECURITY DEFINER', 'SECURITY INVOKER'),
    ('resolve', 'SET search_path=pg_catalog,', 'SET search_path=public,'),
    ('resolve', 'LANGUAGE sql STABLE', 'LANGUAGE sql VOLATILE'),
    ('resolve', 'LANGUAGE sql STABLE', 'LANGUAGE sql STABLE LEAKPROOF'),
    ('resolve', 'LANGUAGE sql STABLE', 'LANGUAGE sql STABLE STRICT'),
    ('resolve', 'DEFAULT NULL', "DEFAULT ARRAY['posts.publish']::text[]"),
])
def test_startup_rejects_context_definition_drift(service_pools, monkeypatch, purpose, before, after):
    services,identity,admin,runtime,issuer,role,uids,drafts = service_pools
    with admin.begin() as c:
        definitions = context_function_definitions(c, [services.runtime_role])
        assert before in definitions[purpose]
        c.execute(text(definitions[purpose].replace(before, after, 1)))
    # Reproduce the gap: the existing identity/grant checks alone accept this
    # altered function with the same name, signature, owner and execution ACL.
    with monkeypatch.context() as patch:
        patch.setattr(database_services, 'verify_context_functions', lambda *a, **k: None)
        database_services.create_services(identity, runtime, issuer)
    with pytest.raises(ValueError, match='function definition'):
        database_services.create_services(identity, runtime, issuer)
    # Verification is read-only; it does not silently repair unsafe definitions.
    with pytest.raises(ValueError, match='function definition'):
        database_services.create_services(identity, runtime, issuer)
    with admin.begin() as c:
        c.execute(text(definitions[purpose]))
    database_services.create_services(identity, runtime, issuer)


def test_context_audience_and_missing_function_are_rejected(service_pools):
    services,identity,admin,runtime,issuer,role,uids,drafts = service_pools
    with admin.begin() as c:
        definition=context_function_definitions(c, [services.runtime_role,role])['issue']
        c.execute(text(definition))
    with pytest.raises(ValueError, match='function definition'):
        database_services.create_services(identity,runtime,issuer)
    with admin.begin() as c:
        schema=c.dialect.identifier_preparer.quote(c.scalar(text('SELECT current_schema()')))
        c.execute(text(f'DROP FUNCTION {schema}.zova_issue_context(text,integer,text,integer,integer,text,text,integer,text,integer)'))
    with pytest.raises(ValueError, match='function definition'):
        database_services.create_services(identity,runtime,issuer)
