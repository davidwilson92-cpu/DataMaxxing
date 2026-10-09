# Staged service-pool request integration

Candidate only; not configured or enabled in production. PostgreSQL validation
is pending. This increment connects the real `get_db`, `current_user` and request
rate-limit paths to the previously tested protected content sessions.

`create_services` verifies three existing PostgreSQL identities using separate
parameter-hidden engines. They must address the same database/schema, have
distinct logins, lack administrative/owner/destructive privileges, and not be
members of one another. The session-verification identity has SELECT on users,
revoked sessions, brands, workspaces and memberships, and DML on request-limit
records. It has no content or authority mutation grants. Unexpected column grants
are also rejected. Issuing/resolving context function permissions are separated;
service identities cannot own these functions. This does not certify every
content/worker column grant or the installed policy/function definitions.

Configured services are installed through trusted application state, never
request parameters. There is deliberately no production environment activation
switch yet. The current allowlist covers draft create/list/read/update/delete,
health and static assets only. Both middleware and the database dependency reject
unmapped routes; this includes handlers that do not use `get_db`. Existing mode
is unchanged when services are absent. Do not enable this partial mode on the
customer-facing application: sign-in/signup, account, OAuth, publishing and other
routes still need complete authority mappings. Workers/direct session entry
points are not integrated or certified by these web checks.

Existing signed cookies are verified against the restricted identity pool,
including auth-version and individual-session revocation. The validated version
is preserved when deriving immutable workspace authority. Explicit foreign brand
selection returns not-found; a stale foreign brand cookie falls back to the
user's default brand, matching existing behavior. Normal middleware rate limits
use the identity pool, without selecting content credentials as a fallback.

The PostgreSQL tests provision disposable service roles and exercise the real
request dependency without dependency overrides or an administrator auth pool.
They cover default/second-brand save/reload/delete, foreign IDs, stale cookies,
session revocation, rate-limit persistence, unmapped-route rejection and grant
attacks. Readiness telemetry remains mocked and unintegrated. Live providers,
customer accounts, production roles and production schema are not touched.

Next: mapped authentication/account mutation services, telemetry, signed callback
brokers, worker claims/recovery and legacy identities; verify exact installed RLS
definitions and final service grants; only then provide validated deployment
configuration. Preserve explicit publishing confirmation and unknown outcomes.
Before activation, rollback is code-only. After future activation, keep policy
and session-revocation protections and use forward recovery rather than shared
privileged credentials or restoring older customer data.
