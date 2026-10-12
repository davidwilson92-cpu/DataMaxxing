"""Explicit pre-deploy schema preparation. Back up first; never run concurrently.

Usage: python -m scripts.prepare_shared_schema
Uses the existing additive migration system; no provider requests or user deletion.
"""
import os


def main():
    if not os.environ.get('DATABASE_URL'):
        raise SystemExit('Set the intended DATABASE_URL explicitly')
    os.environ['ZOVA_SCHEMA_MODE']='initialize'
    from nova.db import Base,engine
    from nova.runtime import prepare_schema
    os.environ['ZOVA_SCHEMA_MODE']='verify'
    prepare_schema(Base.metadata,engine)
    print('Schema prepared and compatible. This does not certify permissions or data recovery.')


if __name__=='__main__':main()
