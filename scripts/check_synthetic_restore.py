"""CI-only restore check; never receives or prints production credentials/data."""
import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

url=make_url(os.environ['ZOVA_TEST_POSTGRES'])
assert url.host in {'127.0.0.1','localhost'} and url.database=='zova_test_ci'
source=create_engine(url)
restored=create_engine(url.set(database='zova_test_restored'))
with source.connect() as a, restored.connect() as b:
    for table in inspect(source).get_table_names():
        assert table.replace('_','').isalnum()
        assert a.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar()==b.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar(),table
    for table,columns in [('nova_users','id,email,password_hash,auth_version,default_brand_name'),('nova_social_connections','id,user_id,brand_id,encrypted_access_token'),('nova_drafts','id,user_id,brand_id,title,workspace_json,revision'),('nova_media_assets','id,user_id,brand_id,storage_key,analysis_json'),('zova_brands','id,user_id,name'),('zova_brand_voices','id,user_id,brand_id,writing_tone')]:
        assert a.execute(text(f'SELECT {columns} FROM {table} ORDER BY id')).all()==b.execute(text(f'SELECT {columns} FROM {table} ORDER BY id')).all(),table
    assert a.execute(text('SELECT key,user_id,kind,period,amount,state FROM zova_usage_entries ORDER BY key')).all()==b.execute(text('SELECT key,user_id,kind,period,amount,state FROM zova_usage_entries ORDER BY key')).all()
    for table,columns,order in [('zova_pending_connections','code_hash,user_id,brand_id,auth_version,platform,encrypted_payload,expires_at,used','code_hash'),('zova_ai_calls','id,user_id,model,status,input_tokens,output_tokens,estimated_gbp,rate_snapshot','id'),('zova_product_events','key,user_id,kind,created_at','key'),('zova_email_verifications','token_hash,user_id,email,expires_at,used','token_hash'),('zova_mail_deliveries','id,status,created_at','id')]:
        assert a.execute(text(f'SELECT {columns} FROM {table} ORDER BY {order}')).all()==b.execute(text(f'SELECT {columns} FROM {table} ORDER BY {order}')).all(),table
    assert a.execute(text('SELECT id,user_id,brand_id,payload_json,fetched_at FROM zova_performance_snapshots ORDER BY id')).all()==b.execute(text('SELECT id,user_id,brand_id,payload_json,fetched_at FROM zova_performance_snapshots ORDER BY id')).all()
print('Synthetic PostgreSQL restore: all table counts and identity/credential/workspace records match.')
with source.connect() as a, restored.connect() as b:
    query = text('SELECT id,creator_id,text,account,authority_digest,status,result_json FROM zova_legacy_publications ORDER BY id')
    assert a.execute(query).all() == b.execute(query).all(), 'legacy publication ledger'

with source.connect() as a, restored.connect() as b:
    for table, order in [("zova_mfa_settings", "user_id"), ("zova_mfa_challenges", "token_hash")]:
        query = text(f"SELECT * FROM {table} ORDER BY {order}")
        assert a.execute(query).all() == b.execute(query).all(), table

with source.connect() as a, restored.connect() as b:
    for table,order in [('zova_workspaces','id'),('zova_workspace_memberships','workspace_id,user_id')]:
        query = text(f'SELECT * FROM {table} ORDER BY {order}')
        assert a.execute(query).all() == b.execute(query).all(), table

# Verify migrated reference columns and trigger behavior survive pg_dump/pg_restore.
from sqlalchemy.exc import DBAPIError
fixture_options={'options':'-csearch_path=zova_reference_restore_fixture'}
reference_source=create_engine(url,connect_args=fixture_options)
reference_restored=create_engine(url.set(database='zova_test_restored'),connect_args=fixture_options)
with reference_source.connect() as a,reference_restored.connect() as b:
    for table in inspect(reference_source).get_table_names():
        assert table.replace('_','').isalnum()
        columns=inspect(reference_source).get_pk_constraint(table)['constrained_columns']
        order=','.join('"'+name+'"' for name in columns)
        query=text(f'SELECT * FROM "{table}"'+(' ORDER BY '+order if order else ''))
        assert a.execute(query).all()==b.execute(query).all(), 'reference fixture '+table
try:
    with reference_restored.begin() as c:
        c.execute(text('UPDATE nova_drafts SET brand_id=0 WHERE brand_id <> 0'))
except DBAPIError as exc:
    assert getattr(exc.orig,'sqlstate',None)=='23514', 'Expected restored ownership check constraint failure'
else:
    raise AssertionError('Restored ownership guard did not reject reassignment')
reference_source.dispose();reference_restored.dispose()
print('Migrated canonical reference records and ownership guards survive restore.')

# Database roles persist in this isolated CI cluster; pg_dump restores schema
# grants/policies/functions into the second database. No production credentials.
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nova.rls import issue_context,bind_context,verify_context_functions,verify_workspace_policies
from nova.account_references import verify_accounts
from nova.account_rls import verify_account_policies
from nova.tenant_migration import workspace_key
from nova.identity_guards import verify_identities
with reference_restored.connect() as c:
    assert len(verify_accounts(c)['table_counts'])==13
    assert verify_identities(c)['protected_tables']==5
try:
    with reference_restored.begin() as c:
        c.execute(text("UPDATE zova_auth_identities SET subject='forbidden-reassignment'"))
except DBAPIError as exc:
    assert getattr(exc.orig,'sqlstate',None)=='23514'
else:raise AssertionError('Restored identity guard allowed reassignment')
print('Restored identity authority guards reject provider-subject reassignment.')
try:
    with reference_restored.begin() as c:
        c.execute(text('UPDATE zova_brands SET user_id=(SELECT MAX(id) FROM nova_users)'))
except DBAPIError as exc:
    assert getattr(exc.orig,'sqlstate',None)=='23514'
else:raise AssertionError('Restored account ownership guard allowed reassignment')
print('Restored account ownership guards and references verified.')
from nova.tenant_references import BRAND_TABLES
runtime=create_engine(url.set(database='zova_test_restored',username='zova_restore_runtime',password='synthetic-restore-only'),connect_args=fixture_options)
issuer=create_engine(url.set(database='zova_test_restored',username='zova_restore_issuer',password='synthetic-restore-only'),connect_args=fixture_options)
with reference_restored.connect() as a:
    uid,wid=a.execute(text('SELECT owner_user_id,id FROM zova_workspaces WHERE legacy_brand_id>0')).one()
with runtime.connect() as c:
    verify_context_functions(c,runtime_roles=['zova_restore_runtime'])
    verify_workspace_policies(c,runtime_roles=['zova_restore_runtime'])
    verify_account_policies(c,runtime_roles=['zova_restore_runtime'])
    for table in BRAND_TABLES:assert c.scalar(text(f'SELECT count(*) FROM {table}'))==0
    token=issue_context(issuer,c,user_id=uid,workspace_id=wid,auth_version=8,membership_revision=1,capability='posts.read',runtime_role='zova_restore_runtime')
    bind_context(c,token)
    assert c.scalars(text('SELECT workspace_id FROM nova_drafts')).all()==[wid]
    assert c.execute(text("UPDATE nova_drafts SET brief='forbidden'")).rowcount==0
    c.commit()
    assert c.scalar(text('SELECT count(*) FROM nova_drafts'))==0
    assert c.scalar(text('SELECT count(*) FROM nova_creator_preferences'))==0
    token=issue_context(issuer,c,user_id=uid,workspace_id=workspace_key(uid,0),auth_version=8,membership_revision=1,capability='account.read',runtime_role='zova_restore_runtime')
    bind_context(c,token)
    assert c.execute(text('SELECT user_id,writing_tone FROM nova_creator_preferences')).all()==[(uid,'Original account')]
    c.commit()
    assert c.scalar(text('SELECT count(*) FROM nova_creator_preferences'))==0
runtime.dispose();issuer.dispose();reference_restored.dispose()
print('Restored RLS denies unbound reads, isolates tenants and blocks read-context writes.')
print('Restored context definitions and complete workspace policy manifest verified.')
print('Restored account policy manifest and private account isolation verified.')
