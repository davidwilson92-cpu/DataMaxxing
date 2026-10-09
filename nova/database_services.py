"""Explicit service-pool integration; staged routes only, never a credential fallback.

No production startup activation yet. Install on app.state.database_services only
after provisioning and verifying separate identities. Unmapped get_db routes fail
closed until their account, callback or worker authority has been implemented.
"""
from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from starlette.routing import compile_path

from .schema_startup import verify_runtime_role
from .tenant_access import WorkspaceDenied
from .workspace_session import authenticated_authority, content_session


DRAFT_ROUTES = {
    ('/api/drafts', 'GET'): 'posts.read',
    ('/api/drafts', 'POST'): 'posts.create',
    ('/api/drafts/{draft_id}', 'GET'): 'posts.read',
    ('/api/drafts/{draft_id}', 'PATCH'): 'posts.edit',
    ('/api/drafts/{draft_id}', 'DELETE'): 'posts.delete',
}
IDENTITY_READ_TABLES = frozenset({'nova_users', 'zova_revoked_sessions', 'zova_brands',
                                'zova_workspaces', 'zova_workspace_memberships'})
AUTH_ROUTES = {('/login','GET'),('/login','POST'),('/logout','POST'),
               ('/mfa/challenge','GET'),('/mfa/challenge','POST'),
               ('/mfa/setup','GET'),('/mfa/setup','POST'),('/mfa/enable','POST'),('/mfa/disable','POST')}
AUTH_TABLE_GRANTS = {
    'nova_users': {'SELECT'},
    'zova_revoked_sessions': {'SELECT','INSERT'},
    'zova_mfa_settings': {'SELECT','INSERT','UPDATE'},
    'zova_mfa_challenges': {'SELECT','INSERT','UPDATE','DELETE'},
}
AUTH_COLUMN_GRANTS = {('nova_users','UPDATE'): {'last_login_at','auth_version','updated_at'}}


@dataclass(frozen=True)
class DatabaseServices:
    identity_sessions: object
    runtime_engine: object
    issuer_engine: object
    runtime_role: str
    authentication_sessions: object = None

    def supports_request(self, method, path):
        if method in {'GET','HEAD'} and (path == '/health' or path.startswith('/static/')):
            return True
        if self.authentication_sessions is not None and (path,method) in AUTH_ROUTES:
            return True
        return any(method == allowed_method and compile_path(route)[0].fullmatch(path)
                   for route,allowed_method in DRAFT_ROUTES)

    def request_session(self, request):
        from .brands import request_brand
        from .security import current_user
        route = getattr(request.scope.get('route'), 'path', request.url.path)
        if self.authentication_sessions is not None and (route,request.method) in AUTH_ROUTES:
            with self.authentication_sessions() as auth:
                yield auth
            return
        capability = DRAFT_ROUTES.get((route, request.method))
        if capability is None:
            raise HTTPException(503, 'This service is not available during database migration.')
        user = current_user(request)
        try:
            with self.identity_sessions() as auth:
                brand_id = request_brand(auth, request, user)
                authority = authenticated_authority(auth, user, brand_id, capability)
            request.state.brand_id = brand_id
            request.state.workspace_id = authority.workspace_id
            with content_session(self.runtime_engine, self.issuer_engine, authority,
                                 runtime_role=self.runtime_role) as db:
                yield db
        except WorkspaceDenied:
            raise HTTPException(403, 'Workspace access is unavailable. Sign in again.') from None


def identity_factory(request):
    services = getattr(request.app.state, 'database_services', None)
    return services.identity_sessions if services is not None else None


def authentication_factory(request):
    services = getattr(request.app.state, 'database_services', None)
    if services is not None and services.authentication_sessions is None:
        raise HTTPException(503, 'Authentication is not available during database migration.')
    return services.authentication_sessions if services is not None else None


def verify_pool_grants(c, metadata, table_grants, column_grants=None):
    """Reject excess and missing table/column privileges for a service pool."""
    column_grants = column_grants or {}
    schema=c.dialect.identifier_preparer.quote(c.scalar(text('SELECT current_schema()')))
    q=c.dialect.identifier_preparer.quote
    for name in set(metadata.tables) | {'zova_db_contexts','zova_schema_migrations'}:
        table=f'{schema}.{q(name)}'
        for operation in ('SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER'):
            table_has=c.scalar(text('SELECT has_table_privilege(session_user,:table,:operation)'),{'table':table,'operation':operation})
            if operation in table_grants.get(name,set()):
                if not table_has:raise ValueError('Service pool grants do not match the manifest')
                continue
            if table_has:raise ValueError('Service pool grants do not match the manifest')
            if operation in {'SELECT','INSERT','UPDATE','REFERENCES'}:
                columns=set(c.scalars(text('''SELECT attname FROM pg_attribute
                    WHERE attrelid=CAST(:table AS regclass) AND attnum>0 AND NOT attisdropped
                    AND has_column_privilege(session_user,attrelid,attname,:operation)'''),
                    {'table':table,'operation':operation}))
                if columns != column_grants.get((name,operation),set()):
                    raise ValueError('Service pool column grants do not match the manifest')


def create_services(identity_engine, runtime_engine, issuer_engine, *, authentication_engine=None):
    """Verify existing identities; never create roles, grants, schema or credentials."""
    from .db import Base
    engines = (identity_engine, runtime_engine, issuer_engine)
    if authentication_engine is not None:engines += (authentication_engine,)
    if len({id(engine) for engine in engines}) != len(engines):
        raise ValueError(('Three' if len(engines)==3 else 'Four')+' separate service engines are required')
    details = []
    for engine in engines:
        if engine.dialect.name != 'postgresql' or not engine.hide_parameters or engine.echo:
            raise ValueError('Service pools require PostgreSQL with hidden parameters and SQL logging disabled')
        with engine.connect() as c:
            verify_runtime_role(c)
            details.append(c.execute(text('SELECT session_user,current_database(),current_schema(),inet_server_addr()::text,inet_server_port()')).one())
    roles = [row[0] for row in details]
    if len(set(roles)) != len(engines) or len({tuple(row[1:]) for row in details}) != 1:
        raise ValueError('Service identities must be distinct and use the same database and schema')
    with identity_engine.connect() as c:
        for left in roles:
            for right in roles:
                if left != right and c.scalar(text("SELECT pg_has_role(:left,:right,'MEMBER')"), {'left':left,'right':right}):
                    raise ValueError('Service identities must not inherit one another')
        # This pool validates existing sessions and rate limits only. It cannot
        # edit passwords/memberships, create users, or read customer content.
        schema=c.dialect.identifier_preparer.quote(details[0][2])
        identity_grants={name:{'SELECT'} for name in IDENTITY_READ_TABLES}
        identity_grants['zova_request_limits']={'SELECT','INSERT','UPDATE','DELETE'}
        verify_pool_grants(c,Base.metadata,identity_grants)
        signatures = {
            'issue': f'{schema}.zova_issue_context(text,integer,text,integer,integer,text,text,integer,text,integer)',
            'resolve': f'{schema}.zova_rls_workspace(text[])',
        }
        for index,role in enumerate(roles):
            for purpose,signature in signatures.items():
                expected = (index == 2 and purpose == 'issue') or (index == 1 and purpose == 'resolve')
                execute=c.scalar(text("SELECT has_function_privilege(:role,:signature,'EXECUTE')"),
                                 {'role':role,'signature':signature})
                owns=c.scalar(text("SELECT pg_has_role(:role,p.proowner,'MEMBER') FROM pg_proc p WHERE p.oid=CAST(:signature AS regprocedure)"),
                              {'role':role,'signature':signature})
                if bool(execute) != expected or owns:
                    raise ValueError('Context functions must remain owned and granted to separate service identities')
    if authentication_engine is not None:
        with authentication_engine.connect() as c:
            verify_pool_grants(c,Base.metadata,AUTH_TABLE_GRANTS,AUTH_COLUMN_GRANTS)
    return DatabaseServices(sessionmaker(bind=identity_engine, expire_on_commit=False),
                            runtime_engine, issuer_engine, roles[1],
                            sessionmaker(bind=authentication_engine,expire_on_commit=False) if authentication_engine is not None else None)
