import os
import threading
from datetime import timedelta
import pytest
from sqlalchemy import MetaData, Table, Column, Integer, create_engine, inspect, text
from nova.runtime import validate_runtime, prepare_schema, database_options
from nova.db import SessionLocal, WorkerHeartbeat, engine, utcnow


def external_config(monkeypatch):
    monkeypatch.setenv('ZOVA_SCHEDULER_MODE','external')
    monkeypatch.setenv('DATABASE_URL','postgresql://synthetic:synthetic@127.0.0.1/zova_test_runtime')
    monkeypatch.setenv('S3_BUCKET','synthetic-private')
    monkeypatch.delenv('S3_PUBLIC_BASE_URL',raising=False)
    monkeypatch.setenv('ZOVA_SCHEMA_MODE','verify')
    monkeypatch.setenv('DB_CONNECTION_BUDGET','40')


def test_current_single_server_is_compatible_and_bad_scaling_refuses(monkeypatch):
    monkeypatch.delenv('ZOVA_SCHEDULER_MODE',raising=False)
    assert validate_runtime()=='embedded'
    monkeypatch.setenv('ZOVA_WEB_REPLICAS','2')
    with pytest.raises(ValueError,match='external scheduler'):validate_runtime()
    external_config(monkeypatch)
    with pytest.raises(ValueError,match='connection budget'):validate_runtime()
    monkeypatch.setenv('DB_CONNECTION_BUDGET','50')
    assert validate_runtime()=='external'
    monkeypatch.setenv('S3_PUBLIC_BASE_URL','https://public.example')
    with pytest.raises(ValueError,match='private shared'):validate_runtime()


def test_verify_mode_does_not_create_or_repair_missing_schema(monkeypatch):
    isolated=create_engine('sqlite://')
    metadata=MetaData();Table('synthetic',metadata,Column('id',Integer,primary_key=True))
    monkeypatch.setenv('ZOVA_SCHEMA_MODE','verify')
    with pytest.raises(RuntimeError,match='schema is incomplete'):prepare_schema(metadata,isolated)
    assert not inspect(isolated).get_table_names()
    metadata.create_all(isolated)
    prepare_schema(metadata,isolated)
    metadata.tables['synthetic'].append_column(Column('new_column',Integer))
    with pytest.raises(RuntimeError,match='columns are incomplete'):prepare_schema(metadata,isolated)
    assert 'new_column' not in {c['name'] for c in inspect(isolated).get_columns('synthetic')}


def test_pool_budgets_and_disabled_poll(monkeypatch):
    assert database_options('sqlite://')=={}
    monkeypatch.setenv('DB_POOL_SIZE','0')
    with pytest.raises(ValueError):database_options('postgresql://')
    monkeypatch.setenv('ZOVA_SCHEDULER_MODE','disabled')
    from nova.scheduler import process_due
    assert process_due()=={'published':0,'failed':0}


def test_invalid_external_configuration_cannot_create_a_database(tmp_path):
    import os, subprocess, sys
    target=tmp_path/'must-not-exist.db'
    env={**os.environ,'DATABASE_URL':'sqlite:///'+target.as_posix(),
         'ZOVA_SCHEDULER_MODE':'external','ZOVA_SCHEMA_MODE':'initialize'}
    result=subprocess.run([sys.executable,'-B','-c','import nova.db'],env=env,capture_output=True,text=True,timeout=15)
    assert result.returncode!=0
    assert 'Separate services require PostgreSQL' in result.stderr
    assert not target.exists()


def test_stale_worker_is_visible(monkeypatch):
    monkeypatch.setenv('ZOVA_SCHEDULER_MODE','external')
    from nova.operations import worker_status
    with SessionLocal() as db:
        row=db.get(WorkerHeartbeat,'publishing')
        if row:db.delete(row);db.commit()
        assert worker_status(db)['status']=='missing'
        db.add(WorkerHeartbeat(role='publishing',status='running',started_at=utcnow()-timedelta(hours=1)));db.commit()
        assert worker_status(db)['status']=='stale'


@pytest.mark.skipif(engine.dialect.name!='postgresql',reason='Real PostgreSQL advisory-lock validation')
def test_only_one_worker_and_restart_reacquires_lock(monkeypatch):
    external_config(monkeypatch)
    from nova import worker, scheduler
    calls=[]
    stop=threading.Event()
    def poll():
        calls.append(1);stop.set();return {'published':0,'failed':0}
    monkeypatch.setattr(scheduler,'process_due',poll)
    with engine.connect() as owner:
        assert owner.scalar(text('SELECT pg_try_advisory_lock(:key)'),{'key':worker.LOCK_ID})
        owner.commit()
        with pytest.raises(RuntimeError,match='holds the lease'):worker.run(stop)
        assert not calls
        owner.execute(text('SELECT pg_advisory_unlock(:key)'),{'key':worker.LOCK_ID});owner.commit()
    worker.run(stop)
    assert calls==[1]
    with engine.connect() as restarted:
        assert restarted.scalar(text('SELECT pg_try_advisory_lock(:key)'),{'key':worker.LOCK_ID})
        restarted.execute(text('SELECT pg_advisory_unlock(:key)'),{'key':worker.LOCK_ID})
