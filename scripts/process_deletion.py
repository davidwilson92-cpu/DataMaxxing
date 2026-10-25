"""Read a deletion plan or execute one verified, drained limited-beta case.

Run on the deployment host with its persistent upload disk and existing secrets.
No credentials or customer content are printed. See the deletion runbook.
"""
import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit


def maintenance_proof(expected_host):
    import httpx
    base=os.environ.get('PUBLIC_BASE_URL','').rstrip('/')
    url=urlsplit(base)
    if url.scheme!='https' or url.hostname!=expected_host or url.username or url.password or url.path or url.query or url.fragment:
        raise ValueError('PUBLIC_BASE_URL must be the expected HTTPS service origin')
    token=os.environ.get('SCHEDULER_SECRET') or os.environ.get('ADMIN_API_KEY')
    if not token:raise ValueError('A full operations credential is required; a monitor token is not sufficient')
    try:
        response=httpx.get(base+'/internal/maintenance',headers={'Authorization':'Bearer '+token},timeout=15,follow_redirects=False)
        if response.status_code!=200:raise ValueError()
        return response.json()
    except Exception:
        raise ValueError('Could not verify maintenance on the running service; no erasure was started') from None


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['plan','execute'])
    parser.add_argument('--receipt',required=True)
    parser.add_argument('--case',help='Nonpersonal operational case reference, at least 8 characters')
    parser.add_argument('--confirm-receipt',help='Repeat the exact receipt to authorise this one case')
    parser.add_argument('--expected-host',help='Expected live HTTPS service hostname, e.g. zova-social.com')
    parser.add_argument('--confirm-services-drained',action='store_true')
    parser.add_argument('--confirm-retention-reviewed',action='store_true')
    args=parser.parse_args(argv)
    if not os.environ.get('DATABASE_URL'):parser.error('An explicit deployment DATABASE_URL is required')
    if args.action=='execute':
        if args.confirm_receipt!=args.receipt:parser.error('Repeat the same receipt with --confirm-receipt')
        if not args.case or len(args.case.strip())<8 or not args.expected_host:parser.error('--case and --expected-host are required')
        if not os.environ.get('UPLOAD_DIR') or not Path(os.environ['UPLOAD_DIR']).is_absolute():parser.error('An explicit absolute deployment UPLOAD_DIR is required')
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    # An erasure command must never silently migrate a database.
    os.environ['ZOVA_SCHEMA_MODE']='verify'
    from nova.db import SessionLocal
    from nova.deletion_operator import plan_receipt,execute_receipt
    try:
        with SessionLocal() as db:
            if args.action=='plan':result=plan_receipt(db,args.receipt)
            else:result=execute_receipt(db,args.receipt,args.case,maintenance_proof(args.expected_host),
                services_drained=args.confirm_services_drained,retention_reviewed=args.confirm_retention_reviewed)
        print(json.dumps(result,indent=2));return 0
    except ValueError as exc:
        print('Not completed: '+str(exc),file=sys.stderr);return 2
    except Exception:
        print('Not completed: operation failed; keep maintenance on and inspect the receipt before retrying. No secrets are included here.',file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
