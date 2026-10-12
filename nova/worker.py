"""Portable dedicated worker: python -m nova.worker.

One active PostgreSQL worker is enforced by a session advisory lock. The lock
connection stays open through dispatch; losing it terminates further polling.
Do not use a transaction-mode pooler for this connection.
"""
import logging
import signal
import threading
import os
from sqlalchemy import text
from .runtime import integer, scheduler_mode, validate_runtime

log=logging.getLogger('nova.worker')
LOCK_ID=826682021


def heartbeat(role,status):
    from .db import SessionLocal,WorkerHeartbeat,utcnow
    with SessionLocal() as db:
        row=db.get(WorkerHeartbeat,role)
        if not row:
            row=WorkerHeartbeat(role=role,started_at=utcnow(),status=status);db.add(row)
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
    role=os.environ.get('ZOVA_WORKER_ROLE','publishing')
    if role not in {'publishing','generation'}:
        raise ValueError('ZOVA_WORKER_ROLE must be publishing or generation')
    lock_id=LOCK_ID if role=='publishing' else LOCK_ID+1
    if role=='generation':
        if os.environ.get('ZOVA_AI_JOBS_ENABLED','false')!='true':
            raise ValueError('Generation worker requires ZOVA_AI_JOBS_ENABLED=true')
        interval=2
    with engine.connect() as connection:
        if not connection.scalar(text('SELECT pg_try_advisory_lock(:key)'),{'key':lock_id}):
            raise RuntimeError('Another dedicated worker already holds the lease')
        connection.commit()
        try:
            while not stop.is_set():
                # Any lost connection exits instead of silently reconnecting
                # without the lock. Supervisor restarts acquire a new lock.
                if connection.invalidated:
                    raise RuntimeError('Worker lock connection was lost')
                connection.execute(text('SELECT 1'));connection.commit()
                try:
                    heartbeat(role,'running')
                    if role=='publishing':
                        result=process_due()
                        log.info('worker_poll_complete published=%s failed=%s',result['published'],result['failed'])
                    else:
                        from .generation_jobs import process_jobs
                        log.info('generation_poll_complete jobs=%s',process_jobs(limit=1))
                    heartbeat(role,'idle')
                except Exception:
                    log.exception('worker_poll_failed')
                    heartbeat(role,'error')
                stop.wait(interval)
        finally:
            if not connection.invalidated:
                connection.execute(text('SELECT pg_advisory_unlock(:key)'),{'key':lock_id})
                connection.commit()


def main():
    logging.basicConfig(level=logging.INFO)
    stop=threading.Event()
    for sig in (signal.SIGINT,signal.SIGTERM):
        signal.signal(sig,lambda *_:stop.set())
    run(stop)


if __name__=='__main__':
    main()
