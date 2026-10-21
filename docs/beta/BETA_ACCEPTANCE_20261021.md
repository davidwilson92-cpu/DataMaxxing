# External beta acceptance — 21 October 2026

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

Validation and deployment are pending. Native app source, database schema,
authentication, provider connections and billing settings are unchanged.
Build 10 remains Apple's approved binary; no replacement native build is needed
for this server dependency change.

## Owner acceptance still needed

- Complete separate recovery-test signup, actual email reset and new login;
  verify used-link and old-session rejection. Never reset Apple's reviewer.
- Physical build 10 attachment/draft reload and Facebook/X/TikTok cancellation
  return, including phone/iOS details. Instagram return was previously confirmed.
- Approve the prepared independent monitor's $1/month minimum and separate
  health-only credential, then prove delivery and acknowledgement of an alert.
- Confirm support inbox coverage. Gmail delivery was verified previously.

The earlier logical recovery receipt remains valid evidence for the database,
encrypted values and 16 available uploads; four missing August files remain
an unresolved historical recovery incident with no current draft references.
Managed PITR and independently stored key recovery are not inferred.

Do not present Apple approval, synthetic tests or an invitation URL as completion
of these remaining checks. Keep customer charges disabled and retain all 79
commercial findings. Do not deploy the unfinished broader migration.
