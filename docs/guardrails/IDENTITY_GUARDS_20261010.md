# Immutable linked identities and issued-token authority

Validated eb26764: CI run 38011548983 passed 587 PostgreSQL tests (two expected
skips), 502 SQLite tests (87 expected skips), restored identity/account/workspace
guards, image build/smoke and Python dependency audit. Production remains unchanged
and the full release gate remains blocked.

Previous account-owner guards prevented changing user_id, but allowed changing the
provider subject or linked creator behind that owner, and rewriting an issued
token's identifier, expiry or authentication version. Consumed tokens could also
be changed back to unused. The regressions reproduce those changes before applying
the new migration, then require their rejection afterwards.

The identity migration protects five tables:

- zova_auth_identities: id, user_id, provider and subject.
- nova_user_creator_links: id, user_id and creator_id.
- zova_recovery_tokens: token_hash, user_id, auth_version and expires_at.
- zova_email_verifications: token_hash, user_id, email and expires_at.
- zova_mfa_challenges: token_hash, user_id, auth_version, destination and expires_at.

For the three consumable token tables, used can move from false to true but cannot
be reset afterwards. Normal conditional consumption, repeated no-op updates and
deletion/cleanup remain available. No new customer record values are written and
no credentials, password hashes, identity links or active sessions are rotated.
Changing an identity requires a separately authorised lifecycle operation, not
rewriting an existing identity record.

The explicit identities phase in scripts/migrate_workspaces.py provides read-only
planning and verification; applying requires migration credentials and paused
writes. The transaction uses bounded PostgreSQL waits and an advisory lock, or a
SQLite write transaction. It verifies required non-null columns, installs update
guards and records its version atomically. Repeating migration preserves records.

Fresh bootstrap and the explicit offline preparation command install the guards.
Populated ordinary bootstrap refuses missing guards before schema changes. Runtime
schema verification requires the migration version and exact guard definitions;
separated service setup checks the guards too. PostgreSQL checks function source,
language, security, search path and enabled all-column trigger shape. SQLite checks
complete normalized trigger definitions. Verification has no row-data dependency
or repair behavior.

Tests cover before/after direct SQL attacks for every protected identity field,
one-way token consumption and permitted deletion, repeat/preservation, interrupted
migration rollback, weakened guard definitions and runtime refusal. The MFA expiry
test now advances the test clock instead of rewriting an issued challenge's expiry.
The backup fixture contains an identity and checks reassignment rejection after
restore, alongside existing account/workspace policy checks.

Remaining: anonymous Apple authorization state, social pending-state claims,
billing/usage identity invariants, dedicated account lifecycle/service routing and
exact grants, runtime drift monitoring, production rehearsal and independent
review. These guards do not authorize insert/delete operations or prove that a
provider returned the correct identity; those are separate controls. Account RLS
remains an offline foundation until its service integration is complete.

Rollout must install this migration before starting this candidate. If verification
fails, keep writes paused and use the authorised maintenance path to diagnose and
forward-repair. Retain identity records, keys and all ownership protections; do not
disable triggers or restore old customer data as a code rollback. Never set an
offline preparation marker in the deployed application. No production migration,
configuration, grants, customer data or deployment changed during this increment.
