# Atomic signup and one-use callback state

Validated candidate 0c11d2c: local and CI SQLite 428 passed / 62 expected skips;
PostgreSQL 489 passed / one expected skip. CI run 38004625728 also passed migrated
RLS restore, restored context/policy verification, image build/smoke and Python
dependency audit. Full production gate remains blocked. No production accounts,
data, grants, keys, provider actions or deployment changed.

Regressions reproduced five account-lifecycle defects before correction: password
signup retained an account after preference creation failed; concurrent signup
returned a server error; initial session issuance could adopt an intervening
security version; Apple identity-link failure retained a partial new account;
and concurrent Apple callbacks both reached token exchange with the same state.
The shared social-state helper also accepted two concurrent claims; this was
reproduced with the Instagram-via-Facebook state variant.

Password signup now flushes the new User (and its existing workspace/membership
hooks), creates default preferences and commits them together. A failed database
write rolls the transaction back, preserves nonsecret form inputs and gives a
retry message without database diagnostics. A concurrent email conflict directs
the losing request to the existing-account message, without signing into that
account or replacing its fields. Session issuance uses the security version
captured before commit; an intervening change requires sign-in. Existing consent,
country, password policy, subscription defaults and onboarding route remain.

Apple new-account creation commits User/workspace/membership/preferences and the
provider identity together. Existing-account profile/login metadata and a new
identity link also commit together. A failed identity transaction rolls back and
requires a fresh sign-in attempt. The already consumed authorization state remains
consumed: no automatic token-exchange retry is introduced.

Apple and the shared social callback helper conditionally claim an unused,
unexpired state with matching identifiers before provider exchange. Concurrent
callbacks cannot both claim it. Tests cover X, Instagram Login, Instagram via
Facebook, Meta and TikTok state variants, alongside existing callback regressions.
No requested scope, provider grant, destination selection or publishing approval
has changed.

Tests verify complete rollback/retry, one winning concurrent signup, retained
consent/preferences, no inherited social connection, an intervening MFA change,
unchanged existing password/session/connection and revoked membership, Apple
rollback and single state claims. Provider exchanges are mocked. These are not
live provider acceptance or browser account-switching evidence.

Restricted registration/Apple/social service routing remains open; those routes
are still disabled in separated-service mode. Account-level database isolation,
historical incomplete-account reconciliation, full provider callback assurance,
worker services and operational/independent release evidence also remain open.
Do not enable the partial service mode or treat this fix as release approval.

Rollback before rollout is code-only. After rollout, retain all created accounts,
preferences, memberships, security versions and consumed states. Use a compatible
forward fix rather than restoring partial commits or replaying provider callbacks.
