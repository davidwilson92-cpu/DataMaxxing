from datetime import timedelta
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import DBAPIError
from nova import db as models
from nova.identity_guards import FIELDS,CONSUMABLE,VERSION,apply_identities,verify_identities
from nova.tenant_migration import MappingError
from nova.schema_startup import verify_runtime_schema
from test_schema_startup import initialize
from test_tenant_registry import registry_db


@pytest.fixture
def identity_db(registry_db):
    engine,initial=registry_db
    initialize(engine,initial)
    with Session(engine) as db:
        user=models.User(email='identity@example.test',password_hash='synthetic-preserved',auth_version=4)
        db.add(user);db.flush()
        for i in (1,2):
            db.add(models.Creator(id=i,name='Synthetic',x_username=f'identity-{i}',api_key_hash=f'identity-key-{i}',
                encrypted_x_api_key='opaque',encrypted_x_api_secret='opaque',
                encrypted_x_access_token='opaque',encrypted_x_access_token_secret='opaque'))
        db.flush()
        expiry=models.utcnow()+timedelta(minutes=10)
        db.add_all([
            models.AuthIdentity(id=1,user_id=user.id,provider='apple',subject='original-subject'),
            models.UserCreatorLink(id=1,user_id=user.id,creator_id=1),
            models.RecoveryToken(token_hash='original-token',user_id=user.id,auth_version=4,expires_at=expiry),
            models.EmailVerification(token_hash='original-token',user_id=user.id,email=user.email,expires_at=expiry),
            models.MfaChallenge(token_hash='original-token',user_id=user.id,auth_version=4,destination='/studio',expires_at=expiry),
            models.AuthState(id=1,provider='apple',state_hash='original-state',nonce_hash='original-nonce',intent='login'),
            models.OAuthState(id=1,user_id=user.id,platform='x',state_hash='original-state',encrypted_code_verifier='synthetic-verifier'),
            models.PendingConnection(code_hash='original-code',user_id=user.id,auth_version=4,platform='instagram',encrypted_payload='synthetic-pending-credentials',expires_at=expiry),
        ]);db.commit()
    # Reproduce the pre-migration state only in this disposable schema.
    with engine.begin() as c:
        for name in FIELDS:
            if c.dialect.name=='postgresql':c.execute(text(f'DROP TRIGGER zova_identity_guard ON {name}'))
            else:c.execute(text(f'DROP TRIGGER {name}_identity_guard'))
        c.execute(text('DELETE FROM zova_schema_migrations WHERE version=:version'),{'version':VERSION})
    return engine


@pytest.mark.parametrize('table',sorted(FIELDS))
def test_existing_identity_authority_cannot_be_rewritten(identity_db,table):
    values={'id':50,'provider':'different','subject':'other-subject','creator_id':2,
            'token_hash':'other-token','auth_version':99,'expires_at':models.utcnow()+timedelta(days=2),
            'email':'other@example.test','destination':'/different','platform':'tiktok',
            'state_hash':'other-state','nonce_hash':'other-nonce','intent':'signup',
            'created_at':models.utcnow()+timedelta(days=1),'encrypted_code_verifier':'other-verifier','code_hash':'other-code'}
    fields=set(FIELDS[table])-{'user_id','brand_id','workspace_id'}  # Separate ownership guards already apply.
    with identity_db.connect() as c:
        before=c.execute(text(f'SELECT * FROM {table}')).all()
        for field in fields:
            savepoint=c.begin_nested()
            try:
                c.execute(text(f'UPDATE {table} SET {field}=:value'),{'value':values[field]})
                assert c.execute(text(f'SELECT * FROM {table}')).all()!=before
            finally:savepoint.rollback()
    apply_identities(identity_db,writes_paused=True)
    for field in fields:
        with pytest.raises(DBAPIError):
            with identity_db.begin() as c:c.execute(text(f'UPDATE {table} SET {field}=:value'),{'value':values[field]})
    with identity_db.connect() as c:assert c.execute(text(f'SELECT * FROM {table}')).all()==before


@pytest.mark.parametrize('table',sorted(CONSUMABLE))
def test_consumption_is_one_way_and_cleanup_remains_possible(identity_db,table):
    with identity_db.begin() as c:
        c.execute(text(f'UPDATE {table} SET used=true'))
        c.execute(text(f'UPDATE {table} SET used=false'))
    apply_identities(identity_db,writes_paused=True)
    with identity_db.begin() as c:
        assert c.execute(text(f'UPDATE {table} SET used=true WHERE used=false')).rowcount==1
        assert c.execute(text(f'UPDATE {table} SET used=true WHERE used=false')).rowcount==0
    with pytest.raises(DBAPIError):
        with identity_db.begin() as c:c.execute(text(f'UPDATE {table} SET used=false'))
    with identity_db.begin() as c:assert c.execute(text(f'DELETE FROM {table} WHERE used=true')).rowcount==1


def test_identity_migration_repeat_preserves_records_and_runtime_requires_guards(identity_db):
    with identity_db.connect() as c:
        before={name:c.execute(text(f'SELECT * FROM {name}')).all() for name in FIELDS}
        with pytest.raises(RuntimeError):verify_runtime_schema(c,models.Base.metadata)
    with pytest.raises(MappingError,match='Pause'):apply_identities(identity_db)
    apply_identities(identity_db,writes_paused=True);apply_identities(identity_db,writes_paused=True)
    with identity_db.connect() as c:
        assert before=={name:c.execute(text(f'SELECT * FROM {name}')).all() for name in FIELDS}
        verify_runtime_schema(c,models.Base.metadata)
        assert c.execute(text('SELECT password_hash,auth_version FROM nova_users')).one()==('synthetic-preserved',4)


def test_identity_migration_interruption_rolls_back(identity_db,monkeypatch):
    from nova import identity_guards
    def fail(c):raise MappingError('Synthetic interruption')
    monkeypatch.setattr(identity_guards,'verify_identities',fail)
    with pytest.raises(MappingError,match='interruption'):apply_identities(identity_db,writes_paused=True)
    with identity_db.begin() as c:
        assert not c.scalar(text('SELECT count(*) FROM zova_schema_migrations WHERE version=:version'),{'version':VERSION})
        c.execute(text("UPDATE zova_auth_identities SET subject='still-original-schema'"))


def test_identity_verifier_rejects_same_name_weakened_guard(identity_db):
    apply_identities(identity_db,writes_paused=True)
    with identity_db.begin() as c:
        if c.dialect.name=='postgresql':
            c.execute(text('ALTER FUNCTION zova_guard_identity() SECURITY DEFINER'))
        else:
            c.execute(text('DROP TRIGGER zova_auth_identities_identity_guard'))
            c.execute(text('CREATE TRIGGER zova_auth_identities_identity_guard BEFORE UPDATE ON zova_auth_identities BEGIN SELECT 1; END'))
    with identity_db.connect() as c,pytest.raises(MappingError):verify_identities(c)
    with identity_db.connect() as c,pytest.raises(RuntimeError,match='identity'):verify_runtime_schema(c,models.Base.metadata)


def test_pending_credentials_can_only_be_preserved_or_erased(identity_db):
    with identity_db.begin() as c:
        c.execute(text("UPDATE zova_pending_connections SET encrypted_payload='replacement'"))
        c.execute(text("UPDATE zova_pending_connections SET encrypted_payload='synthetic-pending-credentials'"))
    apply_identities(identity_db,writes_paused=True)
    with pytest.raises(DBAPIError):
        with identity_db.begin() as c:c.execute(text("UPDATE zova_pending_connections SET encrypted_payload='replacement'"))
    with identity_db.begin() as c:c.execute(text("UPDATE zova_pending_connections SET encrypted_payload=''"))
    with pytest.raises(DBAPIError):
        with identity_db.begin() as c:c.execute(text("UPDATE zova_pending_connections SET encrypted_payload='synthetic-pending-credentials'"))
    with identity_db.connect() as c:assert c.scalar(text('SELECT encrypted_payload FROM zova_pending_connections'))==''


def test_nullable_pkce_verifier_cannot_be_added_after_state_creation(identity_db):
    with identity_db.begin() as c:c.execute(text('UPDATE nova_oauth_states SET encrypted_code_verifier=NULL'))
    apply_identities(identity_db,writes_paused=True)
    with pytest.raises(DBAPIError):
        with identity_db.begin() as c:c.execute(text("UPDATE nova_oauth_states SET encrypted_code_verifier='late-verifier'"))
    with identity_db.begin() as c:assert c.execute(text('UPDATE nova_oauth_states SET used=true')).rowcount==1
