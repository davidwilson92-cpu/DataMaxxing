# Native QA gap fixes — 27 October 2026

Follow-up to NATIVE_QA_REVIEW_20261027.md. The owner explicitly requested fixes to
the recorded gaps. External release remains on hold and customer charges stay off.

## Candidate changes

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
pending data erasure. An offline UI journey and URL-boundary tests cover it;
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

## Production reconciliation (read-only)

The original workbook tester's record was identified directly:
- Schedule 1, draft45, owner19; created 25 October at 05:41 UTC.
- Cancelled 25 October at 06:00 UTC; publication ledger10 for draft45 is also
  cancelled.
- No active scheduled deliveries anywhere in production at the check.
- The existing pending and unknown publication records belong to other owners;
  they were not resent, cancelled, erased or declared resolved.

**TC-45 cleanup warning is resolved at this observation.** The cancellation was
already present; no customer data mutation was needed.

One existing verified account-deletion request remains:
- Account21, access revoked; due 3 November at 13:27 UTC, not overdue.
- No drafts, uploaded media, social connections, subscriptions or publications.
- Read-only erasure plan has no blockers.
- The operation still requires the tested maintenance/drain/retention procedure,
  active-store verification, a completion receipt and an external restore-exclusion
  record. Backups retain their normal expiry; this does not remove social posts.
- Owner confirmation requested before the maintenance window and irreversible
  erasure. Until approval/execution, do not mark the case complete.
- Review evidence: evidence/native-qa-20261027/deletion-plan.png.

## Real-account acceptance

Owner has been asked to verify Facebook login → Page selection → Zova confirmation
→ native return, and real caption scanning → populated voice → reopen, on native
build12. That build uses the same backend/authentication contracts. An answer
supports only the actual checks reported; fixture success is not real provider
success.

No new TestFlight binary or external tester notification has been issued by this
record. Preserve the seven original bugs/five observations/57 original statuses
and all79 separate commercial findings; record subsequent evidence below.
