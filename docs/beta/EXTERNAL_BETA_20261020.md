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
| Exact candidate | Bounded follow-up on the previously validated `45d4d3b` candidate | Record final commit and all required application, PostgreSQL and native checks |
| Staff directory | Reproduced unverified signup claiming an allowlisted address; access now requires verified mailbox ownership | Regression and deployment verification; staff MFA remains a separate commercial gap |
| Disconnect | Local unlink clears tokens, cancels unsent jobs and unused approvals, and preserves in-flight/unknown receipts | Ownership, reconnect and concurrency regression; provider-side revocation remains separate and is explained |
| Monitoring | Embedded scheduler now records durable progress; probe rejects stale/incomplete documents, broken workers, old usage reservations and missing recovery-email configuration | Install an approved alert route and prove delivery/acknowledgement; a passing unit test is not monitoring coverage |
| Charges | Production inspected: subscription enforcement false; Stripe mode and live-checkout flags unset (defaults off) | Recheck after deployment; never enable payments for this beta |
| Password recovery | Production has no SMTP host/from configuration | Configure the owner's mail provider and prove a reset email arrives, is single-use and invalidates old sessions |
| Upload persistence | Render production has a 1 GB disk mounted at `/app/uploads`; daily snapshots visible through 20 October | Database/key/media restoration rehearsal; do not restore an old snapshot over production |
| Publication backlog | Production status: zero overdue/stuck jobs; one historical unknown outcome | Investigate read-only; keep no-resend protection until provider evidence resolves it |
| TikTok | Live developer version has `user.info.basic,video.upload`, Direct Post off; `video.publish` revision still In review. Production uses inbox mode | Provider approval of the production revision, verified media prefix, controlled configuration and reconsent before feed publishing |
| iPhone | Build 9 is Internal-only; replacement export is external-eligible without public App Store submission | Build uploaded/processed; exact-device sign-in, cancellation, account switching and return from each supported social |
| Apple external access | External Beta App Review and reviewer metadata needed | Apple approval before inviting external testers; never make testers App Store Connect administrators |
| Tester support | Tester brief below; existing in-app Help and TestFlight feedback | Confirm support mailbox is monitored, name response owner, choose first small cohort |

## Provider scope to communicate honestly

| Platform | Beta journey | Limits / acceptance |
|---|---|---|
| Instagram | Professional Business/Creator connection, reviewed feed/Reel/Story selection | Personal profiles cannot use the publishing API. Stories/account permissions are checked by the provider. iPhone return acceptance pending |
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
