# Security form correction — 20 October 2026

## Reproduction

The owner created the dedicated Zova App Review account. Its new workspace has
no social connections. A harmless pending draft saved as draft36 and survived a
reload; Drafts shows that one draft and Performance shows the unconnected state.
No AI processing, provider grant or social post was requested.

On live runtime `25374db`, opening Verify your account email and selecting Send a
new verification link returned HTTP403, “Open Zova directly and try again.”
No verification email was sent. Recovery reset and verification pages deliberately
use Referrer-Policy no-referrer; native form POSTs can consequently use Origin null,
which the existing request middleware rejects.

This behaviour is documented in the
[Fetch standard](https://fetch.spec.whatwg.org/#append-a-request-origin-header)
and [MDN's Referrer-Policy reference](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Referrer-Policy).

## Bounded change

Verification request/confirmation and recovery request/reset forms submit with
CORS-mode fetch to their own origin. Credentials remain same-origin and the
request keeps no-referrer. The server's Origin checks are not relaxed and no
new opaque-origin exemption is added. The native handoff is unchanged.

The helper prevents concurrent/repeated dispatch while a request is pending or
successful. Failure stays on the form, retains entries in the current DOM only,
shows a text status and permits deliberate retry. It does not store or log a
password, token or response body. Off-site form actions/navigation are rejected;
the existing connect-src self CSP remains in force.

All token ownership, one-use atomic claims, expiry, password hashing, rate limits
and session-version revocation remain in the existing backend. No database,
social-provider, billing or native binary change is included.

## Acceptance evidence

- Focused synthetic Python checks: 24 passed, including recovery single use,
  session revocation, wrong-owner rejection, expiry and delivery failure.
- Five client regressions cover submission privacy, duplicate suppression,
  failure recovery, network errors and destination restrictions.
- A disposable loopback browser fixture confirmed the verification request and
  confirmation both supply the correct Origin, omit Referer, and redirect
  successfully. Reusing the same link shows a clear inline rejection.
- The fixture sends no real email and contains no customer data or credentials.
- [Required application/PostgreSQL CI 39482173393](https://github.com/davidwilson92-cpu/DataMaxxing/actions/runs/39482173393)
  passed for `b131f23af2dbd95c0609da5b18944753daaac3bc`: SQLite 564 passed/2
  skipped; PostgreSQL 565 passed/1 skipped; 18 client tests/groups and Studio
  harness; dependency audit zero known findings; synthetic restore, container
  smoke and exact scope passed. The earlier local full run had an expected
  scope-manifest failure before that manifest was reviewed/refreshed; it is
  not recorded as a clean full-suite pass.
- Render deployment `dep-dbbruo5pkucs73dudgv0` went live at 20:23 BST on
  20 October with the exact tested revision. Readiness returned 200, required
  schema was available and embedded worker was idle. Billing was off, checkout
  disabled and subscription enforcement disabled. Zero overdue jobs, stuck
  publications, failed mail and stuck mail; the historical unknown publication
  remains unchanged.
- The live reviewer verification request succeeded. Resend message
  `01a15ac4-cc7f-7d56-8e7c-98d389266898` was Delivered. Its link was opened from
  the provider's visible email preview in the same signed-in reviewer session.
  Confirmation redirected to `/account?saved=verified`; using the link again
  showed the expected inline rejection. This proves application confirmation and
  provider delivery, not a separately observed Gmail inbox receipt for this message.
- The live recovery request succeeded. Resend message
  `01a15ac8-47cb-7bf5-9758-0932385111af` was Delivered and its emailed link
  opened the reset form with the token removed from the address bar. No password
  was entered or changed. Full live reset/session-invalidation acceptance still
  requires the owner to complete credential entry and submission; equivalent
  backend cases pass in the synthetic suite.
- Evidence screenshots are in ignored `social-proof/`:
  `security-forms-live-render-20261020.png`,
  `security-form-live-single-use-20261020.png` and
  `reviewer-recovery-verification-delivered-20261020.png`. No credentials or
  email-link tokens are persisted in the evidence.

## Rollback and distribution

Build10's native binary is unchanged and can use the corrected web service.
The previous backend runtime remains `25374db`; reverting to it would reintroduce
the security-form failure and require pausing invitations until corrected.
Preserve database records, email configuration, uploads and existing session keys.
Do not weaken origin checks as a workaround.

Apple reviewer credentials remain private to App Store Connect. The available
Apple form still had an empty password after the owner reported completion;
username was filled and the owner was asked to enter the existing review password.
Do not submit unverified login details or claim Apple approval before its receipt.
