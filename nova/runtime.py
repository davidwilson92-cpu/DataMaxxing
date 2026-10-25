"""Portable deployment controls, selectively adapted from the earlier mobile foundation."""
import os


def integer(name, default, minimum, maximum):
    value = int(os.environ.get(name, str(default)))
    if not minimum <= value <= maximum:
        raise ValueError(f'{name} must be between {minimum} and {maximum}')
    return value


def database_options(url):
    if url.startswith('sqlite'):
        return {}
    return {'pool_size':integer('DB_POOL_SIZE',5,1,50),
            'max_overflow':integer('DB_MAX_OVERFLOW',10,0,50),
            'pool_timeout':integer('DB_POOL_TIMEOUT',30,1,120),
            'pool_recycle':integer('DB_POOL_RECYCLE',1800,30,86400)}


def scheduler_mode():
    mode = os.environ.get('ZOVA_SCHEDULER_MODE','embedded')
    if mode not in {'embedded','external','disabled'}:
        raise ValueError('ZOVA_SCHEDULER_MODE must be embedded, external or disabled')
    return mode


def validate_runtime():
    mode = scheduler_mode()
    maintenance=os.environ.get('ZOVA_MAINTENANCE_MODE','')
    if maintenance not in {'','account-erasure'}:
        raise ValueError('Unknown maintenance mode')
    if maintenance and mode!='disabled':
        raise ValueError('Account erasure maintenance requires disabled scheduling')
    replicas = integer('ZOVA_WEB_REPLICAS',1,1,100)
    if replicas > 1 and mode != 'external':
        raise ValueError('Multiple web instances require an external scheduler')
    if mode == 'external':
        if not os.environ.get('DATABASE_URL','').startswith(('postgres:','postgresql:','postgresql+psycopg:')):
            raise ValueError('Separate services require PostgreSQL')
        if not os.environ.get('S3_BUCKET') or os.environ.get('S3_PUBLIC_BASE_URL'):
            raise ValueError('Separate services require private shared object storage')
        if os.environ.get('ZOVA_SCHEMA_MODE','initialize') != 'verify':
            raise ValueError('Separate services require schema verification mode')
        # Include the publishing worker pool and its held lock connection.
        capacity = integer('DB_CONNECTION_BUDGET',0,1,10000)
        options = database_options(os.environ['DATABASE_URL'])
        needed = (replicas + 1) * (options['pool_size'] + options['max_overflow']) + 1
        if needed > capacity:
            raise ValueError('Database connection budget is too small for the configured services')
    return mode


def prepare_schema(metadata, engine):
    mode = os.environ.get('ZOVA_SCHEMA_MODE','initialize')
    if mode == 'initialize':
        from .migrations import run_migrations
        metadata.create_all(bind=engine)
        run_migrations(engine)
    elif mode == 'verify':
        from sqlalchemy import inspect
        inspector=inspect(engine)
        for table in metadata.sorted_tables:
            if not inspector.has_table(table.name):
                raise RuntimeError('Database schema is incomplete; run offline preparation')
            columns={column['name'] for column in inspector.get_columns(table.name)}
            if not set(table.columns.keys()) <= columns:
                raise RuntimeError('Database columns are incomplete; run offline preparation')
        # Compatibility only: this is not a database grants or RLS audit.
    else:
        raise ValueError('ZOVA_SCHEMA_MODE must be initialize or verify')
