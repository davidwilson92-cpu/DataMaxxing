# Compact social connections — 25 October 2026

Candidate `69f49bc07dc8547983164bd3552a8864bdc1e339`. **Not published.**
The live server remains d3bc09d and TestFlight remains 0.1.0 (11).

The owner confirmed the proposed cleanup after showing Facebook's connected
Page. This is a presentation update, not a new Facebook grant or publishing test.

## Changes

- Each platform has its icon/name, account identity and connection status in a
  compact row. Connect or Manage stays aligned on the right at phone widths.
- Removed the repeated account-login explanation, platform paragraphs and large
  rounded buttons from the list. Existing connection screens retain requirements
  and explain the Instagram/Facebook routes when the user starts connecting.
- Manage expands inline to show Change or reconnect and account-specific Unlink.
  Unlink is hidden until Manage opens; its consequence is stated there. Multiple
  accounts retain separate identities and exact unlink targets.
- Unconnected and unavailable setup states remain distinct. Onboarding uses the
  same compact list but does not expose unlink actions.
- Updated the public deletion guide to the new Account → Social accounts →
  Manage → Unlink path. Existing endpoints, ownership checks, workspace handling
  and scheduled-post cancellation behavior are unchanged.

## Verification

- 32 social-login/onboarding tests passed locally.
- 12 existing mobile handoff, Account refresh and voice client checks passed.
- Isolated browser checks passed at 320/390/1440px: no horizontal overflow,
  44px controls, long names, multiple Facebook Pages, touch/keyboard Manage,
  hidden unlink, account-specific form targets and workspace reconnect URL.
- A synthetic Facebook connection was unlinked through the existing form in the
  disposable local preview; other synthetic connections remained. No customer
  connection, provider permission or real post was changed.
- Browser checks initially expected a relative link and configured Facebook
  credentials. Corrected the checks to accept the real absolute workspace URL
  and the preview's honest setup-unavailable state; product behavior was correct.
- Full application CI passed on exact candidate 69f49bc:
  [push](https://github.com/davidwilson92-cpu/DataMaxxing/actions/runs/40209922826)
  and [PR](https://github.com/davidwilson92-cpu/DataMaxxing/actions/runs/40209926428).
  678 SQLite / 679 PostgreSQL tests (2 / 1 platform-specific skips), client checks,
  mobile composer and Next Move browser regressions, synthetic PostgreSQL restore,
  hosting-image smoke/audit and exact-scope gate all passed. Both dependency audits
  found no known package vulnerabilities; broader security gaps remain tracked.

Screenshots are synthetic previews:
[compact rows](evidence/20261025/socials-compact-preview.png),
[expanded Manage](evidence/20261025/socials-manage-preview.png),
[setup unavailable](evidence/20261025/socials-disconnected-preview.png),
[multiple Pages](evidence/20261025/socials-multiple-preview.png).

No backend/schema/native code change, billing activation, deployment or provider
connection test. Customer charges stay OFF, hosting stays on Render, and all 79
broader gaps and prior QA acceptance requirements remain tracked. The owner's
Facebook screenshot establishes the UI's connected status, not successful live
publication or a complete permissions audit.
