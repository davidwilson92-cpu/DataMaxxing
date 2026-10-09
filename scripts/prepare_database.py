"""Explicit offline schema preparation; never inherit runtime database credentials."""
import argparse
import os
from pathlib import Path
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--writes-paused',action='store_true')
    args=parser.parse_args()
    if not args.apply or not args.writes_paused:
        parser.error('Schema preparation requires --apply --writes-paused after pausing application and worker writes')
    url=os.environ.get('ZOVA_MIGRATION_DATABASE_URL')
    if not url:
        parser.error('Set ZOVA_MIGRATION_DATABASE_URL explicitly; runtime credentials are not used')
    os.environ['DATABASE_URL']=url
    os.environ['ZOVA_SCHEMA_MODE']='bootstrap'
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    try:
        # db imports models and applies the versioned additive migrations.
        # Existing customers still require the separate registry/reference backfill.
        from nova.db import Base,engine
        from nova.schema_startup import verify_runtime_schema
        with engine.connect() as c:verify_runtime_schema(c,Base.metadata)
        engine.dispose()
    except Exception:
        print('Schema preparation failed. Inspect the isolated migration environment; no credentials or customer records are printed.',file=sys.stderr)
        return 1
    print('Schema prepared and verified. Runtime access and production approval remain separate checks.')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
