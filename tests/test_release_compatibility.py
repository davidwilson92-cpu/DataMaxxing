"""Release migration and legacy OAuth signing checks, without provider calls."""
import os
import uuid
import pytest


def test_legacy_x_oauth_signing_remains_compatible():
    import requests
    import tweepy
    auth = tweepy.OAuth1UserHandler('synthetic-key', 'synthetic-secret', 'synthetic-token', 'synthetic-token-secret')
    request = requests.Request('POST', 'https://api.x.com/2/tweets', json={'text':'Synthetic only'}, auth=auth.apply_auth()).prepare()
    header=request.headers['Authorization']
    if isinstance(header,bytes):header=header.decode()
    assert header.startswith('OAuth ') and 'oauth_signature=' in header


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
