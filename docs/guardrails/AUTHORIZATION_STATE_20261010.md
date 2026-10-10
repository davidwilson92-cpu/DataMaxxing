# Pending authorization integrity

Validated 5623847: CI run 38012343321 passed 595 PostgreSQL tests (two expected
skips), 510 SQLite tests (87 expected skips), restored authorization/identity and
account/workspace protections, image build/smoke and Python dependency audit. The
full production gate remains blocked; production is unchanged.

The identities migration now uses version 20261010_authorization_state_guards,
superseding the five-table identity guard implementation with eight protected
tables. Existing migration history and record values are retained. Runtime startup
requires the new version and verifies current definitions. Use the existing
explicit identities phase or authorised offline preparation before rollout.

Additional immutable authority:

- Apple AuthState: identifier, provider, state hash, nonce hash, intent and issue time.
- Social OAuthState: identifier, owner/workspace, platform, state hash, encrypted
  PKCE verifier (including an originally absent verifier) and issue time.
- PendingConnection: code hash, owner/workspace, auth version, platform and expiry.

All three are single-consumption records: used cannot revert from true to false.
The pending connection's encrypted payload can remain unchanged or become empty.
Replacing credentials/account candidates, or restoring them after erasure, is
rejected. This preserves existing confirmation, switch, cancellation and expired
credential cleanup. Existing connected-account credentials are not modified.

Nullable PKCE is explicit in the schema manifest. SQLite workspace columns retain
their existing physical declaration and enforce required canonical ownership via
the separate workspace triggers; PostgreSQL also enforces physical NOT NULL.

Regression fixtures reproduce authority changes before installation and require
rejection afterwards. They cover one-way consumption, permitted deletion, pending
payload erasure and attempted restoration, and adding a late PKCE verifier.
Existing expiry tests now control clocks rather than modifying issued records.
The cleanup test creates an already-expired pending record without moving the
worker clock for unrelated scheduled jobs. Full connection tests retain explicit
confirmation, both Instagram routes, X/TikTok, wrong-owner/brand rejection,
concurrent claims and preservation of existing connections.

The synthetic restore fixture includes Apple state, social state and a pending
connection; it checks that nonce/platform/payload replacement remains forbidden
after restore. No production data, provider calls, grants or configuration change.

Rollout/forward recovery: pause writes for migration, retain current data and
credentials, and diagnose failures through the trusted maintenance process. Never
disable authority guards or restore old records merely to undo code. Do not use
an offline preparation marker in deployed services. The full release gate,
restricted account-service integration and independent/operational review remain
open.

Next inspection: billing customer/mode binding and usage operation ownership.
Usage reservation currently legitimately moves a released entry to the new month;
do not make that period immutable and break retry accounting. Its reserve/finish
helpers need explicit owner/kind checks when resolving an existing key. Any change
must retain disabled subscription enforcement and use synthetic billing providers.
