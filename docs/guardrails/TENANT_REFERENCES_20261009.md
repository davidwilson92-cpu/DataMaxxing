# Canonical references and database write guards

Candidate migration, not deployed. No production database has been altered. This completes the migration machinery for brand-owned references; application read scoping and PostgreSQL RLS remain the next integration work.

## Scope and invariants

The reviewed manifest covers all 16 current user_id/brand_id tables, including OAuth states and pending connection reviews. A new unclassified brand-owned table stops the migration for review. Account-level billing/security data and legacy creator-only objects require separate explicit mapping.

Each record receives workspace_id from the verified existing owner/brand pair. Existing IDs, content, credential bytes, upload locations and auth versions are untouched. Incorrect existing canonical references are rejected rather than repaired. Missing/invalid legacy ownership or registry mappings stop before any changes. Version: 20261009_workspace_references.

PostgreSQL uses foreign keys, non-null references and before-write triggers. SQLite uses transactional backfill plus before/after-write guards, including parent deletion protection even if a legacy client disables foreign_keys. Both reject cross-owner/brand inserts, immutable identity reassignment and workspace ID changes. Existing ORM inserts can omit the new field; the database fills the exact canonical mapping. Allowed content edits remain compatible.

These are integrity controls, NOT read isolation. They do not prove safe tenant reads, complete actor authorization, restricted-role deployment, RLS or operational assurance. Administrative DDL can still alter triggers; restricted service identities and deployment permissions must be completed before release.

## Controlled rollout

First run the registry migration on an isolated restored copy. Then run scripts/migrate_workspaces.py --phase references without --apply to inspect. Apply requires --phase references --apply --writes-paused after an actual pause of application and worker writes. Verify with --phase references --verify. Use ZOVA_MIGRATION_DATABASE_URL explicitly; never pass credentials in command arguments or copy them into evidence.

PostgreSQL holds a migration advisory lock and source/registry table locks during the backfill; SQLite explicitly includes DDL in the transaction. Repeated application verifies existing references and reinstalls the expected guards. Tests rehearse interruption rollback and prove no partial column backfill remains.

Before production: wire canonical read context/RLS and the complete fresh-install/migration path, rehearse all affected application/provider flows, validate restricted identities and measured recovery, and obtain required review. Do not apply this isolated increment to production while the full gate is red.

## Evidence and rollback

Tests attempt direct SQL identity changes, forged references, invalid owners, reassigned/deleted workspace mappings, interrupted migration, unexpected schema growth and old ORM insertion. A full application-schema rehearsal compares representative content, credentials, auth versions and media storage references. The same tests run against isolated SQLite and PostgreSQL schemas in CI.

Rollback preserves customer data and canonical mapping. Before activation, the additive columns/guards can stay with compatible older application code. After read isolation/role restrictions activate, do not remove tenant enforcement for a rollback; use a forward fix with writes/workers paused. Never restore an old database or replay uncertain publications merely to undo code.
