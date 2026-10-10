import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from nova import db as models
from nova.database_services import create_services, verify_pool_grants
from nova.service_permissions import DRAFT_TABLE_GRANTS, DRAFT_COLUMN_GRANTS
from test_database_services import service_pools
from test_rls import rls_db, context
from test_tenant_registry import registry_db


def test_broad_row_policy_fixture_is_not_a_least_privilege_draft_service(rls_db):
    admin,runtime,issuer,roles,uids,drafts=rls_db
    with runtime.connect() as c:
        context(issuer,c,roles[0],uids[0],'posts.publish')
        assert c.scalar(text('SELECT encrypted_access_token FROM nova_social_connections'))=='synthetic'
        assert c.execute(text("UPDATE zova_publish_reviews SET payload_json='tampered'")).rowcount==1
        with pytest.raises(ValueError,match='manifest'):
            verify_pool_grants(c,models.Base.metadata,DRAFT_TABLE_GRANTS,DRAFT_COLUMN_GRANTS)
        c.rollback()  # Reproduction only; no changed fixture approval survives.


def test_draft_role_cannot_read_secrets_or_mutate_delivery_authority(service_pools):
    services,identity,admin,runtime,issuer,role,uids,drafts=service_pools
    attacks=[
        'SELECT encrypted_access_token FROM nova_social_connections',
        'SELECT storage_key FROM nova_media_assets',
        'SELECT payload_json FROM zova_publish_reviews',
        "UPDATE zova_publish_reviews SET payload_json='tampered'",
        "UPDATE nova_drafts SET status='published'",
        'UPDATE nova_drafts SET id=id',
        'UPDATE nova_drafts SET user_id=user_id',
        'UPDATE zova_series_occurrences SET due_at=due_at',
        "UPDATE zova_strategy_actions SET payload_json='tampered'",
        "UPDATE nova_scheduled_posts SET status='published'",
        'DELETE FROM zova_publications',
        'SELECT password_hash FROM nova_users',
        "SELECT setval('nova_drafts_id_seq',1,false)",
        "SELECT nextval('nova_users_id_seq')",
    ]
    for attack in attacks:
        with pytest.raises(DBAPIError) as caught:
            with runtime.begin() as c:
                # Even a valid owner publishing capability cannot turn the
                # draft connection into a publishing or credential service.
                context(issuer,c,services.runtime_role,uids[0],'posts.publish')
                c.execute(text(attack))
        assert caught.value.orig.sqlstate=='42501',attack
    with pytest.raises(DBAPIError) as caught:
        with issuer.connect() as c:c.execute(text('SELECT * FROM nova_users'))
    assert caught.value.orig.sqlstate=='42501'


@pytest.mark.parametrize('target,statement',[
    ('runtime','GRANT SELECT (encrypted_access_token) ON nova_social_connections TO {role}'),
    ('runtime','GRANT SELECT (storage_key) ON nova_media_assets TO {role}'),
    ('runtime','GRANT UPDATE ON nova_drafts TO {role}'),
    ('runtime','REVOKE UPDATE (brief) ON nova_drafts FROM {role}'),
    ('runtime','GRANT UPDATE ON SEQUENCE nova_drafts_id_seq TO {role}'),
    ('issuer','GRANT SELECT (auth_version) ON nova_users TO {role}'),
])
def test_service_startup_rejects_missing_or_excess_content_and_issuer_grants(service_pools,target,statement):
    services,identity,admin,runtime,issuer,role,uids,drafts=service_pools
    engine={'runtime':runtime,'issuer':issuer}[target]
    with engine.connect() as c:target_role=c.scalar(text('SELECT session_user'))
    with admin.begin() as c:
        c.execute(text(statement.format(role=c.dialect.identifier_preparer.quote(target_role))))
    with pytest.raises(ValueError,match='manifest'):
        create_services(identity,runtime,issuer)
