# Commercial operations and release boundaries

This is an undeployed candidate. It does not authorise charging, social posts, grants, invitations or a production deployment.

## Support ownership

Service operator: Zova Social Limited (or configured legal entity). Routing: `SUPPORT_EMAIL`, falling back to the configured privacy contact and then the previously used Zova support mailbox. The **named responder, coverage hours and escalation backup have not been confirmed**; do not publish an SLA. Assign them before a paid cohort. Customer UI now links directly to support without requesting passwords/tokens/card details.

Triage: account access → identity-verified recovery; billing → verified Stripe state and event history; publication unknown → reconcile exact destination before retry; save conflict → preserve/download current work before replacing it. Escalate suspected cross-account access immediately, preserve evidence without customer text in logs, stop affected operations and notify the designated owner. Do not clear ledgers to force a retry.

## Subscription lifecycle

Basic £9.99/month or £99/year; Premium £19.99/month or £199/year. Seven-day trial for eligible new subscribers. Plan limits and subscription enforcement stay off for testing. Test records never grant live entitlements.

Plan changes are **assisted and not implemented in the self-service portal**. Support must not promise an automatic upgrade/downgrade. Before adding that flow, define effective date, proration, explicit price approval and which brand remains writable. Never delete excess brands or credentials to enforce a downgrade. Existing quota code limits new consumption; it does not solve downgrade selection. Returning cancelled customers do not receive another trial.

With enforcement enabled in a future authorised rollout, existing guards admit active/trialing subscriptions and reject protected operations otherwise. Saved data is retained. No overdue-payment grace period is implemented; choose and test one before offering it. For now, explain payment recovery and direct to existing portal/refresh paths. Cancellation stops renewal at the verified end date. No overage billing. Legacy Custom GPT access is outside Studio allowance enforcement and needs a separate reviewed policy.

Advertised prices/Stripe prices must match. Current test prices use inclusive tax behaviour; this is not evidence of VAT registration or configured live tax collection. Owner/tax review must reconcile terms, receipts and checkout before activation. Keep the offer's testing/test-checkout/live states consistent; do not switch flags to make screenshots look complete.

## Recovery and email verification

Recovery preserves hashed, single-use 15-minute links and session revocation. Delivery now runs after the response rather than blocking it. Tokens are invalidated on known mail failure. A mail attempt stores only ID, status and timestamp. Failed attempts in 24 hours and stale sending attempts appear in operational status. The process-local background task is **not a durable mail queue**: a crash before task start can lose mail; request a fresh link. Never claim delivered from SMTP acceptance alone.

Email verification is optional and user-initiated, with account-bound, single-use expiring links. Confirmation requires the same signed-in account and explicit POST; a scanner GET cannot consume it. Link tokens are in fragments. `EMAIL_VERIFICATION_REQUIRED_FOR_CHECKOUT=false` preserves existing access. When enabled later, it gates new checkout, not login, existing sessions, connected accounts or drafts. Existing provider-authenticated emails are preserved.

External gate: configure approved SMTP and HTTPS base URL, SPF/DKIM/DMARC, synthetic inbox delivery and bounce monitoring. No production SMTP/DNS changes were made. Rate limits and per-account verification requests reduce repeated sends but are not complete Sybil/trial-abuse protection.

## Cost and service signals

AI calls record provider-reported token counts, model, outcome and configured GBP estimate, plus a rate snapshot/date. No prompts, output or provider error bodies are recorded. Network failures/unpriced models remain unknown-cost calls. Failed operations may still cost money even when allowance reservations are released. Cost records do not grant/refund usage or change billing. Telemetry failure logs a generic warning and must not cause a duplicate generation.

Set `AI_GBP_RATES_JSON` from dated official tariffs and documented currency assumptions. Schema per exact model: `{input, cached_input, output, as_of, source}`, amounts GBP per million tokens. No current provider rates are hardcoded or claimed here. `/internal/status` exposes estimated monthly total, unpriced calls, coverage and configurable `AI_MONTHLY_ALERT_GBP` threshold. `scripts/check_service.py` is a read-only monitor probe returning attention/exit 1; no external alert destination has been configured or contacted. Also signals overdue/stuck/unknown publications, stale billing reconciliation and mail failures. A quiet webhook feed alone does not prove failure; stale active-account reconciliation is a signal, not a webhook outage diagnosis.

Run `scripts/unit_economics.py docs/unit_economics_inputs.json` to produce 12 normal/allowance/retry scenarios across both plans and intervals. Unknown inputs produce null margins. Populate AI, social, storage, hosting, payment, tax and support assumptions from actual sources. Tests use explicitly synthetic numbers to prove arithmetic/alert behaviour, not profitability. Investigate old reservations; do not automatically release uncertain publication spend.

## Assisted export/erasure

`nova.data_lifecycle` is an operator helper, not a public deletion endpoint. Verify the requester's identity, retention exceptions and case reference first. Use a dedicated unscoped database session; `export_account` covers all brands and excludes password hashes, encrypted credentials and verification tokens. The export contains customer personal data: deliver through an approved secure channel, not application logs. It includes a media manifest; package verified media separately.

`erase_plan` is read-only. It blocks active billing, unresolved/scheduled publishing, linked legacy credentials and remote/unexpected media storage. Resolve these with authorised provider actions first. For local storage, pause application writes and workers, provide a verified case and explicitly acknowledge `writes_paused=True` to `erase_local_account`. It revokes account access, records progress, removes only root-contained local uploads and scrubs active content/voice/connection identifiers. It retains pseudonymous billing/usage/delivery records under the reviewed retention schedule. A failure leaves the request in erasing state; rerun after resolving the fault. Never report whole-service erasure from `active_store_erased`.

S3/object-version/CDN deletion, backups and third-party posts require separate verified workflows. Restore procedures must reapply completed deletion requests before reopening service. No production export/erasure was executed. Synthetic tests verify secret exclusion, user isolation, access revocation, file removal and billing/storage blockers.

## Production gates and rollback

Still required: named operations owner; monitored public staging with durable Stripe webhook acceptance/retries; approved live billing/tax configuration; provider approval evidence; real email delivery; managed database+upload+key restore and timed RPO/RTO drill; customer study; measured costs.

Before a release, stop concurrent migration starts, snapshot database and uploads, verify encryption/session-secret recovery and rehearse additive tables. Existing CI restore compares identity/credential/workspace rows and table counts; it is not a managed production restore. New tables: AI calls, product events, email verification and mail delivery. Existing customer rows/secrets are not rewritten.

Rollback to the preceding brand-aware candidate is supported for these additions: disable optional measurement/verification flags, retain additive tables, and revert this increment's UI/routes. Do not revert to a pre-brand or pre-session-revocation binary. Pending verification links may become unavailable during rollback; recovery and existing passwords remain intact. Never restore an old production database merely to undo UI changes. Historical costs and billing/publication ledgers must remain available.
