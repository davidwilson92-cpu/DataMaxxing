# Retention, deletion and processing inventory

Version 1, 26 October 2026. Owner: David, Zova Social Limited.
**Proposed for approval; new periods are not yet a live customer promise.**
The existing seven-day assisted account-deletion target is already owner-approved.
No customer account or content is erased by preparing this document.

## Rules and rationale

Keep data needed to provide the requested service, maintain security and reconcile
authorised transactions. Separate content from minimal technical evidence. Do not
retain full content indefinitely because a billing or delivery identifier is needed.
Security metadata and pseudonymous IDs can still be personal data.

UK GDPR does not set a single duration for all records. Each period below is an
operational proposal requiring purpose/necessity review, not a statutory period.
[ICO storage limitation](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/data-protection-principles/a-guide-to-the-data-protection-principles/storage-limitation/).

| Category / actual stores | Purpose and proposed basis for review | Proposed rule | Current implementation / required work |
| --- | --- | --- | --- |
| Account, identity, preferences; `nova_users`, `zova_auth_identities`, brands | Account service: contract; abuse controls: legitimate interests | While account is used; review inactive accounts after 12 months, notify before any closure; never delete solely from last-login age yet | Hashes and versioned sessions; assisted deletion scrubs identity. No inactivity notification/closure workflow exists |
| Drafts, Studio conversation, reviews, schedules, recurring series, strategy/actions, voice/examples/learned style | User-requested creation/planning: contract; confirm treatment of third-party people in content | While account active or until user removal; active-store account erasure target seven days after a verified request, subject to reconciled blockers | Saved in owner/brand scope; eraser scrubs/deletes these categories. No arbitrary 30-day purge of working drafts |
| Uploads, filenames, observations, performance snapshots, post excerpts | Media drafting, publishing and requested analytics: contract, with AI permission | Follow content/account lifecycle; remove derivatives with originals on erasure. Performance snapshot overwritten by refresh; expired usefulness is not automatic physical deletion | Original uploads can contain metadata; sampled frames go to AI when allowed. Four historical upload records have missing files. No content-scanning or universal metadata-stripping assurance |
| Social IDs and encrypted access/refresh/audio credentials | Authorised platform connection: contract | Clear local credentials at unlink; erase with account after outcome reconciliation; provider grant revocation tracked separately | Local unlink clears credentials; account request blocks new use. Provider-held posts/grants are not automatically erased everywhere |
| Web recovery and email-verification token hashes, OAuth/Apple state | Sign-in/security: contract and legitimate interests | Eligible for cleanup 24 hours after expiry; daily sweep would add up to 24 hours. OAuth/Apple state is eligible 24 hours after creation, beyond its existing 10/20-minute validity. Keep revocation evidence until its authority expires plus 24 hours | Expiry enforced now. Bounded operator helper prepared; daily execution is not activated or evidenced. Used state must not be made reusable |
| Native sessions, refresh history, grants and browser handoff receipts | Secure iPhone access: contract and legitimate interests | Keep refresh-reuse evidence for entire session lifetime; remove expired session family. Preserve consumed browser receipts for their existing 20-minute navigation grace | Existing native cleanup supports expiry and browser-return grace; never prune a used refresh token while its session is valid |
| Pending social confirmation encrypted payloads | User confirms correct account before connecting: contract | Ten-minute authority; remove expired payloads on worker cycle/next connection | Existing scheduler/connection cleanup. Verify worker health rather than promise instantaneous deletion |
| Request-rate buckets | Abuse prevention: legitimate interests | Delete at window expiry; no permanent raw-IP history for this purpose | Existing request cleanup; hosting logs are separate |
| Product events, AI usage/cost metadata and delivery status metadata | Reliability, service costs, optional measurement: legitimate interests assessment required | Detailed metadata 90 days, then genuinely anonymous aggregates where possible; do not expire unresolved reservations/delivery evidence | Age-based purge not implemented; no claim that existing rows already meet 90 days. Account erasure deletes product events but retains minimal usage records |
| Security/application logs | Incident investigation: legitimate interests | Routine logs 30 days; incident-specific records up to 12 months after closure with documented need | App redacts secret queries/media filenames; host/proxy log retention/settings still require verification. Do not export raw logs into this pack |
| Support mailbox, attachments and case records | Customer support: contract; evidence: legitimate interests | Routine correspondence 12 months after closure; remove unnecessary attachments sooner; assessed holds reviewed every 90 days | Cloudflare forwards to Gmail. Mailbox deletion, trash and provider retention need account-level evidence |
| Billing/financial records and webhook deduplication | Transaction reconciliation: contract; accounting duties where applicable | Separate test records from real financial records. Propose 90-day review of test metadata; accountant confirms statutory duration for real records before live charging | Test-only Stripe; no arbitrary automatic deletion of financial IDs or deduplication records. Disputes/active subscriptions block account erasure until reconciled |
| Publication ledger and review provenance | Prevent duplicate publication, reconcile uncertain results: contract and legitimate interests | Keep unresolved outcomes until reconciled, review every 30 days; then retain minimal IDs/status up to 12 months after account closure, subject to necessity review | Existing eraser scrubs content but retains ledger. Never purge or resend an unknown outcome to make a retention check green |
| Deletion receipts and external recovery exclusion journal | Prove action and prevent resurrection: legitimate interests/compliance assessment | Proposed 12 months after verified completion, and never shorter than the oldest retained backup plus recovery verification; extend only documented necessity | Receipt lives in DB; independent restricted journal and restore reconciliation need operational verification |
| DB exports/PITR and upload disk snapshots | Disaster recovery: legitimate interests | Use shortest documented working recovery window. Observed DB PITR three days; Render logical export retention at least seven days. Disk snapshots have separate retention; copies made outside Render need own expiry | Managed DB backup exists; do not promise a seven-day maximum for all copies. Restored data must be reconciled with current deletion/revocation/publication journals before service resumes |

AI provider and email-provider retention is separate from Zova's own deletion.
Deleting Zova data or withdrawing AI permission is not a retroactive deletion of
all supplier records. Supplier-specific requests/limits belong in the case record.

## Deletion operations

Use [the existing runbook](../beta/ACCOUNT_DELETION_RUNBOOK.md), not an ad hoc SQL
delete. David reviews the private queue daily. Verified self-service request
revokes access; completion is recorded only after files and committed database
cleanup are checked. Keep uncertain provider outcomes, active billing, legacy
identity and storage-ownership blockers visible. Resolve or isolate the minimum
necessary records rather than retaining all content without explanation.

Record a hold's reason, specific categories, approving person, next review date
(no more than 90 days), and release criteria. A hold is not blanket indefinite
retention. Notify the requester of delays/limits using the established support
process; the seven-day target is not a replacement for applicable rights deadlines.

Before restoring, apply the current external deletion-exclusion journal to the
recovered copy. First disable affected accounts and publishing; then reapply
reviewed erasure after resolving dependencies. Preserve revocation/version state
and reconcile provider actions since the backup. Do not restore live traffic until
all journal entries are accounted for. The journal must not reside only in the
database being restored. Its identifiers are restricted personal data.

## Customer notice update after approval and implementation

Explain plainly: account/content lifecycle; assisted deletion target and exceptions;
specific routine-log/support durations; backup windows and suppression on restore;
supplier processing; public social posts remain under the platform account.
Update the actual notice only for controls verified as operating. Preserve export,
AI withdrawal and separate social unlink controls. Do not publish this internal
proposal as though all purge jobs, contracts and backup controls already exist.

## Approval and evidence

Policy owner decision/date: **pending**. Privacy review: **pending**. Business/service
address: **pending**. New purge activation: **not enabled**. Implementation receipts,
job cadence, exception review, sample erasure verification and backup reconciliation
are required to close the relevant rows. Review quarterly during beta.

## Prepared technical control

`python scripts/audit_retention.py` reports aggregate counts with a read-only
transaction and no token/identity output. It does not import/start the app or
migrate tables. The optional `--apply --confirm-expired-only` requires
`ZOVA_RETENTION_POLICY_APPROVED=2026-10-26-v1` after approval. Each transaction
removes at most 500 old recovery/verification/revocation/OAuth/Apple-state rows;
repeat bounded batches if needed. No draft, upload, active native session,
refresh-reuse history, publication or billing row is in its allowlist. There is
no new cron service or paid monitor. It is an operator tool, not an automatic
data-retention programme; other rows in the table remain separate work.
