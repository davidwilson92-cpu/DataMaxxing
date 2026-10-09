# Protected content transaction integration

Candidate only. `nova/workspace_session.py` is an opt-in factory, not a change to
the shared production `SessionLocal`. Validated at 5ac264d: 409 SQLite / 431 PostgreSQL tests passed; expected skips 23 / 1. CI runs 37993492489 and 37993486479 also passed migrated restore, hosting build/smoke and dependency checks. See evidence/workspace-sessions-20261009.json. Production remains blocked.

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
and maintenance; verify active policies and exact grants at startup. Draft deletion cleanup is now verified; reconcile the remaining compound operations
and exact service/column grants. Do not globally enable policies until
those paths pass. No production credentials, roles or data have been changed.

Rollback before activation is code-only. After future policy activation, preserve
the policies and use forward recovery; do not restore unprotected credentials or
drop customer records to recover an application failure.


## Brand and deletion compatibility follow-up

Validated cc70b7d: local/CI SQLite 410 passed / 25 expected skips; PostgreSQL
434 passed / one expected skip. Runs 37994384382 and 37994380750 also passed
migrated RLS restore, hosting image build/smoke and dependency audit.
Evidence: evidence/draft-policy-20261009.json.

The content factory explicitly installs existing brand ownership hooks, including
for entry points that have not imported the web app. Existing draft HTTP handlers
now have default- and second-brand integration coverage for create/save/reload,
canonical mapping and isolation from the same owner's other brand.

The old review-delete policy was restored in an isolated test to reproduce the
foreign-key failure during unsubmitted draft deletion. Reapplying the corrected
policies allows the existing service to remove the review, dismiss the strategy
action and cancel its occurrence atomically. Other workspaces and delivery
history remain intact. The added posts.delete permission applies only to review
DELETE and strategy-action/occurrence UPDATE, not their other mutations. Exact
column-level service grants remain open; this is not a claim of complete least
privilege. Policies still apply live membership and canonical workspace checks.
No production policy, grants, data, provider state or deployment changed.
