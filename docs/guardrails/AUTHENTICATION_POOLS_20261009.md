# Restricted authentication service integration

Candidate only, not production-enabled. Validated at a9dd94b: CI SQLite 412 passed / 31 expected skips; PostgreSQL
442 passed / one expected skip. Runs 37997449697 / 37997443303 passed migrated
RLS restore, hosting image build/smoke and dependency audit. Evidence:
`evidence/authentication-pools-20261009.json`.

The optional fourth engine in `create_services` supplies a distinct authentication
identity. It can read users and revoked sessions, insert revocations, read/insert/
update MFA settings, and manage MFA challenges. User writes are column grants for
`last_login_at`, `auth_version` and `updated_at` only. Password, email, active flag,
workspace membership, content access and MFA-settings deletion are not granted.
The common startup verifier checks every declared table/column permission,
rejects excess grants and keeps all service roles separate from context issuance.
It does not provision or alter roles.

When this fourth service is supplied, staged routing also admits password sign-in,
the sign-in page, optional MFA setup/enable/disable and challenge completion, and
logout. Their database dependency uses the authentication pool. Cookie issuance
and revocation verification use the read-only identity pool; factor rate limits
use its request-limit permission. None should fall back to shared credentials.
With no configured services, the existing application behavior is preserved.

Existing password-only users are not enrolled. MFA still requires the user's
explicit setup and valid confirmation code. Existing encrypted secret storage,
hashed one-use recovery codes, replay rejection, expected security-version checks
and session revocation are retained. MFA enable/disable increments the security
version. Logout stores the session hash rather than changing other sessions.

The authentication service is trusted to operate across account authentication
records. This increment limits its database privileges; it does not establish
account-level RLS or an independent authentication microservice. Endpoint ownership
checks and tests remain essential. Password reset/change, account creation,
Apple sign-in, account lifecycle, callbacks, telemetry and workers are not yet
mapped in the staged mode, and unmapped routes remain unavailable. Do not enable
this partial mode for customers or claim complete authentication rollout.

Validation covers existing password sign-in, opt-in enrollment, MFA challenge,
concurrent recovery-code consumption, disabling MFA and logout, with the old
shared factories set to fail if reached. It also covers authentication-role
attacks on passwords, email, active state, membership, content and MFA deletion,
and rejects an extra password-column grant. Production users, credentials,
provider grants and posts are untouched. Deployment, browser MFA usability and
operational recovery assurance remain separate requirements.

Before activation this change can be rolled back as code. After enrollment is
enabled, never roll back to MFA-unaware authentication. Preserve existing secrets,
recovery hashes, revocations and auth versions, and use compatible forward fixes.
