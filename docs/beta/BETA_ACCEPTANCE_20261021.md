# External beta acceptance — 21–22 October 2026

## Verified starting state

- Apple external group f3f15099-0bec-49dc-8347-cd55beb805c0 shows build
  0.1.0 (10), UUID 49d32ac0-86d6-43bc-a0e3-8d82d9101af1, as Testing.
  There are zero external testers. No public invitation link has been created.
- Render remains on 7048c353d2833a24076bde99a8a09a4c2e7a286f, instance r9986.
  At 21:22 UTC its effective billing mode is off, checkout false and subscription
  enforcement false. Database/schema readiness passes and the embedded worker
  is idle. No overdue or stuck publication, mail failure, old reservation or
  recent AI failure is reported. SMTP recovery is configured.
- Full operational status remains attention for one historical unknown Instagram
  publication and 47 unpriced October AI calls. No outcome or cost is fabricated.
- Apple's isolated reviewer is still signed in and unchanged. The separate
  zova.social+beta-recovery@gmail.com account does not yet exist; signup is
  prepared for the owner's credential entry and terms acceptance.

## Security update

Fresh pip-audit found 18 Pillow findings and 12 pip entries (including duplicate
advisories) in the existing local environment. Render independently reports the
same installed versions: Pillow 12.3.0 and pip 25.0.1. The older application CI
audit result is retained as historical evidence only.

The bounded fix pins Pillow 13.0.0 and pip 26.2.0 in the hosting build. CI now
extracts the actual built image's installed package inventory without network
access and audits that inventory, in addition to the test environment. This
closes the gap where a clean test runner could coexist with an outdated image
installer. Required PostgreSQL, recovery, image-smoke and scope checks remain.

Primary release reference:
https://pillow.readthedocs.io/en/stable/releasenotes/13.0.0.html

Native app source, database schema,
authentication, provider connections and billing settings are unchanged.
Build 10 remains Apple's approved binary; no replacement native build is needed
for this server dependency change.

## Validated and deployed

- Exact candidate `bcd260e25d92b41101f31073e2a626588195c65d` passed required
  application/PostgreSQL CI `39679616727`: 590 SQLite tests / 2 skipped,
  591 PostgreSQL tests / 1 skipped, 18 client tests/groups plus Studio, synthetic
  recovery, hosting-image smoke and the exact limited-beta scope.
- Both the test environment and actual hosting-image package inventory have no
  known findings in the fresh dependency audit. Six new decoder checks cover
  JPEG/PNG/GIF/WebP, phone EXIF orientation/metadata removal and truthful animated
  image first-frame coverage. A separate fresh local environment passed 72
  focused checks plus the six new checks and `pip check`.
- Native CI `39679616901` passed 16 unit tests, one UI test and iPhone release
  compilation. The duplicate application run `39679609151` also passed.
- Render deploy `dep-dbcj1pvb9u1s73bree8g` became Live at 21:39:52 UTC on
  21 October, instance `n7s4s`. Live runtime independently confirms the exact
  commit, Pillow 13.0.0, pip 26.2, billing mode off, checkout false and
  subscription enforcement false. No schema or customer credential migration.
- On 22 October at 09:02 UTC readiness reports database reachable and required
  schema available. Worker is embedded/idle; no overdue/stuck publication,
  failed/stuck mail, old reservation or recent AI failure. Full status remains
  attention for one historical unknown publication and now 49 unpriced AI calls.
  The zero estimate is incomplete, not evidence that AI usage costs nothing.
- The existing reviewer session survived deployment. The owner subsequently
  created the separate recovery account; its onboarding and Drafts show its own
  identity, no connections and no drafts, without the reviewer's draft36.
- Screenshot receipt: `social-proof/beta-security-render-live-20261021.png`
  (ignored). No actual social posts or provider grants changed.

## Owner acceptance and operational decisions

- Owner reports the requested build 10 attachment/draft reload and Facebook/X/
  TikTok cancellation/return checks passed. Device/iOS details were not supplied;
  record this as owner acceptance, not an observed automated physical-device run.
  Instagram return was previously confirmed separately.
- Owner explicitly chose **Leave the monitor inactive** on 22 October. No new
  Render cron, recurring hosting charge or read-only credential was created.
  This supersedes approval of that proposed service as an invitation prerequisite;
  independent automatic application monitoring remains an accepted beta limitation.
- Owner chose `david@zova-social.com` for beta operational contact/test alerts.
  The authorised clearly labelled manual test alert was sent through the deployed
  application mailer. Resend message `01a162d9-354b-7cb1-9a8a-dd7ef6080e8d`
  reports Delivered and the owner confirms receipt in the chosen forwarded inbox.
  The delivery/receipt check is complete. This proves the manual
  delivery route only, not an active automatic incident-alert service.
- Recovery email for the separate account is Delivered, Resend message
  `01a162d7-4bb8-7bf3-bf53-0efa41c37ad5`; the token was opened from the visible
  email and removed from the form URL. After the first owner completion reply,
  read-only checks still showed an unused token/auth_version 0 and the existing
  session remained valid. Completion is not inferred: owner was asked to finish
  the actual new-password submission. Apple's reviewer password is unchanged.

## Evening reconciliation — 22 October

The owner now reports "Password updated" and a completed Apple sign-in. Fresh
read-only checks at approximately 21:57 UTC do not yet match those reports:

- The deployed service is still exact `bcd260e` using PostgreSQL. The separate
  recovery account has auth_version 0 and one unused reset record, expired at
  09:15:38 UTC. No token, hash or credential is copied into the evidence.
- A newly opened protected Account page accepts the pre-reset browser session
  and shows the exact recovery-test email. Old-session rejection has not passed.
- All accessible Apple tabs show login; navigating directly to the intended
  external group still redirects to login. No public-link creation is observed.
- A clarification asks whether the steps were completed in the side browser or
  another browser/phone. Reconcile that answer before asking for repeated actions;
  do not infer a successful reset from the reported message alone or access to an
  Apple session from a sign-in in a different browser.
- Live database/schema readiness passes. Billing is off, checkout and enforcement
  false; worker idle and no overdue/stuck jobs, failed/stuck mail or recent AI
  failures. Full status correctly retains the historical unknown publication and
  49 unpriced AI calls. No new code, deployment, paid monitor or credentials changed.

## Invitation activation — 22 October, approximately 22:09 UTC

- Fresh Apple sign-in is now observed. The external group's assigned build
  **0.1.0 (10)** still shows **Testing**, with 88 days remaining at inspection.
- Saved the owner-requested public link with **Set Limit: 10**. Apple now shows
  **Tester Limit 0 of 10** and https://testflight.apple.com/join/BxawFPCu.
- Opened the public destination and verified **Join the Zova Social beta** and
  Apple's instruction to open it on a device with TestFlight installed.
- No tester was enrolled and no direct invitation was sent. This resolves the
  Apple-session/link blocker only; it does not close the separate recovery check.
- Screenshot receipts (ignored): `social-proof/testflight-public-link-20261022.png`
  and `social-proof/testflight-invitation-page-20261022.png`.

## Remaining acceptance

- Complete the separate recovery account's actual email reset and new login;
  verify used-link and old-session rejection. Never reset Apple's reviewer.

The earlier logical recovery receipt remains valid evidence for the database,
encrypted values and 16 available uploads; four missing August files remain
an unresolved historical recovery incident with no current draft references.
Managed PITR and independently stored key recovery are not inferred.

Do not present Apple approval, synthetic tests or an invitation URL as completion
of these remaining checks. Keep customer charges disabled and retain all 79
commercial findings. Do not deploy the unfinished broader migration.

## Rollback

No schema change is involved. Keep database, uploads, encryption/session keys,
mail settings and publication receipts. Revert an affected application change
while retaining the patched Pillow/installer versions where possible. The prior
`7048c35` deployment is a continuity fallback only: it has the newly documented
dependency findings and is not a security-equivalent release. If it must be used
for an emergency outage, pause new invitations and reapply the dependency patch
before resuming. Never restore stale production data or replay unknown posts.
