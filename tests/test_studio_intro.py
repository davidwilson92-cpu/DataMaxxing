import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from nova.app import app
from nova.db import Base, SessionLocal, User, engine
from nova.security import make_user_session


def account():
    with SessionLocal() as db:
        user = User(email=f'intro-{uuid.uuid4().hex}@example.test', password_hash='synthetic')
        db.add(user); db.commit(); uid = user.id
    return uid, {'nova_session': make_user_session(uid)}


def test_intro_claim_is_once_across_tabs_and_is_account_scoped():
    uid, cookies = account()
    other, other_cookies = account()
    def claim(_):
        client = TestClient(app)
        return client.post('/api/studio/intro/claim', cookies=cookies).json()['show']
    # Competing tabs must not both launch the automatic introduction.
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(claim, range(2))) == [False, True]
    client = TestClient(app)
    assert client.post('/api/studio/intro/claim', cookies=cookies, json={'user_id': other}).json() == {'show': False}
    assert client.post('/api/studio/intro/claim', cookies=other_cookies).json() == {'show': True}
    with SessionLocal() as db:
        assert db.get(User, uid).studio_intro_pending is False


def test_intro_requires_session_and_rejects_cross_site_claims():
    _, cookies = account()
    # The full suite intentionally exhausts the shared anonymous test IP.
    client = TestClient(app, client=('127.0.0.177', 50000))
    assert client.post('/api/studio/intro/claim', follow_redirects=False).status_code in {303, 401}
    assert client.post('/api/studio/intro/claim', cookies=cookies, headers={'Origin': 'https://other.example'}).status_code == 403
    assert client.post('/api/studio/intro/claim', cookies=cookies).json() == {'show': True}


def test_guide_is_public_and_help_bookmarks_still_work():
    client = TestClient(app)
    for url in ['/guide', '/help']:
        response = client.get(url)
        assert response.status_code == 200
        assert 'ZOVA GUIDE' in response.text and '/studio?intro=1' in response.text


def test_intro_migration_preserves_existing_accounts_without_auto_tour(tmp_path):
    from nova.migrations import run_migrations
    if engine.dialect.name == 'postgresql':
        schema = 'intro_migration_' + uuid.uuid4().hex
        with engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA {schema}'))
        isolated = create_engine(engine.url, connect_args={'options': f'-csearch_path={schema}'})
    else:
        isolated = create_engine('sqlite:///' + str(tmp_path / 'intro.db'))
    try:
        Base.metadata.create_all(isolated)
        with Session(isolated) as db:
            db.add(User(email='old@example.test', display_name='Existing creator', password_hash='preserved'))
            db.commit()
        with isolated.begin() as conn:
            conn.execute(text('ALTER TABLE nova_users DROP COLUMN studio_intro_pending'))
        run_migrations(isolated); run_migrations(isolated)
        with Session(isolated) as db:
            old = db.query(User).one()
            assert old.studio_intro_pending is False
            assert (old.display_name, old.password_hash) == ('Existing creator', 'preserved')
            fresh = User(email='new@example.test', password_hash='new-synthetic')
            db.add(fresh); db.commit()
            assert fresh.studio_intro_pending is True
    finally:
        isolated.dispose()
        if engine.dialect.name == 'postgresql':
            with engine.begin() as conn:
                conn.execute(text(f'DROP SCHEMA {schema} CASCADE'))
