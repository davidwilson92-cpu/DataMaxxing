# External beta release checklist — 20 October 2026

## Release boundary

The owner authorises tested updates on Render and preparation of external TestFlight.
Keep customer charges and subscription enforcement disabled. No cloud migration,
new paid staging, replacement of existing grants, or public test posts are authorised
by the deployment request. Preserve existing users, encrypted connections, uploads,
sessions, both Instagram login routes and immutable publication approvals.

This is a controlled external beta, not commercial certification. All 79 items in
the deferred register remain retained. Do not merge the unfinished broad
account/service/RLS migration. Historical provider successes do not establish every
format, account type or iPhone callback.

## Evidence and release gates

| Gate | Evidence / current state | Acceptance needed |
|---|---|---|
| Exact candidate | Runtime `7048c35` live; required application/PostgreSQL CI `39492645799` and native CI `39492645584` passed. Submitted native build 10 remains based on `25374db`; native app source is unchanged | This does not establish physical-device/provider acceptance |
| Staff directory | Reproduced unverified signup claiming an allowlisted address; verified-mailbox protection and regression are now deployed | Staff MFA remains a separate commercial gap |
| Disconnect | Deployed local unlink clears tokens, cancels unsent jobs and unused approvals, and preserves in-flight/unknown receipts; ownership and reconnect regressions passed | Provider-side revocation remains separate and is explained; validate live provider cancellation without disturbing customer grants |
| Monitoring | Embedded scheduler records durable advancing progress; probe rejects stale/incomplete documents and unhealthy dependencies. Separate read-only access is implemented. New Render cron is prepared, not created | Owner approves cost/read-only access and confirms alert destination; prove delivery/acknowledgement. Historical uncertainty/unpriced usage remains visible |
| Charges | After deployment, live runtime confirms billing off, checkout false, enforcement false | Never enable payments for this beta |
| Password recovery | Restricted Resend SMTP is live. Owner confirmed two delivery checks in Gmail. Actual reviewer verification was delivered, confirmed and rejected on reuse; actual reset request was delivered and opened the reset form | Owner creates the prepared separate recovery-test account and completes its live reset; verify old-session invalidation. Preserve Apple's reviewer password |
| Upload persistence | Render has a 1 GB disk with daily snapshots; database UI shows 3-day PITR. Fresh isolated logical restore matched 44 tables / 401 rows, 39 encrypted values and 16 available uploads. Four old August files are missing, with no current draft/review/schedule references found | Full media result remains incomplete; retain records and seek older backup/originals. Managed PITR and independent key recovery remain unproved. Never restore over production |
| Publication backlog | Zero overdue/stuck jobs. Read-only reconciliation leaves Instagram publication-2 from 22 September unknown; no provider receipt identifier was stored | Manual destination evidence needed; preserve no-resend protection and historical ledger |
| TikTok | Live developer version has `user.info.basic,video.upload`, Direct Post off; `video.publish` revision still In review. Production uses inbox mode | Provider approval of the production revision, verified media prefix, controlled configuration and reconsent before feed publishing |
| iPhone | Build 10 processed, notes saved and existing internal group assigned. Native tests passed 16 unit/1 UI plus release compile. Owner confirms automatic Instagram return in response to the build9 check; same return code in10 | Other providers, cancellation/account switching and current build 10 device acceptance remain open; no real publishing proof inferred |
| Apple external access | Build10 assigned to external group, **Waiting for Review**. Reviewer is isolated, email verified and has one saved synthetic pending idea. Owner completed fresh login with the same password saved in Apple; Account identity and draft access verified. Review notes and external-beta metadata saved | Obtain Apple approval and close remaining invitation gates; no external testers invited |
| Tester support | support@zova-social.com is Active; delivery check shows Delivered and Forwarded to Gmail; owner confirms receipt; live Help links to the new address | Confirm support monitoring arrangements, then choose first small cohort |

## Provider scope to communicate honestly

| Platform | Beta journey | Limits / acceptance |
|---|---|---|
| Instagram | Professional Business/Creator connection, reviewed feed/Reel/Story selection; automatic iPhone return owner-confirmed | Personal profiles cannot use the publishing API. Stories/account permissions are checked by the provider. Cancellation, account switching and publishing are separate checks |
| Facebook | Connect and select a managed Page; review exact destination and content | Pages, not personal timelines. Historical owner Page text test does not prove unrestricted customer permissions |
| X | Connect exact account; single post/thread and media options supported by its grant | Provider access/credit/rate limits apply; cancellation and return still need current phone acceptance |
| TikTok | Approved inbox upload; creator completes posting in TikTok | Do not advertise production Direct Post or paid-partnership publishing while the live scope revision is pending |

For all platforms: no action posts without final confirmation. A pending receipt is
not a published post. Unknown outcomes must not be resent. Only confirmed failed
destinations are eligible for retry; changing reviewed content requires a new review.

## Operational acceptance

1. Verify the exact deployment hash, HTTPS, dependency readiness, an advancing worker
   heartbeat and the no-charge configuration.
2. Confirm password recovery, support email and an alert destination. Send one
   authorised synthetic alert, acknowledge it, then restore normal monitoring.
3. Record managed database backup retention, last backup, upload snapshot and key
   recovery location without storing secrets in this document. Restore only into an
   isolated disposable destination with publishing/email/AI disabled.
4. Use two unrelated synthetic accounts and two brands to check drafts, files,
   reviews, exports, connection cancellation and recovery isolation.
5. Complete a real iPhone run and record build, iOS version, account type and each
   step's result. Simulator, desktop browser and provider mocks are separate evidence.
6. Invite the first small cohort only after access/recovery/device blockers are
   closed and Apple approves external testing. Keep a single issue list with owner,
   severity, reproduction, build and evidence.

## Stop conditions

Pause invitations and the affected feature for cross-account access, lost saved
content, a charge, an unapproved/duplicate post, repeat sign-in failure, missing
uploads or an unexplained provider outcome. Retain evidence and customer data.
Do not make a failing readiness check green by removing it.

## Rollback

Prefer reverting the affected presentation or operational change while retaining
the AI-consent boundary and staff verification. The pre-candidate server was
`419d452`; deploying it directly removes the new AI-consent enforcement, so it is
not a safe blanket rollback once customers have made privacy choices.

Keep PostgreSQL data, upload disk, encryption/session keys, publication receipts
and additive tables. Never restore stale production data as a code rollback and
never replay unknown posts. Set the scheduler to disabled before changing worker
ownership; resume only one dispatcher after inspection. Older internal TestFlight
build 9 is a device fallback, not an externally distributable build.

## Status discipline

Track implementation, automated tests, device/provider acceptance, Render deployment
and Apple review separately. This document does not claim an external beta is open.
Update this checklist and the main handoff with final receipts and unresolved gates.

## Verified release receipts

- Render deploy `dep-dbbp1k0ae00c73abch8g`, service `srv-d9rqg6navr4c739thoeg`:
  exact runtime `25374dba138c8c50ebeb5b0224b7d4af55b180bd` live on 20 October.
  Dependency readiness 200, schema present, embedded worker idle and no-charge
  configuration verified after deployment.
- [Application CI](https://github.com/davidwilson92-cpu/DataMaxxing/actions/runs/39453432880):
  SQLite 563 passed/2 skipped; PostgreSQL 564 passed/1 skipped; 13 client groups
  and Studio harness; dependency audit reported zero known findings; synthetic
  restore, container smoke and exact scope passed.
- [Native CI](https://github.com/davidwilson92-cpu/DataMaxxing/actions/runs/39453432747):
  16 unit tests, 1 UI test and iPhone release compilation passed.
- [Codemagic build](https://codemagic.io/app/6ad5cbbeadaac76a4f1f8525/build/6ad7907b454d2506f7ab80b9):
  0.1.0 (10), exact source `25374db`, successful Apple upload. App Store Connect
  now shows Ready to Submit, UUID `49d32ac0-86d6-43bc-a0e3-8d82d9101af1`.
  What to Test saved; existing internal group assigned. External group
  `f3f15099-0bec-49dc-8347-cd55beb805c0` has no testers. The owner completed
  submission; Apple now shows **Waiting for Review** for build 10. Review access,
  notes, external-beta description and support Feedback Email were checked.
- Existing live account remains signed in with its Facebook, X and TikTok
  connections visible. The synthetic 393px Studio consent-decline/reload/retry
  check preserved the pending message. No real posts or provider grants changed.
- Owner reports automatic return to Zova after final Instagram connection
  confirmation. This closes the reported Instagram return defect for that test,
  not the other providers or all device scenarios.
- Render email activation `dep-dbbqk2tpkucs73eg704g` is live on the same exact
  `25374db` runtime. Restricted domain-only sending credential, verified
  STARTTLS and two SMTP sends succeeded. Resend reports Delivered and Cloudflare
  reports Forwarded for both. Recovery readiness is true, with zero mail failures
  or stuck mail. Owner confirms both arrived in Gmail. The real verification/reset
  flow remains unverified.
- Support address activation `dep-dbbqni1jfumc73d36gr0` is Live at 18:59:07 BST
  on the same runtime. Signed-in Help uses support@zova-social.com; session
  continuity and the free-beta message remain intact.

- Security-form fix `b131f23af2dbd95c0609da5b18944753daaac3bc`:
  required CI `39482173393` passed (SQLite 564/2 skipped, PostgreSQL 565/1
  skipped, 18 client tests/groups plus Studio, synthetic restore and scope).
  Render `dep-dbbruo5pkucs73dudgv0` became Live at 20:23 BST. Actual readiness,
  no-charge settings, worker health and verification single-use were checked.
  Both reviewer verification and reset emails show Delivered in Resend. The
  reset form opens, but no password change was performed. See
  `SECURITY_FORM_ACCEPTANCE_20261020.md` for exact receipts and limits.
- Apple submission record checked at 19:47 UTC on 20 October. Screenshot:
  `social-proof/apple-external-beta-waiting-review-20261020.png` (ignored).
  Submission is not approval. No invitation, public App Store release, real post,
  grant change, customer charge or password reset occurred.

Automated CI recovery uses disposable synthetic data. The later controlled live
logical restore is documented in `BETA_CHECKS_20261020.md`; its overall media result
is incomplete because four historical files are missing. The delivered live reset
email does not establish a completed reset or revoked sessions. A green CI run does
not establish alert delivery, managed PITR, provider approval or physical-device acceptance.
