"""Read-only monitor probe. Exit 1 means attention; route through an approved monitor."""
import json
import os
import sys
from datetime import datetime, timezone
from urllib.parse import urlsplit
import httpx


def check(payload, *, now=None):
    # A successful HTTP request is not evidence of a working publishing loop.
    # Fail closed on an incomplete, stale or unexpected status document.
    if not isinstance(payload,dict):
        return {'status':'attention','reasons':['invalid_status_document']}
    reasons=[]
    incomplete=False
    for key in ['overdue_jobs','uncertain_publications','stuck_publications','stale_billing_accounts','old_usage_reservations','mail_failures_24h','stuck_mail','ai_failures_24h']:
        value=payload.get(key)
        if type(value) is not int or value<0:incomplete=True
        elif value:reasons.append(key)
    # Optional for older deployed status endpoints during a rolling release.
    if 'pending_deletion_requests' in payload:
        value=payload['pending_deletion_requests']
        if type(value) is not int or value<0:incomplete=True
        elif value:reasons.append('pending_deletion_requests')
    spend=payload.get('ai_spend')
    if not isinstance(spend,dict):
        incomplete=True
    else:
        if type(spend.get('threshold_exceeded')) is not bool:incomplete=True
        elif spend['threshold_exceeded']:reasons.append('ai_spend_threshold')
        if type(spend.get('unpriced_calls')) is not int or spend['unpriced_calls']<0:incomplete=True
        elif spend['unpriced_calls']:reasons.append('ai_cost_coverage')
    worker=payload.get('worker')
    if not isinstance(worker,dict) or worker.get('mode') not in {'embedded','external','disabled'}:
        incomplete=True
    elif worker.get('status') not in {'running','idle'} or worker['mode']=='disabled':
        reasons.append('publishing_worker_unhealthy')
    try:
        checked=datetime.fromisoformat(payload['checked_at'].replace('Z','+00:00'))
        if checked.tzinfo is None:raise ValueError('Timezone required')
        age=((now or datetime.now(timezone.utc))-checked).total_seconds()
        if not -60<=age<=300:reasons.append('stale_status_document')
    except (KeyError,ValueError,TypeError,AttributeError):
        incomplete=True
    if payload.get('status') not in {'ok','attention'}:incomplete=True
    if payload.get('recovery_email_configured') is not True:reasons.append('recovery_email_unavailable')
    if payload.get('database')!='reachable':reasons.append('database_unavailable')
    if incomplete:reasons.append('invalid_status_document')
    if payload.get('status')=='attention' and not reasons:reasons.append('service_attention')
    return {'status':'attention' if reasons else 'ok','reasons':reasons}


def probe(url, secret, *, get=None):
    try:parts=urlsplit(url)
    except ValueError:return {'status':'attention','reasons':['invalid_monitor_destination']}
    if (parts.username or parts.password or parts.query or parts.fragment
            or parts.path not in {'','/'} or not parts.hostname
            or (parts.scheme!='https' and not (parts.scheme=='http' and parts.hostname in {'127.0.0.1','localhost'}))):
        return {'status':'attention','reasons':['invalid_monitor_destination']}
    if not secret:
        return {'status':'attention','reasons':['missing_monitor_credential']}
    try:
        get=get or httpx.get
        response=get(url.rstrip('/')+'/internal/status',headers={'Authorization':'Bearer '+secret},timeout=20,follow_redirects=False)
        response.raise_for_status();result=check(response.json())
    except Exception:result={'status':'attention','reasons':['probe_failed']}
    return result


if __name__=='__main__':
    result=probe(os.environ.get('ZOVA_MONITOR_URL',''),os.environ.get('ZOVA_MONITOR_SECRET',''))
    print(json.dumps(result));sys.exit(1 if result['status']=='attention' else 0)
