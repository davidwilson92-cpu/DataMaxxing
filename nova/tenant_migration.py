"""Offline, additive workspace registry migration. Does not enable team access or RLS.

No app imports: this module never starts services or applies unrelated migrations.
Run against an isolated copy first. Application/worker writes must be paused for apply.
"""
from __future__ import annotations

import uuid
from sqlalchemy import (MetaData, Table, Column, String, Integer, Boolean, ForeignKey,
                        UniqueConstraint, CheckConstraint, DateTime, select, func, literal, insert)

VERSION = '20261009_workspace_registry'
NAMESPACE = uuid.UUID('eae0f5dc-60ce-43f1-ab44-e69a532aef12')


class MappingError(ValueError):
    """Only table names/counts, never customer content, belong in this exception."""


def workspace_key(user_id, brand_id=0):
    return str(uuid.uuid5(NAMESPACE, f'user:{int(user_id)}:brand:{int(brand_id)}'))


def registry_tables(metadata):
    workspaces = Table('zova_workspaces', metadata,
        Column('id', String(36), primary_key=True),
        Column('owner_user_id', Integer, ForeignKey('nova_users.id'), nullable=False),
        Column('legacy_brand_id', Integer, nullable=False),
        UniqueConstraint('owner_user_id', 'legacy_brand_id'),
        CheckConstraint('legacy_brand_id >= 0', name='workspace_nonnegative_brand'))
    members = Table('zova_workspace_memberships', metadata,
        Column('workspace_id', String(36), ForeignKey('zova_workspaces.id'), primary_key=True),
        Column('user_id', Integer, ForeignKey('nova_users.id'), primary_key=True),
        Column('role', String(20), nullable=False),
        Column('active', Boolean, nullable=False),
        Column('revision', Integer, nullable=False),
        CheckConstraint("role IN ('owner','admin','publisher','creator','analyst','viewer')", name='membership_known_role'),
        CheckConstraint('revision >= 1', name='membership_positive_revision'))
    return workspaces, members


def _sources(connection):
    metadata = MetaData()
    metadata.reflect(bind=connection)
    if not {'nova_users', 'zova_brands'} <= set(metadata.tables):
        raise MappingError('Required identity tables are missing')
    return metadata


def inspect_mapping(connection):
    """Read-only aggregate preflight. Reject ambiguous ownership instead of guessing."""
    metadata = _sources(connection)
    users, brands = metadata.tables['nova_users'], metadata.tables['zova_brands']
    failures = []
    counts = {}
    if connection.scalar(select(func.count()).select_from(brands).where(brands.c.id <= 0)):
        failures.append('zova_brands: invalid nonpositive brand identity')
    for name, table in metadata.tables.items():
        if name in {'zova_workspaces', 'zova_workspace_memberships'} or 'user_id' not in table.c:
            continue
        counts[name] = connection.scalar(select(func.count()).select_from(table))
        orphan = connection.scalar(select(func.count()).select_from(table.outerjoin(users, table.c.user_id == users.c.id)).where(users.c.id.is_(None)))
        if orphan:
            failures.append(f'{name}: {orphan} records lack a valid owner')
        if 'brand_id' in table.c:
            invalid = connection.scalar(select(func.count()).select_from(table.outerjoin(brands,
                (table.c.brand_id == brands.c.id) & (table.c.user_id == brands.c.user_id)))
                .where((table.c.brand_id.is_(None)) | ((table.c.brand_id != 0) & brands.c.id.is_(None))))
            if invalid:
                failures.append(f'{name}: {invalid} records have invalid brand ownership')
    # Brand metadata uses user_id but is not itself BrandScoped.
    expected = connection.scalar(select(func.count()).select_from(users)) + connection.scalar(select(func.count()).select_from(brands))
    if failures:
        raise MappingError('; '.join(failures))
    return {'expected_workspaces': expected, 'source_table_counts': counts,
            'writes_performed': False, 'authorization_enforced': False}


def _pairs(connection, users, brands):
    yield from connection.execute(select(users.c.id, literal(0)))
    yield from connection.execute(select(brands.c.user_id, brands.c.id))


def verify_registry(connection):
    report = inspect_mapping(connection)
    metadata = _sources(connection)
    if not {'zova_workspaces', 'zova_workspace_memberships'} <= set(metadata.tables):
        raise MappingError('Workspace registry has not been created')
    users, brands = metadata.tables['nova_users'], metadata.tables['zova_brands']
    spaces, members = metadata.tables['zova_workspaces'], metadata.tables['zova_workspace_memberships']
    expected = {workspace_key(uid, bid):(uid, bid) for uid, bid in _pairs(connection, users, brands)}
    actual = {r.id:(r.owner_user_id, r.legacy_brand_id) for r in connection.execute(select(spaces))}
    if actual != expected:
        raise MappingError('Workspace registry does not match the verified owner mapping')
    for wid, (uid, _) in expected.items():
        member = connection.execute(select(members).where(members.c.workspace_id == wid, members.c.user_id == uid)).mappings().one_or_none()
        if not member or member['role'] != 'owner' or not member['active']:
            raise MappingError('Owner membership is missing, inactive or changed; no automatic privilege repair')
    # Stage one creates owners only. Additional memberships need a reviewed invitation rollout.
    if connection.scalar(select(func.count()).select_from(members)) != len(expected):
        raise MappingError('Unexpected membership exists before team-access rollout')
    return {**report, 'verified_workspaces': len(expected), 'verified_owner_memberships': len(expected)}


def apply_registry(engine, *, writes_paused=False):
    if not writes_paused:
        raise MappingError('Pause application and worker writes before applying this migration')
    with engine.begin() as connection:
        if connection.dialect.name == 'sqlite':
            # sqlite3 legacy transaction mode otherwise auto-commits CREATE TABLE.
            connection.exec_driver_sql('BEGIN IMMEDIATE')
        if connection.dialect.name == 'postgresql':
            from sqlalchemy import text
            connection.execute(text('SELECT pg_advisory_xact_lock(61009002)'))
            # Read-only preflight and backfill use a stable source while this lock is held.
            metadata = _sources(connection)
            for name in sorted(metadata.tables):
                table = metadata.tables[name]
                if 'user_id' in table.c or name == 'nova_users':
                    quoted = connection.dialect.identifier_preparer.quote(name)
                    connection.execute(text(f'LOCK TABLE {quoted} IN SHARE MODE'))
        before = inspect_mapping(connection)
        metadata = _sources(connection)
        users, brands = metadata.tables['nova_users'], metadata.tables['zova_brands']
        if 'zova_workspaces' in metadata.tables or 'zova_workspace_memberships' in metadata.tables:
            # Never silently repair a changed mapping or reinstate revoked permissions.
            verify_registry(connection)
            return {**before, 'already_applied': True}
        spaces, members = registry_tables(metadata)
        spaces.create(connection)
        members.create(connection)
        for uid, bid in _pairs(connection, users, brands):
            wid = workspace_key(uid, bid)
            connection.execute(insert(spaces).values(id=wid, owner_user_id=uid, legacy_brand_id=bid))
            connection.execute(insert(members).values(workspace_id=wid, user_id=uid, role='owner', active=True, revision=1))
        after = verify_registry(connection)
        if before['source_table_counts'] != after['source_table_counts']:
            raise MappingError('Source counts changed during migration')
        versions = metadata.tables.get('zova_schema_migrations')
        if versions is None:
            versions = Table('zova_schema_migrations', metadata, Column('version', String(100), primary_key=True), Column('applied_at', DateTime, nullable=False))
            versions.create(connection)
        connection.execute(insert(versions).values(version=VERSION, applied_at=func.current_timestamp()))
        return {**after, 'writes_performed': True, 'version': VERSION}
