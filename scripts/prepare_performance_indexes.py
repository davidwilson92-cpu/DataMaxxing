"""Install only the two measured read-path indexes on an existing database.

PostgreSQL uses concurrent index creation outside a transaction. Runtime startup
does not rebuild existing tables. Run using the established migration identity.
"""
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if __name__ == '__main__':
    os.environ.setdefault('ZOVA_SCHEMA_MODE', 'verify')
from sqlalchemy.schema import CreateIndex
from sqlalchemy import inspect, text
from nova.db import Draft, ScheduledPost, engine

NAMES = {'ix_drafts_owner_brand_updated_id', 'ix_schedules_owner_brand_due_id'}


def prepare(database=engine):
    with database.connect().execution_options(isolation_level='AUTOCOMMIT') as connection:
        for model in (Draft, ScheduledPost):
            for index in model.__table__.indexes:
                if index.name not in NAMES:
                    continue
                concurrent = index.dialect_options['postgresql']['concurrently']
                try:
                    index.dialect_options['postgresql']['concurrently'] = database.dialect.name == 'postgresql'
                    connection.execute(CreateIndex(index, if_not_exists=True))
                finally:
                    index.dialect_options['postgresql']['concurrently'] = concurrent
                actual = next(item for item in inspect(connection).get_indexes(model.__tablename__)
                              if item['name'] == index.name)
                if actual['column_names'] != [column.name for column in index.columns] or actual['unique']:
                    raise RuntimeError('Existing performance index has an unexpected definition: ' + index.name)
                if database.dialect.name == 'postgresql':
                    valid = connection.scalar(text('SELECT indisvalid AND indisready FROM pg_catalog.pg_index '
                                                   'WHERE indexrelid = to_regclass(:name)'), {'name': index.name})
                    if valid is not True:
                        raise RuntimeError('Performance index requires operator repair: ' + index.name)
                print('Index ready:', index.name)


if __name__ == '__main__':
    prepare()
