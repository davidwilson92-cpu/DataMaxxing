# Recovery and incident exercise

26 October 2026. Owner/incident lead: David, david@zova-social.com.
Keep Render, Stripe test-only, customer charges/enforcement off, paid monitoring
inactive. No live account deletion, database overwrite or automatic post retry.

## What must be proved

A backup exists; that is not full recovery acceptance. The 20 October logical
production rehearsal matched 44 tables/401 rows, decrypted 39 values and restored
16 available files, with four old missing files. The 26 October release has a
fresh managed DB export. Both are historical evidence, not a current end-to-end
managed-backup drill or proof of independent key recovery.

Proposed objectives for owner approval: usable service within one business day;
at most 24 hours lost content. Measure DB and media separately, including time
to obtain hosting/key access and reconcile post-backup actions. Report actual
recovery-point age, not just how long pg_restore took.

## Safe exercise stages

1. **Preflight:** record exact runtime, source/backup identity and age, free space,
   memory headroom, database size, uploads size, current jobs and billing safety.
   Abort on resource pressure. Record production health before/after.
2. **No-cost bounded logical rehearsal:** existing
   `scripts/rehearse_render_restore.py` uses read-only production snapshots and a
   private Unix-socket scratch database on the existing service. It cannot accept
   an arbitrary restore destination. No app/worker/mail/provider process starts.
   Compare all table row digests, decrypt with the current key and reject a wrong
   key, copy/restore available media and compare hashes. Remove scratch securely
   and verify no local listener/process remains. This is component recovery only.
3. **Managed-backup drill:** restore a selected Render backup/PITR to a separate
   isolated target. Obtain exact temporary cost approval before provisioning.
   Never use disk restore on the live service just to test it. Acquire compatible
   upload backup and a private copy for the drill. Confirm backup age/content
   consistency, encryption and restore instructions. No public endpoint/DNS switch.
4. **Independent keys:** show the designated operator can retrieve required keys
   from approved restricted recovery storage, without displaying them, and decrypt
   the restored values. Same-process access to the current environment key does not
   satisfy loss-of-host recovery. New storage/access arrangements need approval.
5. **Suppress old authority/actions:** apply current deletion/revocation journal,
   password/MFA changes and connection unlinks that occurred after backup. Reconcile
   all pending/unknown provider outcomes and billing events against authoritative
   receipts. No resending merely because the recovered DB has an older state.
6. **Usable-app acceptance:** start isolated app only with verified outbound-network
   denial, worker disabled, test billing/charges off, restricted access and isolated
   uploads. Do not inherit live mail/AI/social credentials. Verify synthetic account
   login, save/reload drafts/media, strategy/voice, Schedule, export and revoked
   access; use fixture provider results. Never impersonate a customer to prove login.
7. **Cleanup:** record evidence without contents/secrets, destroy only the disposable
   target/copies, verify removal and billing termination. No production deletion.

## Required receipt

Record scenario/date/operator/runtime, source and backup creation times, DB/media
coverage, omitted/missing objects, logical/managed restore distinction, recovery
duration, measured RPO/RTO, key recovery source verified (not key value), exclusions
replayed, no-provider-send evidence, separate control-account checks, isolation and
cleanup proof, issues/owner/deadline. A failed/incomplete check remains such.

## Incident tabletop for David

Scenario: hosting fails after a user deletes an account and a provider accepts a
post whose response was lost. David verifies incident scope, records the timeline,
pauses new dispatch using the established maintenance process, preserves logs and
receipts, and restores into isolation. The current deletion journal must prevent
the old account returning; the uncertain post must be reconciled, not sent again.
Resume only after release checks and owner decision. Record customer impact and
whether a personal-data breach assessment/notification is needed; obtain advice
and apply applicable deadlines rather than assuming every outage is a breach.

Operational routine: David checks health, private deletion/operations queue and
support each business day during controlled beta; this is a proposed manual
arrangement pending acknowledgement, not 24/7 detection. Escalate overdue erasure,
failed mail, stuck publication and recovery failures. Test alert delivery was
previously owner-confirmed; the paid monitor remains inactive.

## Retained blockers

### Fresh exercise, 26 October 2026

Runtime: `a9fe5a7a4724231b3491517abed35224f3f8d011`. The existing reviewed
rehearsal helper used a consistent read-only snapshot and private Unix-socket
PostgreSQL 18 scratch target. Official signed PostgreSQL/Debian tools were extracted
to a disposable directory, not installed as a service. No app, worker or network
listener started; no provider calls or source writes occurred.

- All 44 tables / 623 rows matched after restore; 41 encrypted values verified.
- All 25 available files / 25,492,470 bytes passed copy/restore checks.
- Four historical media records still had no source files. Overall **incomplete**.
- Component operation took 4.67 seconds; this is **not** an end-to-end RTO.
- Customer scratch copies and temporary tools removed; no recovery scratch remained.
- Production health returned HTTP 200 after cleanup. Live charging remained off.

The receipt and screenshot are stored in
[recovery evidence](evidence/recovery-20261026.json) and
[the recorded terminal result](evidence/recovery-20261026.png).
This exercise used a fresh logical snapshot, not a managed backup/PITR restore.
It used the current environment key, not independently recovered keys. No usable-app
or external deletion-journal replay was claimed. It does not resolve the blockers
below or supersede the need for a compatible historical DB/media backup exercise.

### Still required

- Four historical missing media files require originals/older backups or an honest
  irrecoverable-loss decision; do not fabricate files or delete records to pass.
- Managed DB/disk restore and independent key access need their own evidence.
- Deletion journal external custody/replay must be exercised.
- A component-only rehearsal does not establish complete application recovery.

References: [Render DB recovery](https://render.com/docs/postgresql-backups),
[disk backup constraints](https://render.com/docs/disks),
[existing beta evidence](../beta/BETA_CHECKS_20261020.md).
