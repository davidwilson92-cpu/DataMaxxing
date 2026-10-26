# Zova Social — independent security assessment brief

Prepared for quotation, 26 October 2026. **Not an authorisation to begin testing.**
Client: Zova Social Limited. Contact: David, david@zova-social.com.

We need an independent, manual, authenticated assessment of our AI social-media
planning/publishing application before commercial launch. It has a shared web/API
backend on Render and an iOS application distributed through TestFlight. Stripe
is test-only and customer charging is disabled. Please quote a fixed price with
one remediation retest included and state assumptions, days and exclusions.

## Scope and approach

Proposed assets: zova-social.com web routes/API and Zova Social iOS identifier
com.zovasocial.app. Agree the exact isolated test environment, build, endpoints,
dates, tester source IPs, rate limits and authorisation letter before starting.
Default to isolated synthetic accounts/data; do not test real customer accounts.
We can provide two separate users, multiple brand workspaces, an expired/revoked
session, sample media and controlled test-provider fixtures. Any additional roles
must reflect implemented roles rather than assumed team/admin functionality.

Map coverage to relevant OWASP ASVS and MASVS requirements, with explicit tested,
not-tested and not-applicable results. Include:

- Cross-account/brand reads and writes, guessed IDs, exports, draft/media access,
  schedule/strategy/voice persistence and authorisation at queued dispatch.
- Password reset, verification, session invalidation, race/replay, optional MFA,
  rate limiting and recovery. Do not change real-user passwords.
- OAuth state/PKCE, browser binding, account confirmation, callback substitution,
  Instagram's two routes, cancellation and iOS universal-link/web handoff.
- Upload ownership, signed URL expiry/substitution, content-type/path handling,
  SSRF, unsafe links/XSS, CSRF, headers/CSP and file/parser resource limits.
- Explicit publishing review, mutation after review, duplicate/ambiguous outcomes,
  disconnect/deletion races and scheduled authorisation. Simulated provider sends
  by default; public posts require separately approved account/content.
- Stripe webhook authentication/replay, test/live separation, billing bypass and
  price/account integrity, without any real charge or subscription.
- AI prompt/data boundaries, third-party text injection and unauthorised disclosure
  or actions; scoped bounded testing without sending actual customer content.
- iOS Keychain, app/web trust boundaries, URL handling, transport, secrets in builds,
  session storage, logout, logs/screenshots and backup exposure.
- Privacy exports/erasure, telemetry/log leakage, dependency and relevant source
  review. Infrastructure permissions/secrets review is read-only unless agreed.

## Rules of engagement

No denial of service, broad brute force, destructive migration, live erasure,
real charge/post/message, credential harvesting, persistence or customer-content
exfiltration. Do not attack Apple, Meta, X, TikTok, OpenAI, Stripe, Render or other
third-party infrastructure; only our integration boundaries and expressly approved
test accounts are in scope. Stop on cross-customer access, unexpected external
effect or instability, preserve minimal evidence and contact David privately.
No public disclosure or uploads to public scanning services.

Use individual time-limited access, minimum privileges and a secure exchange for
credentials. Never ask for the owner's main password or copy production secrets
into the report. Agree confidentiality, subcontractors, processing locations,
report/evidence retention and secure deletion. Proposed tester raw-evidence
deletion: 30 days after accepted retest, subject to the signed agreement.

## Required deliverables and acceptance

1. Scope/limitations, exact tested version, methodology and coverage matrix.
2. Executive risk summary; each finding has severity, affected feature, minimal
   reproduction, redacted proof, business impact and concrete remediation.
3. Immediate private escalation for critical/high findings; no silent withholding
   until the final report.
4. Remediation retest with exact fixed version and pass/fail per original finding.
5. Named qualifications and relevant web/API/iOS/OAuth experience; independent
   identity and business insurance. CREST accreditation or equivalent demonstrated
   competence is useful; do not represent a badge as proof the app is secure.

Release criterion: no unresolved critical/high finding without a separately
documented, accountable risk decision; medium/low items have owners and dates.
Passing is evidence for a particular scope/version, not a guarantee of no defects.
We will supply known limitations privately so they are assessed, not excluded.

Please return price/currency/tax, earliest dates, tester/team, manual effort,
web/API/iOS split, staging requirements, coverage exclusions, retest scope,
evidence custody and terms. Owner selects supplier and budget before appointment.

[NCSC penetration testing guidance](https://www.ncsc.gov.uk/guidance/penetration-testing).
This brief has not been sent; no independent assessment has been completed.

## Quotation candidates (no endorsement or appointment)

Public service descriptions checked 26 October 2026:

- [Cobalt mobile assessment](https://www.cobalt.io/services/application-security/mobile-app-pentest):
  offers human-led iOS testing and linked web/API scopes. Ask for a one-off scoped
  quote with retest rather than assume a platform subscription is appropriate.
- [Kobalt application testing](https://kobalt.io/pentest/): describes startup/SMB
  web and mobile scopes. Ask for a combined Zova-specific quote; displayed web
  packages do not establish the cost of web plus API plus iOS.

These are different companies. Compare named tester competence, manual effort,
actual coverage, evidence protection, retest, total cost/tax and timing before
selection. No price commitment, message, data upload or access grant was made.
