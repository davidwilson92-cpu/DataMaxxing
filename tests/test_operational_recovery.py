import sqlite3
from datetime import timedelta
from fastapi import HTTPException
import pytest
from test_account_integrity import account
from nova.db import SessionLocal, User
from nova.security import encrypt, decrypt
from nova.publishing_workflow import schedule_time


def test_operations_endpoint_requires_secret(monkeypatch):
    client, *_=account()
    monkeypatch.setenv('SCHEDULER_SECRET','synthetic-ops')
    assert client.get('/internal/status').status_code==401
    result=client.get('/internal/status',headers={'Authorization':'Bearer synthetic-ops'})
    assert result.status_code==200
    assert result.json()['database']=='reachable'


def test_dst_requires_explicit_offset():
    with pytest.raises(HTTPException):schedule_time('2027-10-31T01:30','Europe/London')
    with pytest.raises(HTTPException):schedule_time('2027-03-28T01:30','Europe/London')
    assert schedule_time('2027-10-31T01:30:00+00:00','Europe/London').hour==1


def test_synthetic_backup_restores_password_and_encrypted_record(tmp_path):
    from nova.db import engine, SocialConnection
    if engine.dialect.name != "sqlite": pytest.skip("SQLite backup; PostgreSQL dump/restore runs separately in CI")
    from nova.security import verify_password
    client,uid,_,_=account()
    with SessionLocal() as db:
        db.add(SocialConnection(user_id=uid,platform='x',account_id='backup-mock',encrypted_access_token=encrypt('mock-token')))
        db.commit()
    import hashlib, io
    from PIL import Image
    from nova.storage import get_bytes
    from nova.db import MediaAsset
    png=io.BytesIO();Image.new('RGB',(4,4)).save(png,format='PNG')
    uploaded=client.post('/api/media',files={'files':('restore.png',png.getvalue(),'image/png')}).json()['assets'][0]
    with SessionLocal() as db:
        media=db.get(MediaAsset,uploaded['id']);raw=get_bytes(media.storage_key)
    restored_upload=tmp_path/'restored-upload.png';restored_upload.write_bytes(raw)
    assert hashlib.sha256(restored_upload.read_bytes()).digest()==hashlib.sha256(png.getvalue()).digest()
    source=sqlite3.connect(engine.url.database)
    target=sqlite3.connect(tmp_path/'restored.db')
    source.backup(target)
    assert target.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    password=target.execute('SELECT password_hash FROM nova_users WHERE id=?',(uid,)).fetchone()[0]
    token=target.execute('SELECT encrypted_access_token FROM nova_social_connections WHERE user_id=?',(uid,)).fetchone()[0]
    assert verify_password('old-password-123',password)
    assert decrypt(token)=='mock-token'
    source.close();target.close()


def test_additive_migration_preserves_existing_records(tmp_path):
    from sqlalchemy import create_engine, text, inspect
    from sqlalchemy.orm import Session
    from nova.db import Base, Draft
    from nova.migrations import run_migrations
    from nova.db import engine
    if engine.dialect.name=='postgresql':
        import secrets
        schema='zova_test_migration_'+secrets.token_hex(6)
        with engine.begin() as connection: connection.execute(text(f'CREATE SCHEMA {schema}'))
        db_engine=create_engine(engine.url,connect_args={'options':f'-csearch_path={schema}'})
    else:
        db_engine=create_engine('sqlite:///'+str(tmp_path/'old.db'))
    Base.metadata.create_all(db_engine)
    with Session(db_engine) as db:
        user=User(email='migration@example.test',password_hash='preserved-hash')
        db.add(user);db.flush();db.add(Draft(user_id=user.id,brief='Existing draft'))
        db.commit()
    with db_engine.begin() as connection:
        connection.execute(text('ALTER TABLE nova_media_assets DROP COLUMN analysis_json'))
        connection.execute(text('ALTER TABLE nova_users DROP COLUMN auth_version'))
        connection.execute(text('ALTER TABLE nova_drafts DROP COLUMN workspace_json'))
        connection.execute(text('ALTER TABLE nova_drafts DROP COLUMN revision'))
    run_migrations(db_engine);run_migrations(db_engine)
    assert 'analysis_json' in {c['name'] for c in inspect(db_engine).get_columns('nova_media_assets')}
    with db_engine.connect() as connection:
        assert connection.execute(text('SELECT password_hash,auth_version FROM nova_users')).first()==('preserved-hash',0)
        assert connection.execute(text('SELECT brief,workspace_json,revision FROM nova_drafts')).first()==('Existing draft','{}',0)
    db_engine.dispose()
