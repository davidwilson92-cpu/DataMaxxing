# Canonical workspace runtime integration

Candidate only; no production migration or deployment. This increment makes the tested reference migration part of the application's schema contract.

All 16 brand-owned ORM models map workspace_id, including OAuth states and pending connection confirmations. New records obtain the exact existing workspace from their owner/brand pair before insert. Forged or missing mappings fail; canonical identity changes fail before flush and database write guards enforce raw SQL immutability. Request-scoped content reads and aliases now filter by canonical workspace ID as well as the existing owner/brand checks. Signed OAuth state/confirmation paths retain their explicit authority checks and both Instagram routes.

Fresh installations create the schema then install reference guards before serving. Existing databases containing users must have verified references and the migration version before startup. No customer backfill or privilege repair happens during application startup. SQLite's legacy insertion compatibility uses nullable physical columns plus triggers; PostgreSQL installs NOT NULL constraints.

## Validation and remaining boundaries

Tests cover mapped model coverage, canonical filtered/aliased reads, cross-customer/brand lookup refusal, forged inserts, ORM and direct database reassignment, fresh startup/restart, missing migration refusal, and offline upgrade preserving password hash, auth version and draft content. Existing adversarial worker/reconciliation/allowance fixtures now create real separate brands rather than invalid brand IDs, preserving their original boundary assertions. At dc55d2b, local and CI SQLite: 398 passed / 6 expected skips; PostgreSQL: 403 passed / 1 expected skip. Both CI runs (37988211823 / 37988205275) passed application, migrated restore, hosting build/smoke and dependency checks. Provider tests are mocked. Evidence: evidence/canonical-runtime-20261009.json.

This does not finish database read isolation. Raw SQL, unscoped worker sessions and deliberate server-side all-brand operations still require restricted PostgreSQL roles/RLS and validated transaction context. Shared teams, account-level objects and legacy creator authority remain unfinished. Do not mark tenant isolation or the release gate complete.

## Rollout and recovery

Rehearse registry and reference phases on an isolated restored copy, then validate runtime journeys and backup restoration. Production requires an actual maintenance window with application/worker writes paused, verified mappings, all required guardrail evidence and approval already given for publishing. Never deploy this candidate before migrating an existing database: startup deliberately refuses it. Preserve additive columns, registry, memberships and completed/unknown publication outcomes. Use a forward fix retaining MFA and membership enforcement; do not restore old customer data or replay uncertain posts. No paid staging has been provisioned.
