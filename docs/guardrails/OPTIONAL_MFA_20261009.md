# Optional MFA integration — 9 October 2026

Candidate only. No deployment, real-account enrollment, grant, charge or social publication.
Owner authorised optional authenticator setup; mandatory enrollment remains deferred.

## Changes

- Account links to optional two-step sign-in. Setup requires the current password and a working six-digit TOTP before enabling protection.
- Encrypted authenticator secret, ten hashed one-use recovery codes, expiring account/version-bound login challenges, shared database rate limiting and atomic replay protection.
- Enabling/disabling revokes other sessions. Password reset does not remove MFA. Password and Apple sign-in both enforce it; concurrent security changes prevent session issuance.
- Apple new-user request handling, verified-email linking and inactive-account rejection corrected.
- MFA secrets excluded from export, removed during assisted erasure, and secret pages use no-store/no-referrer.
- Versioned additive migration 20261009_optional_mfa creates two empty tables. No user backfill or enrollment. Readiness and synthetic restore include both tables.
- Integrated previously tested UX candidate with queued publication/private-media guardrails. Preserved legacy-password login while retaining 15-character minimum for new passwords. Isolated schedule-window test fixtures so their 100-job backlog cannot affect worker-boundary tests.

## Validation and limits

See evidence/optional-mfa-20261009.json for actual test results. Synthetic accounts and mocked external providers only. Register integrity is not production approval. Source-review attestation remains unset. All 79 sections retain their unresolved status until complete evidence exists.

Manual authenticator entry is supported; QR setup, recovery-code regeneration, a verified support recovery procedure, privileged mandatory MFA, independent security review and deployed browser/provider acceptance remain outstanding. No claim of complete MFA or whole-product guardrail compliance.

## Rollout and rollback

Before rollout: PostgreSQL migration/restore and image CI, independent security review, synthetic desktop/mobile keyboard journey and verified recovery operations. Preserve existing encryption/session keys. Run migration with one controlled migration owner before starting workers; application-import migrations remain a separate baseline gap.

Never roll back to code that ignores MFA after any account enables it. Keep MFA-aware authentication and both tables, or deploy a forward fix; pause sign-ins if safe authentication cannot be restored. Do not disable customer MFA or restore old data as a rollback shortcut. Test backups with the same encryption key in an isolated environment. Retain queued-publication and private-media rollback requirements in ITERATION_PROCESS.md.

## Remaining release blockers

Canonical tenancy/membership and database RLS; privileged roles/MFA; independent staging (paid provisioning remains deferred); worker operations, global publishing pause and provider quotas; immutable audit; private storage assurance; recovery/load/accessibility/security/legal review evidence. No gate bypass or production certification.
