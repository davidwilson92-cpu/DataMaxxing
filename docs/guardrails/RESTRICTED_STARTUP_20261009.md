# Restricted runtime startup

Candidate only. No production roles, credentials, data or hosting settings were changed.

## Separation

PostgreSQL now defaults to ZOVA_SCHEMA_MODE=verify. The web/worker model import only reads schema metadata and migration versions; it never runs CREATE/ALTER/backfill. It rejects missing tables/columns/versions, missing or disabled ownership triggers, and incomplete PostgreSQL canonical foreign-key/non-null constraints. It checks both current_user and session_user so switching away from a privileged login cannot hide the ability to RESET ROLE.

Runtime credentials must not have administrative role attributes, database ownership, membership in a built-in broad-access or administrative/table-owning role, schema CREATE or table TRUNCATE permissions. Both the current and original session identities are checked. The candidate blueprint explicitly sets verify. This does not prove the live host uses the blueprint or that complete least-privilege/RLS is deployed.

Schema preparation is explicit and offline: scripts/prepare_database.py --apply --writes-paused requires ZOVA_MIGRATION_DATABASE_URL, never falls back to the running application's credentials, and prints no credential/customer contents. Existing populated databases must first pass the separate registry/reference migration. SQLite defaults to bootstrap for disposable local/test setups; it can also use verify. Isolated CI explicitly bootstraps using its migration identity. Do not put migration credentials or bootstrap mode on runtime web/worker services.

## Validation scope

Tests check read-only verification, missing/disabled guards, missing columns/tables/version refusal without repair, empty verify startup, and explicit offline preparation. A PostgreSQL-only test creates a temporary restricted login in a loopback synthetic database, runs an actual application import and authenticated draft read, and attacks schema alteration, guard disabling, drop/truncate/create and migration-version deletion. It also tests privileged-login masking and excess schema permissions. CI validation pending for this increment.

This only removes schema-administration capability. The test DML grants intentionally exercise current compatible runtime behavior; they are NOT a final production privilege manifest. Tenant RLS, separate application/worker/auth/analytics identities, per-table and per-operation grants, account-level/legacy authority mapping and revocation races remain unfinished. Do not mark database isolation complete.

## Rollout and recovery

Continue isolated migration, backup/restore and application rehearsals before a maintenance window. Review and provision separate migration and runtime credentials only after the full required evidence is ready. Keep customer data, encryption/session keys and old IDs unchanged. The runtime must reject a missing migration or overprivileged identity rather than repairing it at startup. Production cannot use this candidate until the credential/schema prerequisites and complete release gate pass.

If verification fails, restore correct permissions or forward-fix the schema under the maintenance procedure. Do not grant broad privileges or disable verification to make the app start. Keep the additive data and existing MFA/membership safeguards. This increment does not change billing, provider grants or publishing approval.
