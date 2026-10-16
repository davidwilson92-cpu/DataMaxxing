"""Portable runtime controls; existing single-server deployments keep their defaults."""
import os


def integer(name, default, minimum, maximum):
    value = int(os.environ.get(name, str(default)))
    if not minimum <= value <= maximum:
        raise ValueError(f'{name} must be between {minimum} and {maximum}')
    return value


def database_options(url):
    if url.startswith('sqlite'):
        return {}
    return {
        'pool_size': integer('DB_POOL_SIZE', 5, 1, 50),
        'max_overflow': integer('DB_MAX_OVERFLOW', 5, 0, 50),
        'pool_timeout': integer('DB_POOL_TIMEOUT', 15, 1, 120),
        'pool_recycle': integer('DB_POOL_RECYCLE', 1800, 30, 86400),
    }


def scheduler_mode():
    mode = os.environ.get('ZOVA_SCHEDULER_MODE', 'embedded')
    if mode not in {'embedded', 'external', 'disabled'}:
        raise ValueError('ZOVA_SCHEDULER_MODE must be embedded, external or disabled')
    return mode


def validate_runtime():
    """Refuse known unsafe multi-instance configurations, without claiming readiness."""
    mode = scheduler_mode()
    replicas = integer('ZOVA_WEB_REPLICAS', 1, 1, 100)
    if replicas > 1:
        if mode != 'external':
            raise ValueError('Multiple web instances require an external scheduler')
    if mode == 'external':
        if not os.environ.get('DATABASE_URL', '').startswith(('postgres:', 'postgresql:', 'postgresql+psycopg:')):
            raise ValueError('Separate services require PostgreSQL')
        if not os.environ.get('S3_BUCKET'):
            raise ValueError('Separate services require shared object storage')
        if os.environ.get('ZOVA_SCHEMA_MODE','initialize') != 'verify':
            raise ValueError('Separate services require schema verification mode')
    if os.environ.get('ZOVA_AI_JOBS_ENABLED','false')=='true' and mode!='external':
        raise ValueError('Background AI jobs require separate workers')
    return mode


def prepare_schema(metadata, engine):
    mode=os.environ.get('ZOVA_SCHEMA_MODE','initialize')
    if mode=='initialize':
        from .migrations import run_migrations
        metadata.create_all(bind=engine)
        run_migrations(engine)
    elif mode=='verify':
        from sqlalchemy import inspect
        inspector=inspect(engine)
        for table in metadata.sorted_tables:
            if not inspector.has_table(table.name):
                raise RuntimeError('Database schema is incomplete; run the offline preparation step')
            columns={c['name'] for c in inspector.get_columns(table.name)}
            if not set(table.columns.keys()) <= columns:
                raise RuntimeError('Database columns are incomplete; run the offline preparation step')
        # This is compatibility verification, not a grants/RLS or constraint audit.
    else:
        raise ValueError('ZOVA_SCHEMA_MODE must be initialize or verify')
