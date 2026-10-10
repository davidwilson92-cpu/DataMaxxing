"""Transaction-local limits for offline PostgreSQL workspace migrations."""
from sqlalchemy import text


def bound_migration(connection, *, lock_timeout_ms=5000, statement_timeout_ms=120000):
    # Never permit zero (PostgreSQL's unlimited setting), bools or arbitrary SQL.
    if (type(lock_timeout_ms) is not int or type(statement_timeout_ms) is not int
            or not 1 <= lock_timeout_ms <= 30000
            or not lock_timeout_ms <= statement_timeout_ms <= 600000):
        raise ValueError('Migration time limits must be bounded positive integers')
    if connection.dialect.name == 'postgresql':
        for name, value in [('lock_timeout', lock_timeout_ms),
                            ('statement_timeout', statement_timeout_ms)]:
            connection.execute(text('SELECT set_config(:name, :value, true)'),
                               {'name': name, 'value': f'{value}ms'})
