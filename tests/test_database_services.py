import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from nova import db as models
from nova.database_services import create_services, IDENTITY_READ_TABLES, DRAFT_ROUTES
from nova.service_permissions import DRAFT_TABLE_GRANTS, DRAFT_COLUMN_GRANTS
from test_rls import rls_db
from test_tenant_registry import registry_db


@pytest.fixture
def service_pools(rls_db):
    admin,runtime,issuer,roles,uids,drafts=rls_db
    role='zova_identity_'+secrets.token_hex(8)
    password=secrets.token_hex(24)
    identity=None
    with admin.begin() as c:
        schema=c.scalar(text('SELECT current_schema()'))
        c.execute(text(f"CREATE ROLE {role} LOGIN PASSWORD '{password}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS"))
    try:
        with admin.begin() as c:
            # The RLS foundation fixture is deliberately broad for policy
            # attacks; actual draft service tests must use its exact grants.
            c.execute(text(f'REVOKE ALL ON ALL TABLES IN SCHEMA {schema} FROM {roles[0]}'))
            c.execute(text(f'REVOKE ALL ON ALL SEQUENCES IN SCHEMA {schema} FROM {roles[0]}'))
            for table,operations in DRAFT_TABLE_GRANTS.items():
                c.execute(text(f'GRANT {",".join(sorted(operations))} ON {schema}.{table} TO {roles[0]}'))
            for (table,operation),columns in DRAFT_COLUMN_GRANTS.items():
                c.execute(text(f'GRANT {operation} ({",".join(sorted(columns))}) ON {schema}.{table} TO {roles[0]}'))
            c.execute(text(f'GRANT USAGE ON SEQUENCE {schema}.nova_drafts_id_seq TO {roles[0]}'))
            c.execute(text(f'GRANT USAGE ON SCHEMA {schema} TO {role}'))
            for name in IDENTITY_READ_TABLES:
                c.execute(text(f'GRANT SELECT ON {schema}.{name} TO {role}'))
            c.execute(text(f'GRANT SELECT,INSERT,UPDATE,DELETE ON {schema}.zova_request_limits TO {role}'))
        identity=create_engine(admin.url.set(username=role,password=password).update_query_dict(
            {'options':f'-csearch_path={schema}'}),hide_parameters=True,pool_size=2,max_overflow=0)
        services=create_services(identity,runtime,issuer)
        yield services,identity,admin,runtime,issuer,role,uids,drafts
    finally:
        if identity:identity.dispose()
        with admin.begin() as c:
            c.execute(text(f'DROP OWNED BY {role}'))
            c.execute(text(f'DROP ROLE {role}'))


def test_service_configuration_requires_distinct_engines_and_explicit_route_capabilities():
    with pytest.raises(ValueError,match='Three separate'):
        create_services(None,None,None)
    assert DRAFT_ROUTES[('/api/drafts/{draft_id}','DELETE')]=='posts.delete'
    assert ('/api/publish','POST') not in DRAFT_ROUTES


def test_identity_pool_cannot_read_content_or_change_account_authority(service_pools):
    services,identity,admin,runtime,issuer,role,uids,drafts=service_pools
    for sql in ('SELECT * FROM nova_drafts','UPDATE nova_users SET auth_version=0',
                'UPDATE zova_workspace_memberships SET role=\'owner\'',
                'SELECT * FROM zova_db_contexts'):
        with pytest.raises(DBAPIError) as caught:
            with identity.begin() as c:c.execute(text(sql))
        assert caught.value.orig.sqlstate=='42501'
    # Even a single unauthorized column grant must fail service startup checks.
    with admin.begin() as c:
        schema=c.scalar(text('SELECT current_schema()'))
        c.execute(text(f'GRANT SELECT (brief) ON {schema}.nova_drafts TO {role}'))
    with pytest.raises(ValueError,match='manifest'):
        create_services(identity,runtime,issuer)


def test_identity_pool_cannot_inherit_context_issuer_privilege(service_pools):
    services,identity,admin,runtime,issuer,role,uids,drafts=service_pools
    with admin.begin() as c:
        schema=c.scalar(text('SELECT current_schema()'))
        c.execute(text(f'GRANT EXECUTE ON FUNCTION {schema}.zova_issue_context(text,integer,text,integer,integer,text,text,integer,text,integer) TO {role}'))
    with pytest.raises(ValueError,match='Context functions'):
        create_services(identity,runtime,issuer)


@pytest.mark.parametrize('second_brand',[False,True])
def test_normal_draft_dependency_uses_restricted_service_pools(service_pools,monkeypatch,second_brand):
    from nova.app import app
    from nova import readiness, security, request_security
    services,identity,admin,runtime,issuer,role,uids,drafts=service_pools
    assert models.get_db not in app.dependency_overrides
    with Session(admin) as db:
        bid=db.scalar(select(models.Brand.id).where(models.Brand.user_id==uids[0])) if second_brand else 0
        foreign=models.Brand(user_id=uids[1],name='Another customer brand')
        db.add(foreign);db.commit();foreign_id=foreign.id
    previous=getattr(app.state,'database_services',None)
    app.state.database_services=services
    monkeypatch.setenv('PRODUCT_METRICS_ENABLED','true')
    fallback_attempts=[]
    def forbidden_fallback(*args,**kwargs):
        fallback_attempts.append(True)
        raise AssertionError('Configured requests must not use the shared credential pool')
    for module in (models,security,request_security,readiness):
        monkeypatch.setattr(module,'SessionLocal',forbidden_fallback)
    try:
        client=TestClient(app)
        client.cookies.set('nova_session',security.make_user_session(uids[0],session_factory=services.identity_sessions))
        client.headers.update({'origin':'http://testserver','X-Zova-Brand':str(bid)})
        response=client.post('/api/drafts')
        assert response.status_code==200,response.text
        did=response.json()['id']
        with Session(admin) as db:
            asset=models.MediaAsset(user_id=uids[0],brand_id=bid,filename='safe.jpg',mime_type='image/jpeg',storage_key='private-location')
            foreign_asset=models.MediaAsset(user_id=uids[1],filename='foreign.jpg',mime_type='image/jpeg',storage_key='other-private-location')
            series=models.ContentSeries(user_id=uids[0],brand_id=bid,request_key='draft-service',spec_json='{"timezone":"Europe/London"}')
            db.add_all([asset,foreign_asset,series]);db.flush()
            asset_id,foreign_asset_id=asset.id,foreign_asset.id
            action=models.StrategyAction(user_id=uids[0],brand_id=bid,action_key='draft-service',strategy_revision=0,payload_json='{}',draft_id=did)
            occurrence=models.SeriesOccurrence(user_id=uids[0],brand_id=bid,series_id=series.id,position=0,due_at=models.utcnow(),draft_id=did)
            review=models.PublishReview(user_id=uids[0],brand_id=bid,code='draft-service-review',draft_id=did,revision=0,payload_json='{}',expires_at=models.utcnow())
            db.add_all([action,occurrence,review]);db.commit()
            action_id,occurrence_id=action.id,occurrence.id
        refused=client.patch(f'/api/drafts/{did}',json={'brief':'Wrong attachment','revision':0,'workspace':{'media_asset_ids':[foreign_asset_id]}})
        assert refused.status_code==404,refused.text
        saved=client.patch(f'/api/drafts/{did}',json={'brief':'Real dependency save','revision':0,'workspace':{'media_asset_ids':[asset_id],'instagram_format':'story'}})
        assert saved.status_code==200,saved.text
        loaded=client.get(f'/api/drafts/{did}').json()
        assert loaded['brief']=='Real dependency save'
        assert loaded['workspace']['media_asset_ids']==[asset_id]
        assert loaded['workspace']['instagram_format']=='story'
        assert loaded['planned']['timezone']=='Europe/London'
        assert client.get(f'/api/drafts/{drafts[1]}').status_code==404
        assert client.get('/api/drafts',headers={'X-Zova-Brand':'invalid'}).status_code==400
        assert client.get('/api/drafts',headers={'X-Zova-Brand':'999999'}).status_code==404
        assert client.get('/api/drafts',headers={'X-Zova-Brand':str(foreign_id)}).status_code==404
        client.headers.pop('X-Zova-Brand')
        client.cookies.set('zova_brand',str(foreign_id))
        default=client.get('/api/drafts')
        assert default.status_code==200
        assert drafts[0] in {row['id'] for row in default.json()}
        client.headers['X-Zova-Brand']=str(bid)
        # The rollout cannot fall back to broad credentials for an unmapped route.
        assert client.get('/account').status_code==503
        assert client.post('/logout').status_code==503
        assert client.get('/').status_code==503
        assert client.get('/health').status_code==200
        with Session(admin) as db:
            stored=db.get(models.Draft,did)
            assert stored.brand_id==bid and stored.user_id==uids[0]
            assert db.scalar(select(models.RequestLimit.count)) > 0
        assert client.delete(f'/api/drafts/{did}').status_code==204
        assert client.get(f'/api/drafts/{did}').status_code==404
        with Session(admin) as db:
            assert db.get(models.PublishReview,'draft-service-review') is None
            assert db.get(models.StrategyAction,action_id).draft_id is None
            assert db.get(models.StrategyAction,action_id).status=='dismissed'
            assert db.get(models.SeriesOccurrence,occurrence_id).draft_id is None
            assert db.get(models.SeriesOccurrence,occurrence_id).status=='cancelled'
            assert db.get(models.MediaAsset,asset_id).storage_key=='private-location'
        with admin.begin() as c:
            c.execute(text('UPDATE nova_users SET auth_version=auth_version+1 WHERE id=:uid'),{'uid':uids[0]})
        assert client.get('/api/drafts').status_code==401
        assert fallback_attempts==[]
    finally:
        if previous is None:del app.state.database_services
        else:app.state.database_services=previous
