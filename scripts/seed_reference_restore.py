"""Seed a migrated, synthetic schema so CI restores the new constraints too."""
import os
from pathlib import Path
import sys
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
url=make_url(os.environ['ZOVA_TEST_POSTGRES'])
assert url.host in {'localhost','127.0.0.1'} and url.database=='zova_test_ci'
os.environ['DATABASE_URL']=url.render_as_string(hide_password=False)
os.environ['ZOVA_SCHEMA_MODE']='bootstrap'  # Isolated CI migration identity only.
from nova.db import Base,User,Brand,Draft,SocialConnection,CreatorPreferences
from nova.migrations import run_migrations
from nova.tenant_references import apply_references
from sqlalchemy.orm import Session
admin=create_engine(url)
with admin.begin() as c:c.execute(text('CREATE SCHEMA zova_reference_restore_fixture'))
engine=create_engine(url,connect_args={'options':'-csearch_path=zova_reference_restore_fixture'})
Base.metadata.create_all(engine)
run_migrations(engine)
with Session(engine) as db:
    user=User(email='restore-fixture@example.test',password_hash='synthetic-only-hash',auth_version=8)
    db.add(user);db.flush()
    brand=Brand(user_id=user.id,name='Restore fixture');db.add(brand);db.flush()
    db.add(Draft(user_id=user.id,brand_id=brand.id,brief='Keep canonical references across restore'))
    db.add(SocialConnection(user_id=user.id,brand_id=brand.id,platform='instagram',account_id='synthetic-only',encrypted_access_token='opaque-synthetic-only'))
    other=User(email='other-restore-fixture@example.test',password_hash='other-synthetic-hash')
    db.add(other);db.flush()
    db.add(Draft(user_id=other.id,brief='Other tenant restore fixture'))
    db.add_all([CreatorPreferences(user_id=user.id,writing_tone='Original account'),
                CreatorPreferences(user_id=other.id,writing_tone='Other account')])
    db.commit()
report=apply_references(engine,writes_paused=True)
assert len(report['mapped_table_counts'])==16
from nova.account_references import apply_accounts
assert len(apply_accounts(engine,writes_paused=True)['table_counts'])==13
from nova.rls import apply_rls
from nova.tenant_references import BRAND_TABLES
with engine.begin() as c:
    for role in ('zova_restore_runtime','zova_restore_issuer'):
        c.execute(text(f"CREATE ROLE {role} LOGIN PASSWORD 'synthetic-restore-only' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS"))
        c.execute(text(f'GRANT USAGE ON SCHEMA zova_reference_restore_fixture TO {role}'))
    for name in BRAND_TABLES:
        c.execute(text(f'GRANT SELECT,INSERT,UPDATE,DELETE ON {name} TO zova_restore_runtime'))
    c.execute(text('GRANT SELECT ON zova_workspaces TO zova_restore_runtime'))
apply_rls(engine,runtime_roles=['zova_restore_runtime'],issuer_roles=['zova_restore_issuer'],writes_paused=True)
from nova.account_references import ACCOUNT_TABLES
from nova.account_rls import apply_account_rls
with engine.begin() as c:
    for name in ACCOUNT_TABLES:
        c.execute(text(f'GRANT SELECT ON {name} TO zova_restore_runtime'))
apply_account_rls(engine,runtime_roles=['zova_restore_runtime'],writes_paused=True)
engine.dispose();admin.dispose()
print('Synthetic reference schema ready for full database backup.')
