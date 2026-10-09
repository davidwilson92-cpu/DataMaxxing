# Password change and recovery integration

Candidate only; no production activation. Validated at 212794e: CI SQLite
415 passed / 32 expected skips; PostgreSQL 446 passed / one expected skip. Runs
37998910309 / 37998904763 also passed migrated RLS restore, image build/smoke
and dependency audit. Evidence: `evidence/recovery-pools-20261009.json`.

Password change now preserves the security version from the validated session
and updates only if the active account, old hash and version still match. Two
concurrent changes cannot both replace a password using the same version. A
concurrent MFA enrollment invalidates the change. Cookie issuance is bound to
the expected new version; a later security change sends the user back to sign-in
instead of silently upgrading the session. Existing data, password formats and
optional MFA remain compatible. Database engines hide bound parameters in errors.

The optional fifth service engine handles password change, recovery-token
issuance/consumption and recovery mail status records. Its User writes are limited
to password_hash/auth_version/updated_at; it cannot change MFA, billing status,
email, memberships or content. The authentication service still has no password
write grant. Exact table/column privileges and separation from other roles are
checked before constructing the configured services. This does not establish
account-level RLS: trusted authentication/recovery services still act across
account records, and that authority requires further review and isolation.

Recovery web handlers and their background delivery callbacks carry the explicit
factory, avoiding the old shared credential pool. Factor/request/email throttles
remain in the identity pool. Reset still conditionally consumes the hashed,
expiring token and increments the matching account version in one transaction.
It does not create a logged-in session or disable MFA. A failed mail attempt
invalidates its token and records failed delivery. Known and unknown addresses
retain the same outward response. These checks do not prove production SMTP
delivery, durable mail retry, or support recovery.

Tests cover simultaneous password changes, intervening MFA enrollment, default
session compatibility, restricted-role change/reset/re-login, concurrent single
token consumption, failed SMTP delivery records and rejected MFA/billing/email/
social-token access. Providers use mocks and data is synthetic. No production
roles, keys, account state, social connections or posts have changed.

Before production, complete signup/profile/lifecycle, callback, telemetry and
worker mappings, account authority isolation, exact installed policy checks and
operational evidence. Current staged routing is still incomplete and must not be
enabled for customers. Before activation rollback is code-only; after security
state changes use compatible forward recovery, preserving password hashes,
MFA state, consumed tokens and monotonically increasing auth versions.
