# Legacy X durable publishing rollout

This candidate changes the Custom GPT action contract. Do not deploy it without
updating configured GPT actions from `openapi-action.yaml` and verifying their
user confirmation and status handling in isolated staging. Staging is deferred.

`POST /x/post` requires explicit approval and a 16–128 character idempotency key.
It returns HTTP 202 and a job/status URL, never claims that queued work is already
published. Repeated identical submissions reuse the same creator-scoped job;
reusing a key with different text fails. A new key is a new explicit approval,
not a recovery mechanism for unknown outcomes. Read `/x/jobs/{job_id}` with the
same creator credentials. Only `published` confirms success.

Queued work can be cancelled through `POST /x/jobs/{job_id}/cancel`. The atomic
queued-state transition races safely with the worker claim. Once claimed, the
request may already be in flight; cancellation returns a conflict. Failed and
unknown jobs are retained, never automatically retried. Unknown jobs require
checking the destination before any separately approved resubmission.

Migration `20260929_legacy_publication_queue` adds an empty ledger with a foreign
key to retained creator identities. Historical post logs are not replayed or
backfilled. Existing user, creator, OAuth credentials and content tables are not
rewritten. Tests cover repeat migration, concurrent inserts/claims, changed
authority, cross-creator reads and ambiguous/crashed sends. PostgreSQL CI must
also pass and the synthetic restore must preserve ledger fields.

Roll forward after an interrupted rollout, retaining the ledger. Do not revert
to a synchronous `/x/post` server while clients may retry queued submissions:
the old server cannot recognise their keys. Pause entry traffic and workers,
reconcile every queued/publishing/unknown job and update clients before any
rollback. Never restore an older database or delete ledger rows to retry sends.

Dedicated worker command: `python -m nova.worker`. Set
`EMBEDDED_SCHEDULER=false` on web processes when an independent worker is
provisioned. The default remains compatible with existing embedded scheduling.
No independent worker has been deployed; always-on availability, alert delivery,
staged migration/recovery and restricted database roles remain unverified.

The approval digest binds creator/API authority, account and credential snapshot.
Changes before dispatch reject the job. Calls already in flight cannot be recalled.
Token refresh between approval and claim may require a fresh review; this is a
conservative rejection, not permission to resend an uncertain job. Database RLS,
global pause, append-only audit and provider reconciliation remain separate work.
