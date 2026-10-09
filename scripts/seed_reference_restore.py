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
from nova.db import Base,User,Brand,Draft,SocialConnection
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
    db.commit()
report=apply_references(engine,writes_paused=True)
assert len(report['mapped_table_counts'])==16
engine.dispose();admin.dispose()
print('Synthetic reference schema ready for full database backup.')
