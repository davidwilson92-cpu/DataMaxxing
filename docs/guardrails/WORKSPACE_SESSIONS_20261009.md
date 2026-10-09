# Protected content transaction integration

Candidate only. `nova/workspace_session.py` is an opt-in factory, not a change to
the shared production `SessionLocal`. PostgreSQL CI validation is pending.

Authority is frozen for the lifetime of one request. The authentication database
checks the authenticated user's original security version, current active
membership, canonical owner workspace and capability. A revocation cannot be
silently upgraded to a fresh version. Every new outer SQLAlchemy transaction
obtains a newly issued context through separate issuer credentials, including a
refresh after commit or recovery after rollback. Savepoints keep the enclosing
transaction's authority. Engines must hide parameters and disable SQL echo.

`Session.get` always consults database policies rather than returning a cached
identity. Policies continue to check live membership/security versions on every
statement. Previously returned Python values cannot be recalled; these sessions
must remain request-scoped and must never be shared between users/workspaces.
Callers must close or roll back after errors. The factory does not retry with
stronger credentials or refresh stale authority.

Tests cover commit/refresh, rollback, savepoints, cached identity revocation,
pool reuse, cross-owner reads and stale authenticated versions. An isolated HTTP
test drives the existing create/save/read/list draft handlers, conversation and
Instagram Story persistence, optimistic revision conflicts and revoked access.
Its authentication pool uses fixture administrator credentials; readiness
telemetry is mocked because account-pool integration is not complete. This is
not an end-to-end production credential or worker validation.

Remaining before activation: route the web dependencies through independently
restricted authentication/account and content pools; map signed OAuth callbacks,
billing webhooks, legacy API identities, account telemetry, worker claim/recovery
and maintenance; verify active policies and exact grants at startup. Current
RLS permissions must be reconciled with cross-table operations such as deleting
a draft and dismissing its strategy action. Do not globally enable policies until
those paths pass. No production credentials, roles or data have been changed.

Rollback before activation is code-only. After future policy activation, preserve
the policies and use forward recovery; do not restore unprotected credentials or
drop customer records to recover an application failure.
