"""Offline registry migration; read-only unless --apply --writes-paused are supplied."""
import argparse
import json
import os
from pathlib import Path
import sys
from sqlalchemy import create_engine
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nova.tenant_migration import apply_registry, inspect_mapping, verify_registry, MappingError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--writes-paused', action='store_true')
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    url = os.environ.get('ZOVA_MIGRATION_DATABASE_URL')
    if not url:
        parser.error('Set ZOVA_MIGRATION_DATABASE_URL explicitly; no application credential fallback is used')
    engine = create_engine(url)
    try:
        if args.apply:
            report = apply_registry(engine, writes_paused=args.writes_paused)
        else:
            with engine.connect() as c:
                report = verify_registry(c) if args.verify else inspect_mapping(c)
        print(json.dumps(report, indent=2))
        return 0
    except MappingError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception:
        print('Registry migration failed. No credentials or customer content are included in this output. Inspect in the isolated migration environment.', file=sys.stderr)
        return 1
    finally:
        engine.dispose()


if __name__ == '__main__':
    raise SystemExit(main())
