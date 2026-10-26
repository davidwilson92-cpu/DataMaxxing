# Limited-beta account deletion runbook

Owner: **David**. Service target: **seven days from request creation**. Check the private queue daily; the monitor remains inactive unless separately approved. This is a manual service, not an automatic deletion or notification system.

## Daily triage

1. Use the existing full operations credential to read `/internal/deletions`. A read-only monitoring token cannot read case receipts or execute erasure. The queue includes owner, target date and overdue state; `/internal/status` exposes counts only, not customer content.
2. Record the opaque receipt and a nonpersonal case reference in the restricted operator case log. Do not copy passwords, tokens, email addresses or post content into logs, screenshots or chat. The user already verified their current password when submitting the self-service request; do not require another support email or external form.
3. On the current Render deployment host, using its existing environment and persistent upload disk, run the read-only plan:

   ```sh
   python scripts/process_deletion.py plan --receipt RECEIPT
   ```

   An explicit `DATABASE_URL` is required. The script uses schema verification only and never silently migrates. It resolves the receipt to exactly one inactive account without printing customer identity/content. It refuses an arbitrary platform receipt, unresolved account or still-active account.
4. Review blockers promptly. Do not wait for the seven-day target before investigating. If a target will be missed, contact the user through the established support process and keep the receipt pending. No automatic email has been sent. The receipt shows overdue status honestly.

## Reconcile before erasure

- **Sending, pending or unknown outcomes:** confirm the provider's result using existing reconciliation/support tools. Never resend. Preserve receipt/credentials while investigating. The eraser refuses scheduled, queued, publishing, pending and unknown ledger states. Do not manually rewrite statuses solely to make the eraser pass.
- **Subscriptions:** reconcile cancellation and financial records with the provider. Active/trialling/past-due/unpaid/incomplete/paused subscriptions block erasure. Customer charges remain disabled; this is still checked defensively.
- **Provider access:** the request disables local connections. This workflow destroys locally stored primary/refresh/audio credentials after reconciliation; it does not claim to remove published social posts or revoke every provider-side grant. Record any required provider-side action in the case; do not perform unnecessary account-wide revocation that affects another user/brand.
- **Legacy links:** a linked legacy Creator identity blocks this helper and requires a separately verified credential/retention procedure.
- **Storage:** this bounded workflow supports the existing local Render upload disk. It refuses remote/unexpected paths, symlinks and files shared with another owner (including equivalent paths/hardlinks). Do not delete another customer's file. Remote/versioned object storage requires a separately verified storage-specific erasure procedure; do not bypass this refusal.
- **Retention/backups:** record the applicable retention basis, retained ledger categories and a review/expiry date in the restricted case. The helper retains pseudonymous billing/usage/delivery records, technical IDs and terms/audit dates; it scrubs customer text/media/profile/credentials and checkout payloads. Identify backup retention and ensure any restore reapplies completed deletion cases before serving users. Do not call this “all copies everywhere deleted.” No new statutory retention period is invented by this runbook.

## Establish an actual maintenance/drain window

The current app has writers that can finish after authentication. Revoking one user's access alone does not guarantee that all in-flight requests have finished. The safe beta procedure uses a short, explicit full-service pause.

1. Schedule a quiet maintenance window and record the deployment/environment/storage location in the case. No account data is exported as an untracked “backup”. Follow the existing controlled backup policy, including retention and deletion replay after restore.
2. On **all** web/worker services set `ZOVA_MAINTENANCE_MODE=account-erasure` and `ZOVA_SCHEDULER_MODE=disabled`, then restart/redeploy so old processes actually stop. Leave normal production defaults unchanged outside this window. Runtime rejects maintenance with an enabled scheduler.
3. Verify old instances, workers, jobs and shells that could write are stopped. An environment-variable edit without restart is insufficient. Wait at least five minutes after the replacement maintenance service starts and verify the running hostname returns authenticated `/internal/maintenance` with the expected mode and disabled scheduler. Public health and deletion receipts remain readable; customer routes, callbacks and webhooks return retryable 503. No new customer work is accepted.
4. Review provider reconciliation again. The command additionally refuses a publishing-worker heartbeat recorded after maintenance began. This is a supplemental check, not proof that arbitrary external writers have stopped. The operator must confirm every old service is drained.
5. Use the maintenance host's same deployed code/database/disk to execute **one** reviewed case. Do not copy a production database URL into a different local checkout or run against an unrelated upload directory.

## Execute one case

```sh
python scripts/process_deletion.py execute \
  --receipt RECEIPT --confirm-receipt RECEIPT \
  --case NONPERSONAL-CASE-REFERENCE \
  --expected-host zova-social.com \
  --confirm-services-drained --confirm-retention-reviewed
```

Use the exact actual service hostname if processing a separately authorised test environment. The script requires an absolute `UPLOAD_DIR`, an explicit database URL, local maintenance/disabled scheduling, an authenticated HTTPS response from the expected live origin with redirects disabled, a five-minute pause, both operator confirmations and the repeated receipt. Operations secrets are read from the environment, never passed on the command line or printed. Do not put credentials in the case reference.

The command rechecks all blockers, revokes access, marks processing, deletes local media, scrubs profile/strategy/voice/draft/content/connection data, clears transient checkout data and removes authentication authority. It commits cleanup, reads it back and checks files are absent **before** marking the customer receipt `active_store_erased` and adding a completion timestamp. Another owner's data is outside the selected account.

### Failure and retry

- Nonzero exit means **not completed**. Keep maintenance active, inspect the receipt and restricted diagnostics, resolve the specific problem and rerun the same receipt/case. Do not manually set the completion status.
- A crash after access revocation leaves `erasing`; a crash after a file was removed can be safely retried. Missing files are handled idempotently. Failed database/file verification does not mark completion. Retrying completed cleanup is permitted and re-verifies it.
- The public receipt is the completion communication. Confirm it displays the verified timestamp and retention limits. If sending a separate email is necessary, use the existing authorised support process; this script sends no email and does not store an outgoing-message promise.

## Resume and evidence

1. Save only the receipt, case reference, completion time, blocker reconciliation references and retention/backup decisions in the restricted operator log.
2. Remove `ZOVA_MAINTENANCE_MODE`, restore the prior scheduler mode, restart the services and verify health/readiness, worker heartbeat and queues. Deferred webhooks/callback attempts must not reactivate a deleted account; inspect any retry errors before broad beta use resumes.
3. Confirm the deleted account cannot authenticate, its receipt remains readable and a separate synthetic control account's content is intact. Do not use a real user's credentials to test this.
4. Review overdue queue counts daily. An inactive paid monitor does not remove David's responsibility to check the queue. Seven days is an operational target; an overdue or blocked case remains visible rather than being falsely completed.

## Release boundary

This procedure makes the limited-beta manual process executable and testable. It is not a claim of automatic erasure, universal provider grant revocation, immediate backup erasure or commercial/legal certification. Production execution has not been performed merely by adding the code or this runbook.
