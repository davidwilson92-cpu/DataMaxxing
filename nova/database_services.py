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


@dataclass(frozen=True)
class DatabaseServices:
    identity_sessions: object
    runtime_engine: object
    issuer_engine: object
    runtime_role: str

    def supports_request(self, method, path):
        if method in {'GET','HEAD'} and (path == '/health' or path.startswith('/static/')):
            return True
        return any(method == allowed_method and compile_path(route)[0].fullmatch(path)
                   for route,allowed_method in DRAFT_ROUTES)

    def request_session(self, request):
        from .brands import request_brand
        from .security import current_user
        route = getattr(request.scope.get('route'), 'path', request.url.path)
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


def create_services(identity_engine, runtime_engine, issuer_engine):
    """Verify existing identities; never create roles, grants, schema or credentials."""
    from .db import Base
    engines = (identity_engine, runtime_engine, issuer_engine)
    if len({id(engine) for engine in engines}) != 3:
        raise ValueError('Three separate service engines are required')
    details = []
    for engine in engines:
        if engine.dialect.name != 'postgresql' or not engine.hide_parameters or engine.echo:
            raise ValueError('Service pools require PostgreSQL with hidden parameters and SQL logging disabled')
        with engine.connect() as c:
            verify_runtime_role(c)
            details.append(c.execute(text('SELECT session_user,current_database(),current_schema(),inet_server_addr()::text,inet_server_port()')).one())
    roles = [row[0] for row in details]
    if len(set(roles)) != 3 or len({tuple(row[1:]) for row in details}) != 1:
        raise ValueError('Service identities must be distinct and use the same database and schema')
    with identity_engine.connect() as c:
        for left in roles:
            for right in roles:
                if left != right and c.scalar(text("SELECT pg_has_role(:left,:right,'MEMBER')"), {'left':left,'right':right}):
                    raise ValueError('Service identities must not inherit one another')
        # This pool validates existing sessions and rate limits only. It cannot
        # edit passwords/memberships, create users, or read customer content.
        schema=c.dialect.identifier_preparer.quote(details[0][2])
        q=c.dialect.identifier_preparer.quote
        for name in set(Base.metadata.tables) | {'zova_db_contexts','zova_schema_migrations'}:
            table=f'{schema}.{q(name)}'
            for operation in ('SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER'):
                allowed = (name in IDENTITY_READ_TABLES and operation == 'SELECT') or (
                    name == 'zova_request_limits' and operation in {'SELECT','INSERT','UPDATE','DELETE'})
                table_has=c.scalar(text('SELECT has_table_privilege(session_user,:table,:operation)'),{'table':table,'operation':operation})
                has=table_has
                # Include column grants: table-level checks alone miss them.
                if operation in {'SELECT','INSERT','UPDATE','REFERENCES'}:
                    has = has or c.scalar(text('SELECT has_any_column_privilege(session_user,:table,:operation)'),{'table':table,'operation':operation})
                if (allowed and not table_has) or (not allowed and has):
                    raise ValueError('Identity pool grants do not match the session-verification manifest')
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
    return DatabaseServices(sessionmaker(bind=identity_engine, expire_on_commit=False),
                            runtime_engine, issuer_engine, roles[1])
