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
    for table,columns in [('nova_users','id,email,password_hash,auth_version'),('nova_social_connections','id,user_id,encrypted_access_token'),('nova_drafts','id,user_id,workspace_json,revision')]:
        assert a.execute(text(f'SELECT {columns} FROM {table} ORDER BY id')).all()==b.execute(text(f'SELECT {columns} FROM {table} ORDER BY id')).all(),table
print('Synthetic PostgreSQL restore: all table counts and identity/credential/workspace records match.')
