# Immutable account ownership migration

Candidate only; full SQLite/PostgreSQL and restore validation pending. No production
schema, grants, data, roles or deployment changed.

The existing account foreign keys prevent nonexistent owners in PostgreSQL but
do not prevent reassignment to another valid user. Synthetic regressions reproduce
that direct-SQL reassignment on all 13 account-owned model tables before migration,
then verify rejection afterwards. This is an ownership invariant, not a claim of
account-level row security or authorization for every insert/read/delete.

`nova/account_references.py` explicitly classifies preferences, usage, recovery,
external login identities, legacy creator links, billing accounts, AI/product
measurement, email verification, MFA settings/challenges, brands and memberships.
The existing 16 brand-owned tables retain their separate workspace guards. Private
database-context records remain under their separate issuer/function controls.
Unclassified user-owned tables stop migration until reviewed.

Offline phase `accounts` in `scripts/migrate_workspaces.py` provides a read-only
plan by default. Apply requires explicit migration credentials plus
`--apply --writes-paused`. PostgreSQL takes bounded advisory/table locks, validates
existing ownership, preserves all row values, ensures user foreign keys/non-null
owners and installs a BEFORE UPDATE ownership guard. Anonymous AI calls may retain
a null owner, but cannot later be assigned to an account. SQLite has equivalent
insert/update/parent-delete checks even when a client disables foreign keys.

`--verify` checks ownership and installed guards; PostgreSQL additionally compares
the function body/security/search path and trigger shape to the migration source.
SQLite currently checks guard presence, not complete definition integrity. The
versioned migration is transactional and repeatable. It never repairs ambiguous
ownership or re-enables membership. Existing field updates, revocation and privacy
erasure remain supported. Production startup does not install this migration.

Tests explicitly install guards before the full disposable application suite, and
restricted PostgreSQL service fixtures install them before role tests. Migration
tests cover plan/repeat preservation, rollback, unknown tables, null/orphan owners,
parent deletion, anonymous telemetry and removed-guard detection. CI restore
rehearsal includes the migrated account records/guards and rejects reassignment
after restore.

Remaining: account-level read/delete/insert authorization, immutable secondary
identity fields, legacy-creator isolation, restricted registration/callback/worker
services, production startup enforcement, full constraint/SQLite definition
attestation and real deployment review. This migration does not expand service
grants or activate partial separated-service routing.

Rollback: application and workers must be paused for migration, with a verified
backup and isolated rehearsal first. Failures roll back the migration transaction.
If production rollout is later authorized, retain immutable ownership and existing
data; use a compatible forward fix. Do not restore an old customer database or
permit ownership transfers to work around a rejected write.
