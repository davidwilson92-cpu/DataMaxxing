"""Authenticated operational signals without credentials or customer content."""
import hmac
import os
from datetime import timedelta
from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import func, select, text
from .db import SessionLocal, ScheduledPost, Publication, BillingEvent, BillingAccount, UsageEntry, MailDelivery, AICall, utcnow
from .readiness import spend_summary, cohort_report

router=APIRouter()


def require_operations(authorization, *, monitor=False):
    """Monitoring can read health, never dispatch jobs or inspect cohorts."""
    supplied=(authorization or '').removeprefix('Bearer ').encode('utf-8')
    secrets=[os.environ.get('SCHEDULER_SECRET') or os.environ.get('ADMIN_API_KEY')]
    if monitor:
        secrets.append(os.environ.get('MONITOR_READ_TOKEN'))
    if not any(secret and hmac.compare_digest(supplied,secret.encode('utf-8')) for secret in secrets):
        raise HTTPException(401,'Invalid operations credential')


def worker_status(db):
    from .runtime import scheduler_mode, integer
    from .db import WorkerHeartbeat
    mode=scheduler_mode()
    if mode=='disabled':return {'mode':mode,'status':'disabled'}
    row=db.get(WorkerHeartbeat,'publishing')
    threshold=utcnow()-timedelta(seconds=max(integer('SCHEDULER_INTERVAL_SECONDS',60,30,3600)*3,300))
    # Compare timestamps in the database so SQLite's naive datetimes do not
    # accidentally make the PostgreSQL check behave differently.
    recent=db.scalar(select(WorkerHeartbeat.role).where(WorkerHeartbeat.role=='publishing',WorkerHeartbeat.started_at>=threshold))
    return {'mode':mode,'status':'missing' if row is None else 'stale' if not recent else row.status}

@router.get('/internal/ready')
def ready(authorization: str | None = Header(default=None)):
    """Dependency readiness, separate from public process liveness.

    This does not make provider requests or claim the scheduler is healthy.
    Full table selections validate required columns even on an empty database.
    """
    require_operations(authorization,monitor=True)
    try:
        from .db import User, Draft, PerformanceSnapshot, AIConsent, WorkerHeartbeat
        with SessionLocal() as db:
            db.execute(text('SELECT 1'))
            for model in (User, Draft, Publication, ScheduledPost, PerformanceSnapshot, AIConsent, WorkerHeartbeat):
                db.execute(select(model).limit(1)).first()
    except Exception:
        # Do not expose database URLs, credentials, schema or driver errors.
        raise HTTPException(503,'Application dependencies are not ready') from None
    return {'status':'ready','database':'reachable','required_schema':'available',
            'worker':'not_checked','providers':'not_checked'}

@router.get('/internal/status')
def status(authorization: str | None = Header(default=None)):
    require_operations(authorization,monitor=True)
    with SessionLocal() as db:
        db.execute(text('SELECT 1'))
        worker=worker_status(db)
        from .recovery import recovery_ready
        mail_configured=recovery_ready()
        overdue=db.scalar(select(func.count()).select_from(ScheduledPost).where(ScheduledPost.status=='scheduled',ScheduledPost.scheduled_at<utcnow()-timedelta(minutes=5)))
        uncertain=db.scalar(select(func.count()).select_from(Publication).where(Publication.status=='unknown'))
        stuck=db.scalar(select(func.count()).select_from(Publication).where(Publication.status.in_(['publishing','queued']),Publication.updated_at<utcnow()-timedelta(minutes=15)))
        spend=spend_summary(db)
        stale_billing=db.scalar(select(func.count()).select_from(BillingAccount).where(BillingAccount.status.in_(['active','trialing','past_due']),BillingAccount.synced_at<utcnow()-timedelta(days=2)))
        reservations=db.scalar(select(func.count()).select_from(UsageEntry).where(UsageEntry.state=='reserved',UsageEntry.created_at<utcnow()-timedelta(hours=1)))
        latest=db.scalar(select(func.max(BillingEvent.processed_at)))
        mail_failures=db.scalar(select(func.count()).select_from(MailDelivery).where(MailDelivery.status=='failed',MailDelivery.created_at>utcnow()-timedelta(days=1)))
        mail_stuck=db.scalar(select(func.count()).select_from(MailDelivery).where(MailDelivery.status=='sending',MailDelivery.created_at<utcnow()-timedelta(minutes=5)))
        ai_failures=db.scalar(select(func.count()).select_from(AICall).where(AICall.status!='returned',AICall.created_at>utcnow()-timedelta(days=1)))
        attention=bool(ai_failures or overdue or uncertain or stuck or spend['threshold_exceeded'] or spend['unpriced_calls'] or stale_billing or reservations or mail_failures or mail_stuck or not mail_configured or worker['status'] not in {'running','idle'})
        return {'status':'attention' if attention else 'ok','database':'reachable','overdue_jobs':overdue,'uncertain_publications':uncertain,'stuck_publications':stuck,
                'stale_billing_accounts':stale_billing,'last_billing_event':latest.isoformat() if latest else None,
                'ai_failures_24h':ai_failures,'old_usage_reservations':reservations,'mail_failures_24h':mail_failures,'stuck_mail':mail_stuck,'recovery_email_configured':mail_configured,'ai_spend':spend,'worker':worker,'checked_at':utcnow().isoformat()}


@router.get('/internal/cohorts')
def cohorts(authorization: str | None = Header(default=None)):
    require_operations(authorization)
    with SessionLocal() as db:return cohort_report(db)
