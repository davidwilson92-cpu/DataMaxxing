"""Explicit schema preparation for a backed-up, isolated deployment target.

Use a migration identity, with web/worker writes stopped. Importing the database
module uses the existing additive migration implementation. Never run this during
ordinary cloud service startup; use ZOVA_SCHEMA_MODE=verify there.
"""
import argparse
import os
import sys
from pathlib import Path

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--confirm-target-backed-up',action='store_true',required=True)
    parser.parse_args()
    if not os.environ.get('DATABASE_URL'):
        raise SystemExit('Set an explicit target DATABASE_URL; refusing the default database')
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    os.environ['ZOVA_SCHEMA_MODE']='initialize'
    os.environ['ZOVA_SCHEDULER_MODE']='disabled'
    os.environ['ZOVA_WEB_REPLICAS']='1'
    from nova.db import Base,engine
    from nova.runtime import prepare_schema
    os.environ['ZOVA_SCHEMA_MODE']='verify'
    prepare_schema(Base.metadata,engine)
    print('Schema compatibility verified. Grants, restored data, media and encryption keys require separate checks.')
