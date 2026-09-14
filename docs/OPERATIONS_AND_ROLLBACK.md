# Operations and rollback — local candidate, 14 September 2026

Nothing in this document authorises a production deployment, post, grant change, review submission or charge.

## Release boundary

Candidate: `codex/studio-attachment-ux`, based on main `493fe375a2bb922e2910af47b67f23d014281d25`. The separate, dirty `zova-production` tree was inspected but not deployed or copied wholesale. Existing PostgreSQL, uploads, encryption key and session secret must remain in place. Both Instagram login routes and the original simple Publish → Confirm publish journey remain. Keep `REQUIRE_SUBSCRIPTION=false` during testing; checkout now rejects requests in that mode.

## Required staging gates

1. Make a managed PostgreSQL snapshot and independent logical backup, plus an upload-volume snapshot. Record timestamps, database version, schema version, row counts and upload manifest hashes without exposing customer content. Verify the encryption key is recoverable in the secret store. Backups containing personal data require the same access protections as production.
2. Restore into a separate PostgreSQL instance with isolated uploads and mocked provider adapters. Compare users, password hashes, encrypted connection bytes, drafts, schedules, media ownership and upload hashes. Test decryption and legacy-session acceptance using synthetic credentials. The local SQLite and synthetic-upload hash drill is **not** proof of a production restore.
3. Run additive migrations once, with other application/worker instances stopped. New tables retain revocations, recovery tokens, request limits, deletion records, reviewed snapshots and publication records; old user/draft rows acquire default versions and empty workspace metadata. No existing columns or rows are deleted. Concurrent migration start is not supported by this lightweight migration runner. Capture migration duration and any locks in PostgreSQL staging.
4. Deploy the candidate frontend and backend together in staging. Old frontend publish calls lack a review token and will safely fail; do not mix cached old JavaScript with the new publishing API. Give the changed assets a release-specific cache version before an authorised release. Restart workers only after the migration and application checks pass.
5. Run the test suite against an isolated PostgreSQL test configuration, plus both browser sizes and mocked providers. Current test fixtures deliberately force disposable SQLite; a PostgreSQL staging fixture must be isolated explicitly before that run. Do not point the current test harness at production.
6. Configure and test recovery email with a synthetic inbox: `SMTP_HOST`, `SMTP_PORT` (587 default), `SMTP_FROM`, optional `SMTP_USERNAME`/`SMTP_PASSWORD`, and HTTPS `PUBLIC_BASE_URL`. STARTTLS certificate verification is enabled. Links expire after 15 minutes, are stored hashed, and revoke prior sessions when used. New email links carry their token in the URL fragment to avoid access-log query strings. Confirm SPF/DKIM/DMARC, delivery, bounce handling and timing-based enumeration protections separately.
7. Reconcile actual granted scopes and approved operating modes, without changing them as part of this task. Direct Instagram review was in progress at the handoff; Facebook `pages_manage_posts`, TikTok upload/direct mode and X publishing access require independent evidence. A local mock success is not provider validation.

## Monitoring

`GET /health` remains a lightweight public liveness signal. `GET /internal/status`, authenticated with `SCHEDULER_SECRET` or `ADMIN_API_KEY`, reports database reachability, jobs overdue by five minutes, requests stuck for fifteen minutes and uncertain outcomes. It returns no customer text or credentials. Connect an approved monitoring service to these signals; no external monitor or alert destination has been configured here. Alert on non-OK status, unexpected 5xx/rate spikes, storage pressure and restore failures. Never log request bodies, recovery tokens, bearer headers or OAuth query strings.

The worker atomically claims each due job and each platform delivery. An interrupted/ambiguous attempt becomes `unknown` and is not automatically sent again. TikTok pending jobs are polled for completion. Reconcile uncertain outcomes with the destination before any manual retry. Do not clear publication rows to force another attempt. Post IDs and attempt history are required to avoid duplicates.

Dependency evidence is in `validation/dependency-audit.json`; the scan covers installed Python packages, including local test tools. It is not a penetration test or a comprehensive audit of vendored FFmpeg/OS components. A CI workflow runs tests, dependency checks and a vulnerability scan, but has not been pushed or executed remotely.

## Rollback

Before a future authorised release, record the deployed image/commit, schema state and backup IDs. Stop new publication/scheduling requests and pause workers if delivery behaviour is uncertain. Preserve publication/review/revocation tables and all new data. Prefer a forward fix or disabling an affected feature while retaining this security layer.

Do **not** blindly roll back to main `493fe375`: it does not honour the new session revocation/version rules, has the original password-persistence defect, and cannot read full workspace state or immutable approvals. Reverting to it can revive revoked legacy sessions and lose visibility of recent work. An emergency rollback image must retain the new authentication checks and delivery ledger; validate it in staging first. Never rotate the social encryption key or restore an old database merely to revert UI code. Restore data only for a confirmed recovery incident, accounting for writes and provider actions after the backup.

No destructive downgrade migration is provided. Additive columns/tables can remain during a UI rollback. If migration fails, stop startup, preserve the snapshot, inspect the error and repair forward before restarting. The synthetic migration test applies twice and preserves existing rows; PostgreSQL migration/restore timing remains unverified.

## Remaining engineering risks

- Full production load, adversarial security testing, PostgreSQL contention and multi-process migrations remain unvalidated.
- CSP retains `unsafe-inline` for compatibility; nonce-based templates would improve defence. Reverse-proxy timeouts, trusted proxy/IP settings, TLS and storage limits must be checked in staging.
- Images are decoded with frame/pixel limits. Videos are container-checked and their first frame decoded; full transcoding, malware scanning and isolated decoder workers are not implemented. PyAV adds a platform-specific binary dependency that must be verified on the hosting image.
- Upload quotas take a user-row lock in PostgreSQL before persistence; that lock is not enforced by the local SQLite database and still needs PostgreSQL concurrency validation. Removed attachments remain owned assets, preserving uploads. Orphan retention/cleanup needs a separately reviewed lifecycle policy.
- Recovery email delivery is synchronous and may create timing differences despite identical responses. Queueing mail, operational delivery monitoring and a timing assessment remain necessary for stronger account-recovery assurance.
- Analytics is explicitly a limited sample of dated recent posts, with available lifetime counters. It is not a historical engagement time series or a complete paginated account export.
- Full provider-specific failure reconciliation and live permission/approval validation remain external gates. Unknown outcomes intentionally prioritise avoiding duplicate posts over automatic retry.

## Reproduce local checks

Use an isolated Python 3.12 environment. Install `requirements.txt`, `pytest` and `pip-audit`, then run `python -m pytest -q`, `python -m pip check` and `python -m pip_audit`. Tests create disposable data and replace provider calls with mocks; do not import production configuration. Validate the changed JavaScript with `node --check`. Current local result: 76 passed, 17 deprecation warnings; dependency check clean and no known package vulnerabilities.


The 14 September experience-only rollback boundaries and browser evidence are in `ZOVA_EXPERIENCE_IMPLEMENTATION.md`. Do not revert the previous security candidate to undo the canvas changes. No production actions occurred.
