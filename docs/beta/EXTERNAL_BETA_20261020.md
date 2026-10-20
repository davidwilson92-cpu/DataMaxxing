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
| Exact candidate | `25374db` live; application CI `39453432880` and native CI `39453432747` succeeded | Keep later changes separately validated; this does not establish physical-device/provider acceptance |
| Staff directory | Reproduced unverified signup claiming an allowlisted address; verified-mailbox protection and regression are now deployed | Staff MFA remains a separate commercial gap |
| Disconnect | Deployed local unlink clears tokens, cancels unsent jobs and unused approvals, and preserves in-flight/unknown receipts; ownership and reconnect regressions passed | Provider-side revocation remains separate and is explained; validate live provider cancellation without disturbing customer grants |
| Monitoring | Embedded scheduler now records durable progress; probe rejects stale/incomplete documents, broken workers, old usage reservations and missing recovery-email configuration | Install an approved alert route and prove delivery/acknowledgement; a passing unit test is not monitoring coverage |
| Charges | After deployment, live runtime confirms billing off, checkout false, enforcement false | Never enable payments for this beta |
| Password recovery | Restricted Resend SMTP is live; two authorised checks show Delivered and Cloudflare Forwarded; recovery readiness true | Owner inbox acknowledgement and real verification/reset acceptance, including single use and old-session invalidation |
| Upload persistence | Render has a 1 GB disk at `/app/uploads`; daily snapshots through 20 October; database UI shows 3-day PITR and an export from 19 October 09:03 BST | Isolated production database/key/media restoration rehearsal remains open; synthetic CI restore passed. Never restore over production |
| Publication backlog | Zero overdue/stuck jobs. Read-only reconciliation leaves Instagram publication-2 from 22 September unknown; no provider receipt identifier was stored | Manual destination evidence needed; preserve no-resend protection and historical ledger |
| TikTok | Live developer version has `user.info.basic,video.upload`, Direct Post off; `video.publish` revision still In review. Production uses inbox mode | Provider approval of the production revision, verified media prefix, controlled configuration and reconsent before feed publishing |
| iPhone | Build 10 processed, notes saved and existing internal group assigned. Native tests passed 16 unit/1 UI plus release compile. Owner confirms automatic Instagram return in response to the build9 check; same return code in10 | Other providers, cancellation/account switching and current build10 device acceptance remain open; no real publishing proof inferred |
| Apple external access | External group created with 0 testers; build10 reaches the required form; private contact entered and dedicated signup prepared | Owner completes reviewer signup and private Apple credentials; verify access and obtain Beta App Review approval before external invitations |
| Tester support | support@zova-social.com is Active; delivery check shows Delivered and Forwarded to existing Gmail; live Help links to the new address | Owner inbox acknowledgement and monitoring, then choose first small cohort |

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
  `f3f15099-0bec-49dc-8347-cd55beb805c0` created with no testers; review not submitted.
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
  or stuck mail. Owner inbox receipt and the real reset flow remain unverified.
- Support address activation `dep-dbbqni1jfumc73d36gr0` is Live at 18:59:07 BST
  on the same runtime. Signed-in Help uses support@zova-social.com; session
  continuity and the free-beta message remain intact.

All automated recovery evidence uses disposable synthetic data. A green CI run
does not establish delivered reset email, live alert delivery, managed production
restoration, provider approval or a working physical iPhone journey.
