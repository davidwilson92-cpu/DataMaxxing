"""Release migration and legacy OAuth signing checks, without provider calls."""
import os
import uuid
import pytest


@pytest.mark.parametrize('provider_status',[201,403])
def test_legacy_x_oauth_signing_remains_compatible(monkeypatch,provider_status):
    import json
    from types import SimpleNamespace
    from sqlalchemy import select
    from fastapi import HTTPException
    from nova import app as module
    from nova.db import Creator, SessionLocal, PostLog
    from nova.security import encrypt, hash_api_key
    def provider(url,headers,content,timeout):
        assert url=='https://api.x.com/2/tweets' and timeout==30.0
        assert headers['Authorization'].startswith('OAuth ') and 'oauth_signature=' in headers['Authorization']
        assert json.loads(content)=={'text':'Synthetic only'}
        return SimpleNamespace(status_code=provider_status,text='Synthetic denial',json=lambda:{'data':{'id':'synthetic-id'}})
    monkeypatch.setattr(module.httpx,'post',provider)
    with SessionLocal() as db:
        creator=Creator(name='Synthetic',x_username='synthetic-'+uuid.uuid4().hex,api_key_hash=hash_api_key(uuid.uuid4().hex),encrypted_x_api_key=encrypt('key'),encrypted_x_api_secret=encrypt('secret'),encrypted_x_access_token=encrypt('token'),encrypted_x_access_token_secret=encrypt('token-secret'))
        db.add(creator);db.commit()
        if provider_status==201:
            assert module.publish_legacy_creator('Synthetic only',creator,db)['post_id']=='synthetic-id'
        else:
            with pytest.raises(HTTPException):module.publish_legacy_creator('Synthetic only',creator,db)
        log=db.scalar(select(PostLog).where(PostLog.creator_id==creator.id))
        assert log.status==('published' if provider_status==201 else 'unknown')


@pytest.mark.skipif(not os.environ.get('ZOVA_TEST_POSTGRES'),reason='Requires isolated PostgreSQL CI')
def test_existing_postgres_draft_title_migration():
    from sqlalchemy import create_engine, text
    from nova.db import Base, User, Draft
    from nova.migrations import run_migrations
    from sqlalchemy.orm import Session
    from sqlalchemy.engine import make_url
    url=os.environ['ZOVA_TEST_POSTGRES']
    parsed=make_url(url)
    assert parsed.host in {'localhost','127.0.0.1'} and parsed.database.startswith('zova_test_')
    schema='ux_migration_'+uuid.uuid4().hex
    admin=create_engine(url)
    with admin.begin() as conn:conn.execute(text(f'CREATE SCHEMA {schema}'))
    isolated=create_engine(url,connect_args={'options':f'-csearch_path={schema}'})
    try:
        Base.metadata.create_all(isolated)
        with Session(isolated) as db:
            user=User(email='migration@example.test',password_hash='synthetic');db.add(user);db.flush()
            draft=Draft(user_id=user.id,brief='Keep this content',revision=7);db.add(draft);db.commit();did=draft.id
        with isolated.begin() as conn:conn.execute(text('ALTER TABLE nova_drafts DROP COLUMN title'))
        run_migrations(isolated);run_migrations(isolated)
        with isolated.connect() as conn:
            assert conn.execute(text('SELECT brief,revision,title FROM nova_drafts WHERE id=:id'),{'id':did}).one()==('Keep this content',7,'')
    finally:
        isolated.dispose()
        with admin.begin() as conn:conn.execute(text(f'DROP SCHEMA {schema} CASCADE'))
        admin.dispose()
