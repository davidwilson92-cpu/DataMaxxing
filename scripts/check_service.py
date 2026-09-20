"""Read-only monitor probe. Exit 1 means attention; route through an approved monitor."""
import json
import os
import sys
from urllib.parse import urlsplit
import httpx


def check(payload):
    reasons=[]
    for key in ['overdue_jobs','uncertain_publications','stuck_publications','stale_billing_accounts','mail_failures_24h','stuck_mail']:
        if payload.get(key):reasons.append(key)
    if payload.get('ai_spend',{}).get('threshold_exceeded'):reasons.append('ai_spend_threshold')
    if payload.get('ai_spend',{}).get('unpriced_calls'):reasons.append('ai_cost_coverage')
    if payload.get('database')!='reachable':reasons.append('database_unavailable')
    return {'status':'attention' if reasons else 'ok','reasons':reasons}


if __name__=='__main__':
    url=os.environ.get('ZOVA_MONITOR_URL','')
    parts=urlsplit(url)
    if parts.scheme!='https' and not (parts.scheme=='http' and parts.hostname in {'127.0.0.1','localhost'}):
        raise SystemExit('Monitor needs HTTPS or loopback HTTP')
    try:
        secret=os.environ['ZOVA_MONITOR_SECRET']
        response=httpx.get(url.rstrip('/')+'/internal/status',headers={'Authorization':'Bearer '+secret},timeout=20,follow_redirects=False)
        response.raise_for_status();result=check(response.json())
    except Exception:result={'status':'attention','reasons':['probe_failed']}
    print(json.dumps(result));sys.exit(1 if result['status']=='attention' else 0)
