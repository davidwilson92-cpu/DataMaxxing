# Account row isolation foundation

Validated 62dafb0: CI run 38010083098 passed 569 PostgreSQL tests
(two expected skips), 491 SQLite tests (80 expected skips), synthetic backup and
restore, image build/smoke and Python dependency audit. The full release gate
remains blocked with 80 unresolved entries; production is unchanged.

The regression fixture demonstrates unrestricted cross-account preference reads
with deliberately broad test grants before applying the new policies. The offline
migration adds forced row security to all 13 account tables. Unbound access is
denied; account.read requires the authenticated owner's default workspace context.
An account.edit context can modify only that owner's preferences and brands.
Security, billing, identity, membership and measurement writes are denied through
this role. Separate service authority for those operations remains unfinished.

Context checks reuse expiry, backend/transaction binding, login audience, current
membership and authentication-version verification. Secondary-brand contexts do
not confer personal account authority. The verifier compares complete function
definitions, execution grants, table flags, owner and all five policies per table.
Unexpected permissive policies cannot override restrictive row checks and are
also rejected by the manifest verifier.

The trusted migration owner is an explicit exception so existing security-definer
context functions can inspect memberships without recursive policy evaluation.
Policies supply CURRENT_USER themselves. Passing an invented actor directly to
the Boolean helper supplies no rows and cannot alter later policy evaluation.
Tests exercise this boundary and a non-superuser migration owner. Runtime roles
must not own the tables, inherit privileged roles or create schema objects.

The synthetic backup fixture includes both owners' preferences and account
policies. Restore verification checks their definitions, unbound denial and
owner-only access after obtaining a fresh transaction-bound context.

This is an offline foundation, not runtime integration. Existing authentication,
recovery, telemetry, registration, billing, callbacks and workers cannot simply be
switched to these policies. Exact operation/column grants, dedicated authorities,
secondary identity immutability, legacy isolation and full service integration
remain required. No production role, schema, data or application configuration was
changed. Shared-team account access is not enabled.

Forward recovery: keep writes paused if migration or verification fails. The
migration is transactional and bounded; diagnose in an isolated copy, retain
customer data and existing ownership protections, and rerun only with the trusted
migration identity. Never disable RLS or grant owner privileges to restore runtime
access. Do not activate this incomplete service model for customers. Production
rehearsal, external review and the complete release gate remain outstanding.

Validation history: run 38009344422 exposed a missing FOR UPDATE permission in
the synthetic non-superuser maintenance fixture. Run 38009736679 then exposed a
false-positive foreign INSERT test using a nonexistent timestamp column. The
fixture permission and SQL were corrected; the regression now requires SQLSTATE
42501 and an explicit row-security rejection. Final run 38010083098 passes both.
