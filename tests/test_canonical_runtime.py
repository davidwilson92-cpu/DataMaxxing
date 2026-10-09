"""Runtime canonical identities, scoped queries and fresh/legacy startup."""
import os
import subprocess
import sys
import pytest
from sqlalchemy import select, text, event
from sqlalchemy.exc import DBAPIError
from fastapi import HTTPException
from nova.db import (Base, CanonicalWorkspace, SessionLocal, Draft, Brand,
                     OAuthState, engine)
from nova.tenant_migration import workspace_key
from nova.tenant_references import BRAND_TABLES
from test_account_integrity import account


def test_every_brand_owned_model_maps_canonical_reference():
    models = {m.class_.__tablename__ for m in Base.registry.mappers
              if issubclass(m.class_, CanonicalWorkspace)}
    assert models == BRAND_TABLES


def test_runtime_queries_and_aliases_use_canonical_workspace():
    from sqlalchemy.orm import aliased
    _, uid, _, _ = account()
    _, other, _, _ = account()
    with SessionLocal() as db:
        brand = Brand(user_id=uid, name='Separate content')
        db.add(brand); db.flush()
        own = Draft(user_id=uid, brief='Own content')
        foreign = Draft(user_id=other, brief='Other customer')
        secondary = Draft(user_id=uid, brand_id=brand.id, brief='Other brand')
        db.add_all([own, foreign, secondary]); db.commit()
        assert own.workspace_id == workspace_key(uid)
        assert secondary.workspace_id == workspace_key(uid, brand.id)
    queries = []
    def capture(conn, cursor, statement, parameters, context, many):
        if statement.lstrip().startswith('SELECT'): queries.append(statement)
    event.listen(engine, 'before_cursor_execute', capture)
    try:
        with SessionLocal() as db:
            db.info.update(brand_id=0, brand_user_id=uid)
            alias = aliased(Draft)
            assert [r.id for r in db.scalars(select(Draft)).all()] == [own.id]
            assert [r.id for r in db.scalars(select(alias)).all()] == [own.id]
            assert db.get(Draft, foreign.id) is None
            assert db.get(Draft, secondary.id) is None
        assert all('workspace_id =' in q.partition('WHERE')[2] for q in queries)
    finally:
        event.remove(engine, 'before_cursor_execute', capture)


def test_forged_insert_and_identity_changes_are_rejected_in_runtime():
    _, uid, _, _ = account()
    _, other, _, _ = account()
    with SessionLocal() as db:
        db.add(Draft(user_id=uid, workspace_id=workspace_key(other)))
        with pytest.raises(ValueError, match='canonical'): db.flush()
        db.rollback()
        draft = Draft(user_id=uid); db.add(draft); db.commit()
        draft_id = draft.id
        draft.workspace_id = workspace_key(other)
        with pytest.raises(HTTPException): db.flush()
        db.rollback()
        state = OAuthState(user_id=uid, platform='instagram', state_hash='runtime-' + str(uid))
        db.add(state); db.commit()
        assert state.workspace_id == workspace_key(uid)
        state.user_id = other
        with pytest.raises(HTTPException): db.flush()
    # Fresh application schema has database guards too, not just ORM hooks.
    with pytest.raises(DBAPIError):
        with engine.begin() as c:
            c.execute(text('UPDATE nova_drafts SET workspace_id=:wid WHERE id=:id'),
                      {'wid':workspace_key(other), 'id':draft_id})


def test_fresh_startup_installs_guards_and_existing_startup_requires_migration(tmp_path):
    database = tmp_path / 'startup.db'
    env = dict(os.environ, DATABASE_URL='sqlite:///' + database.as_posix())
    def run(code):
        return subprocess.run([sys.executable, '-B', '-c', code], env=env,
                              capture_output=True, text=True, timeout=30)
    seeded = run("from nova.db import SessionLocal, User; "
                 "db=SessionLocal(); db.add(User(email='startup@example.test',password_hash='synthetic')); db.commit()")
    assert seeded.returncode == 0, seeded.stderr
    assert run('import nova.db').returncode == 0
    # Remove only the migration attestation in this disposable fixture.
    import sqlite3
    with sqlite3.connect(database) as c:
        c.execute("DELETE FROM zova_schema_migrations WHERE version='20261009_workspace_references'")
    blocked = run('import nova.db')
    assert blocked.returncode != 0
    assert 'Workspace reference migration required' in blocked.stderr
    with sqlite3.connect(database) as c:
        assert c.execute('SELECT email,password_hash FROM nova_users').fetchone() == ('startup@example.test','synthetic')


def test_existing_database_offline_reference_upgrade_preserves_runtime_content(tmp_path):
    import sqlite3
    database = tmp_path / 'legacy-upgrade.db'
    env = dict(os.environ, DATABASE_URL='sqlite:///' + database.as_posix())
    def run(code):
        return subprocess.run([sys.executable, '-B', '-c', code], env=env,
                              capture_output=True, text=True, timeout=30)
    from sqlalchemy import MetaData, create_engine
    from sqlalchemy.orm import Session
    from nova.db import User
    from nova.migrations import run_migrations
    legacy = MetaData()
    for table in Base.metadata.sorted_tables:
        table.to_metadata(legacy)
    for name in BRAND_TABLES:
        table = legacy.tables[name]
        for constraint in list(table.constraints):
            if 'workspace_id' in constraint.columns:
                table.constraints.remove(constraint)
        for index in list(table.indexes):
            if 'workspace_id' in index.columns:
                table.indexes.remove(index)
        table._columns.remove(table.c.workspace_id)
    isolated = create_engine(env['DATABASE_URL'])
    legacy.create_all(isolated)
    run_migrations(isolated)
    with Session(isolated) as db:
        owner = User(email='legacy@example.test',password_hash='preserved-hash',auth_version=4)
        db.add(owner); db.commit(); uid=owner.id
    with isolated.begin() as c:
        c.execute(legacy.tables['nova_drafts'].insert().values(user_id=uid,brief='Preserved draft'))
    isolated.dispose()
    blocked = run('import nova.db')
    assert blocked.returncode != 0 and 'canonical workspace reference is missing' in blocked.stderr
    migrated = run("from sqlalchemy import create_engine; import os; "
                   "from nova.tenant_references import apply_references; "
                   "apply_references(create_engine(os.environ['DATABASE_URL']),writes_paused=True)")
    assert migrated.returncode == 0, migrated.stderr
    accepted = run("from nova.db import SessionLocal,User,Draft; from sqlalchemy import select; "
                   "from nova.tenant_migration import workspace_key; db=SessionLocal(); "
                   "u=db.scalar(select(User)); d=db.scalar(select(Draft)); "
                   "assert (u.password_hash,u.auth_version,d.brief)==('preserved-hash',4,'Preserved draft'); "
                   "assert d.workspace_id==workspace_key(u.id)")
    assert accepted.returncode == 0, accepted.stderr
