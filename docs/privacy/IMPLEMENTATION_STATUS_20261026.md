# Commercial assurance implementation — 26 October 2026

Client: Zova Social Limited. Owner: David, david@zova-social.com.
David confirmed public support email support@zova-social.com. Business postal
address and receiving Gmail account type remain unconfirmed; the email response
does not supply those facts. Quote reply-to remains david@zova-social.com.

## Completed

1. **Internal retention policy adopted.** David explicitly approved policy version
   `2026-10-26-v1` and only the tested expired-token cleanup. Active drafts,
   strategy/voice, native refresh-reuse evidence and unresolved publication records
   remain protected. Other retention category purges are not enabled.
2. **Expired-token cleanup performed on production.** One transactional batch
   removed 88 expired records across the strict allowlist: 77 OAuth states, one
   verification token, three reset tokens and seven expired revocation records.
   The subsequent read-only audit returned zero eligible records. This is a
   completed operator run, not a daily automated retention programme.
3. **Supplier register prepared.** It maps data, roles, official supplier terms and
   account-specific verification requirements, including support mail forwarded to
   Gmail. Public availability of a DPA is not proof of the applicable signed terms.
4. **Fresh production component recovery exercised.** All 44 tables/623 rows
   matched, 41 encrypted values verified and 25 available media files restored.
   Four historical files are missing, so the overall result remains incomplete.
   There were no source writes/provider calls, app startup or network listener.
   Disposable customer scratch and temporary official tools were removed.
5. **Independent quotes requested.** Owner-approved scope messages sent to Cobalt
   and Kobalt. Resend reports both delivered; this confirms delivery to receiving
   mail servers, not that a person read them or agreed to quote. Replies go to
   david@zova-social.com. No credentials, customer data or private findings sent;
   no purchase, subscription, testing permission or access grant.

## Verification

Reviewed operator-code candidate: `70713cf65c6cc6c9682ee65998396a94bf885a7c`.
Application runtime stays `a9fe5a7a4724231b3491517abed35224f3f8d011`.

- [Application CI](https://github.com/davidwilson92-cpu/DataMaxxing/actions/runs/40309377569):
  passed; 709 SQLite tests (two skips), 710 PostgreSQL tests (one skip), synthetic
  restore, browser/client checks, hosting image smoke and dependency audit.
- [Native CI](https://github.com/davidwilson92-cpu/DataMaxxing/actions/runs/40309377558):
  passed simulator tests/release compilation. No new iOS binary issued.
- Focused local retention/deletion/recovery set: 35 passed. Retention tests cover
  cutoff boundaries, active-state preservation, approval guard, batch limit,
  idempotence, read-only audit and rollback.
- Production health after operations: HTTP 200. Stripe mode test, live checkout
  false, plan limits false. Customer charges/enforcement and paid monitor remain
  off; Render retained. No new hosting resources or production application deploy.

Evidence: [operation receipt](evidence/operations-20261026.json),
[recovery receipt](evidence/recovery-20261026.json),
[expired-token audit](evidence/retention-cleanup-20261026.png),
[delivered quotes](evidence/security-quotes-delivered-20261026.png),
[sent message](evidence/security-quote-message-20261026.txt).

## Remaining before full closure

| Remaining work | Next concrete step | Owner/dependency |
| --- | --- | --- |
| Public privacy identity | Supply a publishable business/service address and verify company details | David; requested in chat |
| Support-mailbox arrangement | Confirm personal Gmail versus Workspace; assess applicable contract and choose business mailbox if needed | David; requested in chat |
| Privacy/supplier review | Verify actual account DPAs, settings and transfers against register; obtain scoped privacy review | David/adviser; no contracts accepted on his behalf |
| Other retention controls | Implement reviewed routine metadata/log/support purges, cadence and exception evidence; update public notice only after verification | Engineering + privacy review; outside the token-only purge approval |
| Missing historical media | Recover four originals/older backup or record an accountable irrecoverable-loss decision | David/engineering; do not fabricate or silently erase evidence |
| Full disaster recovery | Approve exact isolated target/cost, restore compatible managed DB/media backups, recover keys independently, replay external deletion/revocation journal and verify isolated usable app | David + operations; fresh logical rehearsal alone cannot close this |
| Independent assessment | Compare incoming fixed-price quotes, select budget/supplier, agree written test scope, perform test and remediate/retest | David + independent supplier; quotes only authorised |

The recovery targets remain proposals (one business day usable service, maximum
24 hours lost content); neither a measured SLA nor owner approval is inferred.
The existing 79-item follow-up register is preserved. Internal checks and this
pack do not constitute independent security certification or legal sign-off.
