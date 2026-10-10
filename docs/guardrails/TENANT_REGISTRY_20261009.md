# Canonical workspace registry — migration foundation

This is the first migration increment for guardrails 2/4/10/11/60. It is NOT an active authorization boundary, a completed team feature or production RLS. Do not deploy/apply it to production as an isolated change. The main application does not yet consult these tables.

## Mapping

Each existing user receives a default workspace; each owned brand receives a separate workspace. Workspace IDs are deterministic UUIDs derived from the existing owner/brand pair. Existing user IDs, brand IDs, URLs, credentials and content are untouched. Only owner memberships are backfilled. Six capability sets are defined with unknown roles/actions denied; enforcement comes in the next increment.

The preflight inventories all user_id tables and rejects missing owners and mismatched brand ownership. Legacy creator-only tables still need an explicit verified mapping and service identity. No ownership is inferred from an email, account name or provider username. A changed or inactive owner membership stops a repeat migration rather than escalating it back to owner.

## Apply procedure for an isolated copy

Use scripts/migrate_workspaces.py with ZOVA_MIGRATION_DATABASE_URL explicitly set to an isolated database. The script does not import the app or fall back to application credentials. Default mode is read-only. Apply requires --apply --writes-paused, following an actual pause of web/worker writes. PostgreSQL serializes the migration and holds source-table read locks; SQLite uses an explicit transaction to include schema rollback. Verify again with --verify.

Migration version: 20261009_workspace_registry. The migration creates zova_workspaces and zova_workspace_memberships plus the version record. Existing source rows are never updated. Compare aggregate source counts and a protected full-data checksum in the isolated recovery environment; never store customer content or credential hashes in public evidence.

## Test evidence

17 focused synthetic tests cover read-only inspection, two owners/default and named workspaces, preserved source bytes, repeat application, invalid owner/brand rejection, role constraints, revoked-owner refusal, unexpected memberships and rollback after an interrupted verification. The same tests use isolated PostgreSQL schemas in CI and SQLite locally. No production database is used.

## Next integration steps

1. Add workspace_id to every customer-owned record with deterministic backfill and referential constraints; reconcile legacy creators and account-level billing/security data explicitly.
2. Create/update registry entries transactionally during signup and brand creation; integrate erasure/export and backup restore.
3. Authorize every route and worker with verified membership plus the exact capability. Keep team invitations disabled until this is complete.
4. Separate migration/application/worker/admin identities; enable and adversarially test PostgreSQL RLS under restricted roles before rollout.
5. Rehearse migration, restore and forward recovery in an approved isolated staging environment. Required independent review and paid-staging deferral still apply.

## Rollback

Before activation, application behavior is unchanged and the additive registry may remain while code is rolled back. Do not restore an old customer database or delete customer data. After workspace references/RLS are activated, rollback must preserve tenant enforcement: use a reviewed forward fix, pause writes and reconcile jobs before any older worker is considered. Do not enable team access based solely on these role definitions.
