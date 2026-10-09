import secrets
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import DBAPIError
from nova import db as models
from nova.rls import apply_rls, issue_context, bind_context, WRITE_CAPABILITIES
from nova.tenant_references import BRAND_TABLES
from nova.tenant_migration import workspace_key
from test_tenant_registry import registry_db
from test_schema_startup import initialize


def seed_all(db, uid):
    draft=models.Draft(user_id=uid,brief='Synthetic private draft')
    conn=models.SocialConnection(user_id=uid,platform='instagram',account_id=str(uid),encrypted_access_token='synthetic')
    series=models.ContentSeries(user_id=uid,request_key='synthetic',spec_json='{}')
    db.add_all([draft,conn,series]);db.flush()
    code='review-'+str(uid)
    db.add_all([
        models.BrandVoice(user_id=uid),
        models.OAuthState(user_id=uid,platform='instagram',state_hash='state-'+str(uid)),
        models.PublishReview(user_id=uid,code=code,draft_id=draft.id,revision=0,payload_json='{}',expires_at=models.utcnow()),
        models.Publication(user_id=uid,draft_id=draft.id,platform='instagram',connection_id=conn.id,review_code=code),
        models.MediaAsset(user_id=uid,filename='synthetic.jpg',mime_type='image/jpeg',storage_key='synthetic'),
        models.ScheduledPost(user_id=uid,platform='instagram',content_json='{}',scheduled_at=models.utcnow()),
        models.Activity(user_id=uid,platform='instagram',status='draft'),
        models.PendingConnection(user_id=uid,code_hash='pending-'+str(uid),auth_version=0,platform='instagram',encrypted_payload='synthetic',expires_at=models.utcnow()),
        models.PerformanceSnapshot(user_id=uid),models.Strategy(user_id=uid),
        models.StrategyAction(user_id=uid,action_key='synthetic',strategy_revision=0,payload_json='{}'),
        models.SeriesOccurrence(user_id=uid,series_id=series.id,position=0,due_at=models.utcnow()),
        models.SeriesApproval(user_id=uid,series_id=series.id,revision=0,token='approval-'+str(uid),payload_json='{}',expires_at=models.utcnow()),
    ])
    return draft.id


@pytest.fixture
def rls_db(registry_db):
    admin, initial=registry_db
    if admin.dialect.name!='postgresql':pytest.skip('Requires real PostgreSQL row-level policies')
    initialize(admin,initial)
    with Session(admin) as db:
        users=[models.User(email=f'rls-{i}@example.test',password_hash='synthetic') for i in range(2)]
        db.add_all(users);db.flush();uids=[u.id for u in users]
        drafts=[seed_all(db,uid) for uid in uids]
        secondary=models.Brand(user_id=uids[0],name='Same owner, separate workspace')
        db.add(secondary);db.flush()
        db.add(models.Draft(user_id=uids[0],brand_id=secondary.id,brief='Other brand private draft'))
        db.commit()
    roles=['zova_rls_'+secrets.token_hex(8) for _ in range(2)]
    passwords=[secrets.token_hex(24) for _ in roles]
    engines=[]
    with admin.begin() as c:
        schema=c.scalar(text('SELECT current_schema()'))
        for role,password in zip(roles,passwords):
            c.execute(text(f"CREATE ROLE {role} LOGIN PASSWORD '{password}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS"))
            c.execute(text(f'GRANT USAGE ON SCHEMA {schema} TO {role}'))
    try:
        with admin.begin() as c:
            for name in BRAND_TABLES:c.execute(text(f'GRANT SELECT,INSERT,UPDATE,DELETE ON {schema}.{name} TO {roles[0]}'))
            c.execute(text(f'GRANT SELECT ON {schema}.zova_workspaces TO {roles[0]}'))
            c.execute(text(f'GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA {schema} TO {roles[0]}'))
        report=apply_rls(admin,runtime_roles=[roles[0]],issuer_roles=[roles[1]],writes_paused=True)
        assert report['protected_tables']==16 and not report['runtime_integrated']
        for role,password in zip(roles,passwords):
            url=admin.url.set(username=role,password=password).update_query_dict({'options':f'-csearch_path={schema}'})
            engines.append(create_engine(url,pool_size=2,max_overflow=0))
        yield admin,engines[0],engines[1],roles,uids,drafts
    finally:
        for engine in engines:engine.dispose()
        with admin.begin() as c:
            for name in BRAND_TABLES:c.execute(text(f'DROP POLICY IF EXISTS zova_runtime_access ON {schema}.{name}'))
            for role in roles:
                c.execute(text(f'DROP OWNED BY {role}'))
                c.execute(text(f'DROP ROLE {role}'))


def context(issuer,c,role,uid,cap='posts.read',**changes):
    args=dict(user_id=uid,workspace_id=workspace_key(uid),auth_version=0,membership_revision=1,capability=cap,runtime_role=role)
    args.update(changes)
    token=issue_context(issuer,c,**args);bind_context(c,token)
    return token


def test_policy_manifest_covers_every_brand_owned_table():
    assert set(WRITE_CAPABILITIES)==BRAND_TABLES


def test_context_and_migration_inputs_fail_before_database_access():
    with pytest.raises(ValueError,match='Pause'):
        apply_rls(None,runtime_roles=['runtime'],issuer_roles=['issuer'])
    with pytest.raises(ValueError,match='Separate'):
        apply_rls(None,runtime_roles=['same'],issuer_roles=['same'],writes_paused=True)
    for token in ('','forged',None,'a'*10000):
        with pytest.raises(ValueError,match='Invalid'):bind_context(None,token)


def test_context_binding_failure_does_not_disclose_bearer_in_traceback():
    import traceback
    from types import SimpleNamespace
    from sqlalchemy.exc import SQLAlchemyError
    marker='synthetic-private-context-marker'
    def fail(*args,**kwargs):raise SQLAlchemyError(marker)
    connection=SimpleNamespace(dialect=SimpleNamespace(name='postgresql'),execute=fail)
    try:bind_context(connection,secrets.token_urlsafe(32))
    except RuntimeError as error:
        assert str(error)=='Database workspace context could not be bound'
        assert marker not in traceback.format_exc()
    else:pytest.fail('Expected a sanitized binding failure')


def test_direct_reads_default_deny_and_isolate_all_sixteen_tables(rls_db):
    admin,runtime,issuer,roles,uids,_=rls_db
    with runtime.connect() as c:
        for name in BRAND_TABLES:assert c.scalar(text(f'SELECT count(*) FROM {name}'))==0
        c.execute(text("SELECT set_config('zova.workspace_id',:wid,true)"),{'wid':workspace_key(uids[1])})
        bind_context(c,secrets.token_urlsafe(32))
        assert c.scalar(text('SELECT count(*) FROM nova_drafts'))==0
        context(issuer,c,roles[0],uids[0])
        for name in BRAND_TABLES:
            assert c.scalars(text(f'SELECT workspace_id FROM {name}')).all()==[workspace_key(uids[0])]
    # An unrelated permissive policy must not defeat the restrictive boundary.
    with admin.begin() as c:c.execute(text('CREATE POLICY accidental_allow_all ON nova_drafts USING (true)'))
    with runtime.connect() as c:
        context(issuer,c,roles[0],uids[0])
        assert c.scalar(text('SELECT count(*) FROM nova_drafts'))==1


def test_read_context_cannot_write_and_write_context_cannot_cross_workspace(rls_db):
    _,runtime,issuer,roles,uids,drafts=rls_db
    with runtime.begin() as c:
        context(issuer,c,roles[0],uids[0])
        assert c.execute(text("UPDATE nova_drafts SET brief='forbidden'")).rowcount==0
        assert c.execute(text('DELETE FROM nova_activity')).rowcount==0
    with runtime.begin() as c:
        context(issuer,c,roles[0],uids[0],'posts.edit')
        assert c.execute(text("UPDATE nova_drafts SET brief='allowed'")).rowcount==1
        assert c.execute(text("UPDATE nova_drafts SET brief='foreign' WHERE id=:id"),{'id':drafts[1]}).rowcount==0
    with pytest.raises(DBAPIError) as caught:
        with runtime.begin() as c:
            context(issuer,c,roles[0],uids[0],'posts.create')
            c.execute(models.Draft.__table__.insert().values(user_id=uids[1],brief='Cross workspace'))
    assert caught.value.orig.sqlstate=='42501'
    with runtime.begin() as c:
        context(issuer,c,roles[0],uids[0],'posts.create')
        c.execute(models.Draft.__table__.insert().values(user_id=uids[0],brief='Allowed new draft'))
        assert c.scalar(text('SELECT count(*) FROM nova_drafts'))==2


@pytest.mark.parametrize('change',["active=false","role='viewer'","revision=revision+1"])
def test_membership_revocation_is_seen_without_reusing_cached_authority(rls_db,change):
    admin,runtime,issuer,roles,uids,_=rls_db
    with runtime.connect() as c:
        context(issuer,c,roles[0],uids[0],'posts.edit')
        assert c.scalar(text('SELECT count(*) FROM nova_drafts'))==1
        with admin.begin() as a:a.execute(text(f'UPDATE zova_workspace_memberships SET {change} WHERE user_id=:uid'),{'uid':uids[0]})
        assert c.scalar(text('SELECT count(*) FROM nova_drafts'))==0


def test_expiry_session_revocation_and_transaction_replay_fail_closed(rls_db):
    admin,runtime,issuer,roles,uids,_=rls_db
    with runtime.connect() as c:
        token=context(issuer,c,roles[0],uids[0])
        with runtime.connect() as other:
            bind_context(other,token)
            assert other.scalar(text('SELECT count(*) FROM nova_drafts'))==0
        # Even a malicious session-level setting cannot carry authority into the next transaction.
        c.execute(text("SELECT set_config('zova.workspace_context',:token,false)"),{'token':token})
        c.commit()
        assert c.scalar(text('SELECT count(*) FROM nova_drafts'))==0
        token=context(issuer,c,roles[0],uids[0])
        c.rollback()
        bind_context(c,token)
        assert c.scalar(text('SELECT count(*) FROM nova_drafts'))==0
        context(issuer,c,roles[0],uids[0])
        with admin.begin() as a:a.execute(text('UPDATE zova_db_contexts SET expires_at=CURRENT_TIMESTAMP - interval \'1 second\''))
        assert c.scalar(text('SELECT count(*) FROM nova_drafts'))==0
        context(issuer,c,roles[0],uids[0])
        with admin.begin() as a:a.execute(text('UPDATE nova_users SET auth_version=auth_version+1 WHERE id=:uid'),{'uid':uids[0]})
        assert c.scalar(text('SELECT count(*) FROM nova_drafts'))==0


def test_runtime_cannot_mint_enumerate_or_edit_contexts_or_authority(rls_db):
    _,runtime,issuer,roles,uids,_=rls_db
    attacks=['SELECT * FROM zova_db_contexts','DELETE FROM zova_db_contexts',
             "UPDATE zova_workspace_memberships SET role='owner'",'UPDATE nova_users SET auth_version=0']
    for attack in attacks:
        with pytest.raises(DBAPIError) as caught:
            with runtime.begin() as c:c.execute(text(attack))
        assert caught.value.orig.sqlstate=='42501'
    with pytest.raises(DBAPIError) as caught:
        with runtime.connect() as c:context(runtime,c,roles[0],uids[0])
    assert caught.value.orig.sqlstate=='42501'
    with pytest.raises(DBAPIError) as caught:
        with issuer.connect() as c:c.execute(text('SELECT * FROM nova_drafts'))
    assert caught.value.orig.sqlstate=='42501'


@pytest.mark.parametrize('override',[{'workspace_id':'forged'},{'auth_version':99},{'membership_revision':99},{'capability':'unknown'},{'runtime_role':'postgres'}])
def test_issuer_rejects_stale_or_wrong_authority(rls_db,override):
    _,runtime,issuer,roles,uids,_=rls_db
    with pytest.raises(DBAPIError) as caught:
        with runtime.connect() as c:context(issuer,c,roles[0],uids[0],**override)
    assert caught.value.orig.sqlstate=='42501'


def test_reapply_preserves_boundary_and_rejects_truncate_privilege(rls_db):
    admin,runtime,issuer,roles,uids,_=rls_db
    apply_rls(admin,runtime_roles=[roles[0]],issuer_roles=[roles[1]],writes_paused=True)
    with runtime.connect() as c:
        context(issuer,c,roles[0],uids[0])
        assert c.scalar(text('SELECT count(*) FROM nova_drafts'))==1
    with admin.begin() as c:c.execute(text(f'GRANT TRUNCATE ON nova_drafts TO {roles[0]}'))
    with pytest.raises(ValueError,match='destructive'):
        apply_rls(admin,runtime_roles=[roles[0]],issuer_roles=[roles[1]],writes_paused=True)
    with admin.begin() as c:c.execute(text(f'REVOKE TRUNCATE ON nova_drafts FROM {roles[0]}'))
