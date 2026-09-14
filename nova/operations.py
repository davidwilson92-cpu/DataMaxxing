"""Authenticated operational signals without credentials or customer content."""
import hmac
import os
from datetime import timedelta
from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import func, select, text
from .db import SessionLocal, ScheduledPost, Publication, utcnow

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
        return {'status':'attention' if overdue or uncertain or stuck else 'ok','database':'reachable','overdue_jobs':overdue,'uncertain_publications':uncertain,'stuck_publications':stuck,'checked_at':utcnow().isoformat()}
