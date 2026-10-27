# Native QA gap fixes — 27 October 2026

Follow-up to NATIVE_QA_REVIEW_20261027.md. The owner explicitly requested fixes to
the recorded gaps. External release remains on hold and customer charges stay off.

## Implementation and validation history

Candidate 9e62dbc adds:
- A single sentence beside the X selector describing a single update or connected
  thread, plus the same explanation in Guide.
- Explicit 44pt secondary targets for brand/history, calendar navigation and
  attachment removal. Calendar cells have guaranteed minimum width/height.
- Semantic text styles in Next Move, calendar and save/approval footer; rows reflow
  at accessibility sizes. Performance metrics use one column at these sizes.
- A calendar that retains its seven-day layout while allowing horizontal scrolling
  when the user's larger text needs more room.
- Studio composer inside the scrolling content in landscape/accessibility sizes;
  landscape typing hides the header to keep input/actions reachable.
- Honest connection progress and specific no-Facebook-Page guidance.
- Six additional simulator journeys: X wording/targets, largest Dynamic Type,
  product landscape with keyboard/send, voice scan/reopen, schedule edit/list
  navigation and protected deletion entry. Fixtures are DEBUG-only and cannot
  contact real accounts or publish.

Authentication, ownership/brand checks, Keychain/session storage, explicit
publication review, unknown-outcome protection, server routes and billing
contracts remain unchanged.

Further review found that the native deletion form discarded the server's status
receipt after submitting. The follow-up candidate retains a session-only link on
the signed-out confirmation screen. Only an exact same-origin status path with a
64-character lowercase hexadecimal receipt is accepted; queries, fragments and
other paths/hosts are rejected. The receipt is cleared when starting sign-in and
is not stored with another account. Confirmation distinguishes closed access from
pending data erasure. A synthetic UI journey and URL-boundary tests cover it;
these do not execute production erasure.

## Validation

- Focused local account/scheduling/social-return/deletion regressions: **72 passed**,
  two dependency deprecation warnings, 120.77 seconds.
- [Application CI40576732269](https://github.com/davidwilson92-cpu/DataMaxxing/actions/runs/40576732269):
  **727 SQLite / 728 PostgreSQL passed**, browser/client checks, synthetic recovery,
  hosting-image audits and limited-beta guard passed.
- Native CI40576732230 passed **39 unit / 16 UI tests** and Release compilation
  for 9e62dbc. Screenshots revealed a real remaining large-text issue despite
  those passes: tab labels wrapped into many lines, consuming too much height.
  The original SwiftUI-only test override also did not reach presented sheets.
- Follow-up constrains only tab-label text and provides Apple's Large Content
  Viewer for navigation; app content continues to scale. This follows Apple's
  [custom tab-bar guidance](https://developer.apple.com/documentation/swiftui/view/accessibilityshowslargecontentviewer()).
  The UI test now launches with the UIKit content-size preference and asserts
  that the presented Next Move title scales, rather than merely launching a
  sheet under an override. Landscape captures wait for loaded content.
- Follow-up candidate validation, visual review and signing remain pending.
  Do not use either build-12 or 9e62dbc results as proof of the follow-up changes.

The b450725 follow-up passed application CI40579704797 (727 SQLite / 728
PostgreSQL) and all 40 native unit tests. Native UI CI40579704520 passed 14/16:
the deletion test queried a Link although the captured hierarchy showed a
Button with the exact receipt identifier and correct signed-out message; the
large-text calendar test used only vertical swipes although day 1 was outside the
horizontal viewport. Neither failure is treated as a pass. Corrections query
the actual control and exercise both calendar axes, then select the day. The
receipt label now has a 44pt hit area; large-text Studio has a shorter readable
placeholder and header labels retain their full height. A fresh run is required.

## Production reconciliation (read-only)

The original workbook tester's record was identified directly:
- Schedule 1, draft 45, owner 19; created 25 October at 05:41 UTC.
- Cancelled 25 October at 06:00 UTC; publication ledger 10 for draft 45 is also
  cancelled.
- No active scheduled deliveries anywhere in production at the check.
- The existing pending and unknown publication records belong to other owners;
  they were not resent, cancelled, erased or declared resolved.

**TC-45 cleanup warning is resolved at this observation.** The cancellation was
already present; no customer data mutation was needed.

Planning observation before owner approval (now completed below):
- Account 21, access revoked; due 3 November at 13:27 UTC, not overdue.
- No drafts, uploaded media, social connections, subscriptions or publications.
- Read-only erasure plan has no blockers.
- The operation still requires the tested maintenance/drain/retention procedure,
  active-store verification, a completion receipt and an external restore-exclusion
  record. Backups retain their normal expiry; this does not remove social posts.
- Owner confirmation requested before the maintenance window and irreversible
  erasure. Until approval/execution, do not mark the case complete.
- Review evidence: evidence/native-qa-20261027/deletion-plan.png.

## Real-account acceptance

At planning time the owner was asked to verify Facebook login → Page selection → Zova confirmation
→ native return, and real caption scanning → populated voice → reopen, on native
build 12. That build uses the same backend/authentication contracts. An answer
supports only the actual checks reported; fixture success is not real provider
success.

At that planning stage no new TestFlight binary or tester notification had been issued. Preserve the seven original bugs/five observations/57 original statuses
and all 79 separate commercial findings; record subsequent evidence below.

## Further validation and correction

Candidate 07d9994 passed all 40 unit tests and 15 of 16 UI journeys in each of
native CI40583125563 and PR CI40583134183. Both failures are retained as failures.
The push runner exposed an invalid one-third-size accessibility coordinate space
following simulator rotation/relaunch. The independent PR run reached normal
portrait geometry and exposed a real empty-Studio scroll problem: automatic
bottom scrolling placed the input above the visible scroll area at AX5.

Candidate 9504809 scrolls an empty accessible Studio to the top of its composer;
focus also keeps the input visible, while the header makes room above the keyboard.
The test now requires the input to be immediately hittable rather than attempting
to scroll past it. The largest-text journey runs before orientation changes, and
the landscape journey terminates its app before restoring portrait to isolate
simulator state. No target-size, keyboard or calendar assertions are removed.
Fresh full validation passed; see the final evidence below.

## Gap traceability after implementation

| Original item | Change or additional evidence | Remaining boundary |
| --- | --- | --- |
| UX-05 | Short single-post/thread explanation beside the X selector and in Guide. | Passed exact-candidate validation below. |
| TC-53/54/56 | Semantic type, adaptive rows, minimum targets, scaled calendar, scrollable landscape/AX composer, compact tabs with Large Content Viewer. | Exact-candidate UI validation passed; physical-device layout acceptance remains useful. |
| BUG-01 / TC-50 | Protected deletion initiation retains a validated receipt and describes pending erasure honestly. | Approved account 21 erasure completed and verified below. |
| BUG-02 / TC-43/44 | Existing guards retained; native schedule edit/cancel journey passes. Backend regression changes the actual scheduled time. | Phone picker-change acceptance, not live provider delivery. |
| BUG-05 / TC-46 | Added two-saved-post navigation and schedule-edit-to-Studio coverage passes. | No claim of a new tester-reported phone pass. |
| BUG-06 / TC-48 | Synthetic scan changes saved voice fields and reopening retains them. Existing backend persistence/empty/error cases pass. | Owner reported the requested connected-account check completed. |
| BUG-03 / TC-33 / UX-03 | Specific no-Page guidance and honest connection progress; existing bound login/return protections retained. | Owner reported the requested Facebook check completed. |
| TC-45 | Exact original schedule and publication reconciled as cancelled; no active schedules. | Resolved at the read-only observation; unrelated uncertain publications untouched. |
| BUG-04 / TC-31 | Saved strategy revision and stale-context guards retain passing evidence. | No guarantee every AI suggestion meets subjective expectations. |
| BUG-07 | Public Help returns HTML without login; native welcome exposes it. | Existing checked correction retained. |

The original 57 statuses remain historical. This follow-up does not turn synthetic
checks into live-provider evidence or close the separate 79 commercial findings.

## Final validation and operational evidence

Validated runtime: **95048097f5c57646b865387d193f0a2693ec6ec9**.
- Native push CI40586221324: **40 unit and 16 UI tests passed**, iPhone Release
  compilation passed. Includes actual UIKit AX5 text settings, presented sheets,
  two-axis calendar navigation, keyboard input/send and landscape product journeys.
- Application CI40586221444: **727 SQLite / 728 PostgreSQL passed**, browser/client,
  synthetic recovery, hosting-image package audit and exact limited-beta guard passed.
- PR native CI40586232192 initially hit an XCTest screenshot-service timeout in
  the landscape journey (not an app assertion); failed job was rerun once.
  The rerun passed all 40 unit / 16 UI tests and Release compilation at
  21:56:38 UTC. Both results remain documented.
- Inspected AX5 Studio input/keyboard, Next Move, Schedule, Performance and Account,
  the deletion receipt screen, and landscape Schedule/Performance/Account/keyboard.
  The first landscape Studio attachment captured its loading transition; the later
  keyboard/send capture and passing journey establish interactive Studio behavior.
  No screenshot of the transition is presented as a loaded-screen layout pass.

Owner answered **Done** to the combined request to complete native build 12 Facebook
login/Page selection/final confirmation/return, and scan populated voice/reopen.
This records owner-reported completion of those requested checks, not independent
provider observation or a new public publishing test. Candidate uses unchanged
provider and backend contracts.

Owner approved the maintenance window and erasure for account 21. The existing
helper completed `BETA-ERASURE-20261027-21` at **21:39:45.685460 UTC**. Read-back active
store verification and public completion receipt passed; separate review-account
export digest and unrelated delivery statuses remained unchanged. Zero pending
account-deletion requests remained. No customer email or social post was sent.

Production remained pinned to **2de31e1** throughout. Maintenance deployment
`dep-dbghhd0473hc73b4ttl0` started the paused process at 21:34:26 UTC. Authenticated
proof showed account-erasure mode and disabled scheduling, public login returned
503, and the prior publishing heartbeat preceded maintenance. After the required
five-minute drain and erasure, resume deployment `dep-dbghl56tlv9c739ormf0` was live
at **21:42:28 UTC**. Authenticated proof then showed maintenance false and scheduler
embedded. Public health/login returned 200, Studio redirected 303, and unauthenticated
native session access returned 401. Stripe mode stayed test, subscription enforcement
false and live checkout false. The worker heartbeat resumed; seven published, one
cancelled, one pending and one unknown publication remained; no active schedules.

A restricted, fsynced completion journal exists on the persistent upload disk and
survived resume. A separate ACL-restricted local restore-exclusion index is outside
the repository/database. Any restore must reapply this erasure before traffic.
Existing backups expire normally. Evidence images contain no opaque receipt.

Codemagic build `6ae11bc3206ce93970c6a317` signed exact runtime 9504809;
checkout SHA and exported metadata were verified. Upload of **0.1.0 (13)**
succeeded at 21:51:43 UTC, delivery UUID `1ef3a4d0-7500-44ac-baa8-1172d2db5097`.
Apple completed processing and the existing Zova Social Internal Beta group was
assigned. At 22:01 UTC its Builds page explicitly showed **0.1.0 (13) — Testing**.
Testing notes are saved. Owner can update without deleting the app. No external
group was assigned to build 13 and no external Notify Testers action was taken.
Build 12 remains externally Approved/held; existing external build 11 is unchanged.
Evidence: `evidence/native-qa-20261027/zova-build13-internal-testing.png`.
