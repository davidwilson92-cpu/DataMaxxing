# External beta follow-up checks — 20 October 2026

## Changes

Candidate `7048c353d2833a24076bde99a8a09a4c2e7a286f` adds three bounded fixes:

- A separate optional `MONITOR_READ_TOKEN` can read dependency/worker health. It
  cannot dispatch jobs or access customer cohort reports. Existing operations
  credentials retain their previous scope. No new credential has been created.
- The monitor requires a safe HTTPS destination, refuses redirects and malformed
  destinations, times out, and reports sanitized failures. Its existing checks
  for uncertain publications, worker/mail failure and missing cost coverage remain.
- Attachments are checked for availability and size before publication review and
  again before dispatch. Missing files return a useful re-upload instruction;
  loss after review is a definite pre-send failure with the usage reservation
  released. Drafts, attachment records and publication receipts are preserved.

Native app source is unchanged. A simulator-only test setup timeout increased
from 5 to 30 seconds after the network listener became ready late in CI. The
handshake, body, cookie, redirect and response assertions are unchanged. The
failed run `39489964197` remains recorded rather than counted as a pass.

## Recovery evidence

The live database was read with a consistent, read-only snapshot. It was restored
into a newly generated private Unix-socket PostgreSQL 18 database under temporary
storage on the existing Render instance. No network listener, application,
scheduler, email or provider process ran in that restored environment. The source
database and upload files were not changed. Temporary copies and extracted
official PostgreSQL tools were removed and cleanup was verified.

The database comparison passed: **44 tables / 401 rows**, full row digests match,
and **39 encrypted values** decrypt with the existing key and reject a wrong key.
**16 files / 6,187,895 bytes** passed copied/restored content hashes.
See `restore-receipt-20261020.json` for the sanitized receipt.

The overall media recovery result is **incomplete**: four records dated 29–30
August have no corresponding file on the live upload disk. Read-only checks found
no reference to them in current draft workspaces/conversation media, saved publish
reviews or schedules. No matching copy was found in local workspace upload folders.
The records were retained. Recovery from an older independent backup or the
original files remains open; no file was fabricated and no missing record deleted.

This proves a fresh logical database/key/available-media restore. It does **not**
prove Render's managed PITR service, restoration from an older snapshot, or
independent recovery of keys if the hosting account is unavailable. Those broader
operational gaps remain in the retained commercial register.

## Automated acceptance

- 106 focused media, review, provider-outcome and restore-boundary checks passed.
- 34 focused monitor, restore-boundary and beta-scope checks passed after the
  sanitized recovery diagnostic update.
- Required complete application/PostgreSQL CI: `39492645799` passed: 584 SQLite
  checks / 2 skipped, 585 PostgreSQL checks/ 1 skipped, 18 client tests/groups plus Studio,
  no known dependency vulnerabilities, synthetic recovery, container smoke and scope.
- Native simulator/release checks: `39492645584` passed 16 unit tests, 1 UI test and
  release compilation. This remains separate from phone acceptance.

All automated provider calls use synthetic data and mocks. No real post was sent.
No database schema or customer credential changes are included.

## Remaining invitation gates

1. Apple approval: build 0.1.0 (10) still **Waiting for Review**; external group has
   zero testers. Review credentials remain unchanged.
2. Owner completes the separate `Zova Recovery Check` account signup and a live
   reset using its controlled mailbox. Then verify login and old-session/link
   rejection. Do not reset Apple's reviewer account.
3. Owner completes the requested build 10 device check: attachment/draft reload,
   Facebook/X/TikTok sign-in cancellation and return, with iPhone/iOS details.
   Instagram return was owner-confirmed previously; this is not all-provider proof.
4. Independent monitor is prepared, not activated: Render cron every 10 minutes,
   30-second runtime cap, auto-deploy off, no database/provider/billing credentials.
   Owner approval of the $1/month minimum and the new read-only access is pending.
   Configure the alert destination and demonstrate delivery/acknowledgement.
   Historical unknown publication and unpriced AI usage must stay visible; do not
   suppress these signals merely to obtain a green monitor.
5. Owner confirms who monitors the already delivery-tested support mailbox.

Do not invite testers until the applicable access/recovery/device/alert gates are
closed. The four historical missing files remain a documented recovery incident;
the check must not be represented as a full media-recovery pass.

## Deployment and rollback

The exact candidate 7048c35 is live on Render, deploy `dep-dbbt0mjncjis73c1hcv0`,
at 21:35 BST. Effective billing mode off, checkout false and subscription enforcement
false were verified. Dependency readiness is 200; the database/schema and embedded
worker are available. Full status remains attention for one historical unknown
publication and 47 unpriced AI calls. No overdue/stuck jobs, mail failures or old
reservations. Studio draft 36 and reviewer session survive the update; Drafts,
Performance, Account and Help were checked. A brief 502 during restart cleared
when the deploy became Live. TestFlight build 10 remains the submitted native binary.

If this bounded server change causes regressions, restore runtime `b131f23` on
the same service while retaining database, upload disk, encryption/session keys
and all publication receipts. It retains the prior AI-consent and security-form
fixes. If a monitor has subsequently been enabled, pause its job during rollback
because that version does not accept the new read-only key. Never replay unknown
posts or restore stale production data as a code rollback.

All 79 deferred commercial findings remain retained. Beta readiness and commercial
readiness are different decisions; do not award unsupported closure or scores.
