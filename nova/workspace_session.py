"""Opt-in content sessions for the isolated PostgreSQL RLS rollout.

Not wired to the shared account/OAuth/worker SessionLocal. Authority is derived
using the authentication pool; content transactions use restricted credentials.
"""
from dataclasses import dataclass

from sqlalchemy import event, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .capabilities import permits
from .rls import bind_context, issue_context
from .tenant_access import WorkspaceDenied
from .tenant_migration import workspace_key


@dataclass(frozen=True)
class WorkspaceAuthority:
    user_id: int
    brand_id: int
    workspace_id: str
    auth_version: int
    membership_revision: int
    capability: str


def authenticated_authority(auth_db, authenticated_user, brand_id, capability):
    """Use a user returned by validated authentication, never request claims.

    Preserve its validated auth_version: loading the latest version and silently
    upgrading it would let a concurrent session revocation be bypassed.
    """
    from .db import User, TenantWorkspace, WorkspaceMembership
    if type(brand_id) is not int or brand_id < 0:
        raise WorkspaceDenied('Workspace access is unavailable.')
    uid, version = authenticated_user.id, authenticated_user.auth_version
    wid = workspace_key(uid, brand_id)
    row = auth_db.execute(select(WorkspaceMembership.role, WorkspaceMembership.revision)
        .join(TenantWorkspace, TenantWorkspace.id == WorkspaceMembership.workspace_id)
        .join(User, User.id == WorkspaceMembership.user_id)
        .where(TenantWorkspace.id == wid, TenantWorkspace.owner_user_id == uid,
               TenantWorkspace.legacy_brand_id == brand_id,
               WorkspaceMembership.user_id == uid, WorkspaceMembership.active.is_(True),
               User.active.is_(True), User.auth_version == version)).first()
    if not row or not permits(row.role, capability):
        raise WorkspaceDenied('Workspace access is unavailable.')
    return WorkspaceAuthority(uid, brand_id, wid, version, row.revision, capability)


class WorkspaceSession(Session):
    def get(self, entity, ident, **kwargs):
        # A cached Session.get must still consult current database policy. Already
        # returned Python values cannot be recalled; sessions are request-scoped.
        kwargs['populate_existing'] = True
        return super().get(entity, ident, **kwargs)


def content_session(runtime_engine, issuer_engine, authority, *, runtime_role):
    """Create one request's session; never switch its authority or share it.

    Every outer transaction gets a fresh bound context, including refresh after
    commit. Expired/revoked claims are not upgraded or retried with stronger ones.
    Nested savepoints share the outer transaction's authority.
    """
    if not isinstance(authority, WorkspaceAuthority):
        raise ValueError('Validated workspace authority is required')
    if runtime_engine is issuer_engine or not runtime_role:
        raise ValueError('Separate runtime and issuer engines are required')
    for engine in (runtime_engine, issuer_engine):
        if engine.dialect.name != 'postgresql' or not engine.hide_parameters or engine.echo:
            raise ValueError('Protected sessions require PostgreSQL with hidden parameters and SQL logging disabled')
    db = WorkspaceSession(bind=runtime_engine, expire_on_commit=True,
                          info={'brand_id': authority.brand_id, 'brand_user_id': authority.user_id,
                                'workspace_id': authority.workspace_id})

    @event.listens_for(db, 'after_begin')
    def bind_transaction(session, transaction, connection):
        if transaction.nested:
            return
        try:
            token = issue_context(issuer_engine, connection, user_id=authority.user_id,
                workspace_id=authority.workspace_id, auth_version=authority.auth_version,
                membership_revision=authority.membership_revision, capability=authority.capability,
                runtime_role=runtime_role)
            bind_context(connection, token)
        except (SQLAlchemyError, RuntimeError):
            # Context and credential diagnostics stay out of application errors.
            # Rollback/close remains the caller's responsibility, as with Session.
            raise WorkspaceDenied('Workspace access could not be verified. Sign in again.') from None

    return db
