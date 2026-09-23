"""Authenticated operational signals without credentials or customer content."""
import hmac
import os
from datetime import timedelta
from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import func, select, text
from .db import SessionLocal, ScheduledPost, Publication, BillingEvent, BillingAccount, UsageEntry, MailDelivery, AICall, utcnow
from .readiness import spend_summary, cohort_report

router=APIRouter()

@router.get('/internal/status')
def status(authorization: str | None = Header(default=None)):
    secret=os.environ.get('SCHEDULER_SECRET') or os.environ.get('ADMIN_API_KEY')
    supplied=(authorization or '').removeprefix('Bearer ')
    if not secret or not hmac.compare_digest(supplied,secret):
        raise HTTPException(401,'Invalid operations credential')
    with SessionLocal() as db:
        db.execute(text('SELECT 1'))
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
        attention=bool(ai_failures or overdue or uncertain or stuck or spend['threshold_exceeded'] or spend['unpriced_calls'] or stale_billing or mail_failures or mail_stuck)
        return {'status':'attention' if attention else 'ok','database':'reachable','overdue_jobs':overdue,'uncertain_publications':uncertain,'stuck_publications':stuck,
                'stale_billing_accounts':stale_billing,'last_billing_event':latest.isoformat() if latest else None,
                'ai_failures_24h':ai_failures,'old_usage_reservations':reservations,'mail_failures_24h':mail_failures,'stuck_mail':mail_stuck,'ai_spend':spend,'checked_at':utcnow().isoformat()}


@router.get('/internal/cohorts')
def cohorts(authorization: str | None = Header(default=None)):
    secret=os.environ.get('SCHEDULER_SECRET') or os.environ.get('ADMIN_API_KEY')
    if not secret or not hmac.compare_digest((authorization or '').removeprefix('Bearer '),secret):
        raise HTTPException(401,'Invalid operations credential')
    with SessionLocal() as db:return cohort_report(db)
