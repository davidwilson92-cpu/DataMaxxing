# Workspace membership enforcement — 9 October 2026

Candidate only. No production migration or deployment. Builds on TENANT_REGISTRY_20261009.md; the earlier registry-only status is historical for the migration foundation.

## Active behavior in this candidate

New users and brands receive canonical workspace and owner membership rows in the same database transaction. New non-owner memberships default to inactive viewer access. Existing databases without a registry refuse application startup: run the reviewed offline backfill on an isolated copy, validate it, then perform a separately controlled migration before rollout.

Current owner-scoped content/API, social connection and billing paths consult current membership/capabilities server-side. Unknown new API mutations deny access until explicitly classified. Billing checks the default account workspace; brand renaming checks the actual target. Existing object ownership checks remain in force. Missing, inactive or wrong-workspace memberships are never silently repaired. Personal authentication/recovery routes remain available.

Role/active changes through the ORM increment membership revision and account auth_version, revoking previous sessions. Workspace/membership identity changes through ORM are rejected. Studio queued publishing and older scheduled jobs recheck current publishing permission before provider dispatch. An already in-flight provider request cannot be recalled. Direct SQL privilege changes and a unified race-safe mutation service still require the upcoming database constraints/RLS/audit work.

Assisted erasure deactivates memberships before deleting content. Export includes role/active/workspace ID only. Schema readiness and synthetic backup restore include both registry tables.

## Validation

Tests cover atomic account/brand creation and rollback, two-owner isolation, every role's draft/create/publish authorization, revoked sessions, fresh-login refusal after revocation, missing-membership refusal, uncached permission reads, queued publication revocation, identity mutation rejection, explicit classification of current API mutations, unknown-route denial and safe membership defaults. Existing customer/reviewer journeys are exercised by the full regression suite with mocked providers.

## Still incomplete

This is enforcement for existing owner-scoped workflows, not complete collaborative-team support. Shared-member routing, invitations, ownership transfer, actor attribution, legacy creator authority consolidation, workspace_id on all customer data and PostgreSQL RLS/restricted identities remain outstanding. Do not advertise team sharing or mark guardrails 2/4/60 complete. Internal operator paths still need separate staff identity and mandatory MFA. Full browser accessibility and independent security review are outstanding.

## Rollout and rollback

Run offline registry preflight/backfill/verification against a restored isolated copy first. Existing production data has not been migrated. Preserve all old IDs, credentials, auth keys, drafts and publishing ledgers. Confirm every expected owner mapping and membership without exposing customer content in evidence.

Do not roll back to code that ignores membership revocation after changing permissions. Retain membership enforcement and MFA-aware authentication or deploy a forward fix. Pause writes/workers before schema rollout; reconcile pending/unknown sends and never replay unknown outcomes. Keep additive registry tables; restoring old customer data is not a code rollback.
