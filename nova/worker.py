"""Run the existing publishing scheduler independently: python -m nova.worker.

No new queue semantics or automatic retry of ambiguous sends. PostgreSQL's
session lock keeps one poller; a supervisor must restart a lost lock connection.
"""
import logging
import signal
import threading
from sqlalchemy import text
from .runtime import integer, scheduler_mode, validate_runtime

log=logging.getLogger('nova.worker')
LOCK_ID=826682021


def heartbeat(status):
    from .db import SessionLocal, WorkerHeartbeat, utcnow
    with SessionLocal() as db:
        row=db.get(WorkerHeartbeat,'publishing')
        if row is None:
            row=WorkerHeartbeat(role='publishing',started_at=utcnow(),status=status)
            db.add(row)
        row.status=status
        if status=='running':row.started_at=utcnow()
        if status=='idle':row.completed_at=utcnow()
        db.commit()


def run(stop=None):
    if scheduler_mode()!='external':
        raise RuntimeError('Dedicated worker requires ZOVA_SCHEDULER_MODE=external')
    validate_runtime()
    from .db import engine
    from .scheduler import process_due
    if engine.dialect.name!='postgresql':
        raise RuntimeError('Dedicated worker requires PostgreSQL')
    stop=stop or threading.Event()
    interval=integer('SCHEDULER_INTERVAL_SECONDS',60,30,3600)
    with engine.connect() as connection:
        if not connection.scalar(text('SELECT pg_try_advisory_lock(:key)'),{'key':LOCK_ID}):
            raise RuntimeError('Another publishing worker holds the lease')
        connection.commit()
        try:
            while not stop.is_set():
                if connection.invalidated:
                    raise RuntimeError('Worker lock connection was lost')
                connection.execute(text('SELECT 1'));connection.commit()
                try:
                    heartbeat('running')
                    result=process_due()
                    log.info('worker_poll_complete published=%s failed=%s',result['published'],result['failed'])
                    heartbeat('idle')
                except Exception:
                    log.error('worker_poll_failed')
                    heartbeat('error')
                stop.wait(interval)
        finally:
            if not connection.invalidated:
                connection.execute(text('SELECT pg_advisory_unlock(:key)'),{'key':LOCK_ID})
                connection.commit()


def main():
    logging.basicConfig(level=logging.INFO)
    stop=threading.Event()
    for sig in (signal.SIGINT,signal.SIGTERM):
        signal.signal(sig,lambda *_:stop.set())
    run(stop)


if __name__=='__main__':
    main()
