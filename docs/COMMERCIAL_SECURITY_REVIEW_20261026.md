# Commercial engineering review — 26 October 2026

**Publication update:** the owner subsequently authorised deployment. Runtime
a9fe5a7 is now live on Render, with post-release checks passed. See
[release acceptance](beta/SECURITY_RELEASE_20261026.md). The pre-release notes
below remain the historical review; this deployment does not close the broader
commercial-readiness conditions.

## Verdict

Continue the controlled beta with customer charges disabled. Do not describe this
review as commercial security certification or claim that every social-provider
journey has been exercised live. The review found and fixed concrete defects, but
privacy operations, independent security assurance and release evidence remain
conditions of a paid commercial launch. UX is left to the external tester.

Scope: authentication/recovery/native handoff, account and workspace isolation,
uploads and delivery, AI permission and budgets, publishing confirmation and
duplicate protection, billing test/live separation, logs, privacy disclosures,
customer routes/forms/assets, dependency inventory and native key storage.

## Findings and bounded fixes

| Priority | Finding | Change and verification |
| --- | --- | --- |
| High | A reset racing with sign-in could let a checked old password mint a session at the newer credential version. | Conditional credential updates and session issuance bound to the verified version prevent both interleavings. New hashes use scrypt N=2^14/r=8/p=5; legacy hashes verify and upgrade on successful login. Existing sessions remain valid for work-factor-only upgrades. |
| High | Local upload URLs were permanent bearer links; raw delivery did not check a registered asset or active owner. | Owner access or a filename-bound HMAC URL expiring within one hour is now required. Provider URLs are refreshed at dispatch. Check registered assets, active owners, file containment/type/size; reject symlinks and external-file reads. Tests cover anonymous/other-account access, expiry, tampering, substituted filenames and deactivated owners. |
| Medium | Upload storage budget was filtered to the selected brand. | Sum the explicitly identified user's uploads across all brands under the existing user lock. Cross-brand exhaustion and another user's independent allowance tested. |
| Medium | Anonymous multipart uploads could reach parsing before route-level sign-in checks. | Reject signed-out upload requests in outer middleware before reading the body; a regression test fails if parsing or the downstream handler runs. |
| Medium | AI insights missed the stricter AI request bucket. | Use the same route classification for AI permission and AI rate limiting; put native token/refresh requests in the authentication bucket rather than the shorter general-mutation bucket. Rejection tested before handler execution. |
| Medium | Studio recent-post links escaped HTML but did not reject executable URL schemes. | Permit HTTPS URLs without embedded credentials; reject javascript/data/relative URLs. Regression test added to CI. |
| Medium | Privacy text omitted the account AI choice and incorrectly described strategy confirmation as a search trigger. | Describe opt-in/withdrawal, named operational providers, actual research trigger, temporary media links, original metadata and assisted deletion limits. This factual correction does not substitute for a lawful-basis/retention/legal review. |
| Low | Brands and account-deletion pages returned raw authentication errors to signed-out browsers. | Redirect to login, preserving API/callback error semantics. |
| Low | Local raw-media paths could be retained in application access logs. | Redact filenames as well as existing secret query strings. |
| Low | Unused unrestricted remote-fetch helper and duplicated local file checks. | Remove the unused helper; share the managed-file boundary check. |

No schema, provider permission, bulk customer-data migration, pricing enforcement or native
runtime change is part of these bounded fixes. No real post was sent. S3 public
base configuration remains a separate deployment concern; the current Render
local-media protection must not be represented as a universal private-bucket audit.

## Evidence and limits

- Before changes: 689 application tests passed, 2 skipped (SQLite). This is baseline evidence, not the changed candidate's acceptance.
- Focused new and affected tests: 27 passed across navigation, media privacy and TikTok Direct Post; 17 passed across media/privacy/storage/security controls. Overlapping counts are not additive coverage.
- Six focused browser-JavaScript tests passed, including unsafe-link rejection and AI permission behavior.
- Render read-only smoke: 15 public/protected URLs returned expected pages or login redirects, with no-store and frame-denial headers. This checks the existing live version, not deployment of these changes.
- Synthetic authenticated crawl renders 22 customer pages and checks at least 50 distinct internal route/form/static references. It does not follow real OAuth authorizations, click destructive controls or prove external sites never fail.
- A separate rendered-page check found no missing targets among 21 in-page fragment links across 14 pages.
- Local dependency audit after aligning with the repository's already-pinned Pillow 13.0.0 and pip 26.2: no known vulnerabilities reported; pip dependency consistency check passed. Initial findings were stale local packages, not newly verified production vulnerabilities.
- Existing tests cover recovery/session revocation, cross-account/workspace access, immutable publishing review, provider error ambiguity, deletion and Stripe test/live isolation. Provider fixtures are simulated; historical live acceptances are recorded separately.
- Native source review confirms WhenUnlockedThisDeviceOnly, non-synchronizing Keychain storage, owned-origin navigation, PKCE/state and one-use handoff checks. No phone or Apple account was operated in this review.
- Previous native CI run 40233634882 failed because its first loopback WebKit GET lacked the expected cookie. Fresh candidate run 40301485777 passed. That is fresh acceptance evidence, not a diagnosis of the earlier intermittent failure; retain it for investigation if it recurs.
- Full changed-candidate application/PostgreSQL/image/native results are recorded in the acceptance addendum below when available.

## Functional and code-quality interpretation

| Area | What the review establishes | What it does not establish |
| --- | --- | --- |
| Sign-in, recovery and account isolation | Regression coverage includes credential races, session revocation, account/brand boundaries and native handoff. | An independent penetration test or every real device/browser combination. |
| Studio, Schedule, Strategy and voice | Existing synthetic persistence/journey tests and route/form checks run with the candidate. | A new UX acceptance or a live external AI response for every journey. |
| Social connections and publishing | Provider fixtures check consent, reviewed snapshots, media URL delivery and ambiguous-result protection. | Fresh live Facebook/X/Instagram/TikTok publishing acceptance. No real post was sent in this review. |
| Billing and email | Synthetic tests cover mode separation and recovery; previous hosted acceptance remains in the dated handover. | A new real payment, live billing approval or email deliverability guarantee. Charges stay disabled. |
| Maintainability | A dedicated media-delivery module replaces an unrestricted route; common file validation and AI classification reduce duplication. New tests cover behavioral boundaries. | The large legacy application module, all duplicated legacy paths or the unfinished service/RLS migration being resolved. Avoid a broad rewrite as part of this security patch. |
| Dependencies and secrets | Current package/image audit and a narrow tracked-file scan for private keys, AWS access keys and Stripe keys provide bounded evidence. | A full Git-history secret scan, supplier assurance or proof that no undisclosed vulnerability exists. |

The test suite now resets persisted request budgets between independent tests;
actual request limits remain active within each test and in production. This
removes shared-IP leakage from high-volume native fixtures without increasing
production limits. Existing client-library deprecation warnings remain hygiene
work, not hidden test failures.

## What still prevents an unconditional commercial sign-off

1. **Privacy decisions and evidence (owner/legal):** approve a data inventory with purposes/lawful bases, actual retention periods, supplier processing agreements and international-transfer safeguards. The current generic retention wording is not a completed retention programme. Implement approved purge periods and verify backup expiry/deletion replay. Do not invent legal assurances in the public notice.
2. **Operational evidence (owner/engineering):** complete an incident/restore exercise with measured recovery targets. David is already the designated daily deletion-queue owner with a seven-day target, and the test alert to david@zova-social.com was confirmed received. Those decisions are preserved. Synthetic restore coverage and yesterday's backup do not prove a current production recovery drill or timely incident detection. The owner declined the paid monitor; it remains inactive. Record the manual health-check/incident response arrangement before paid launch.
3. **Security assurance (engineering/independent reviewer):** finish privileged-account MFA/least-privilege evidence, rotation inventory and independent penetration testing. Broad inline-script CSP, incomplete tamper-resistant security audit coverage, full dependency locking, upload metadata/scanning policy and load testing remain retained findings. These are not all evidence of an exploitable defect, but have not been closed by this review.
4. **Exposed tester credential — owner-confirmed closed:** on 26 October the owner confirmed the password was changed and the recording secured. This is owner attestation, not independent inspection of the password or recording.
5. **Release acceptance (engineering/tester):** run exact-candidate PostgreSQL/image/native checks; investigate any repeated native cookie failure. Verify signed local media fetching in the deployed environment without a real post. Confirm all legacy local-media URL origins match PUBLIC_BASE_URL. Before switching raw-media access rules, drain in-flight provider fetches and retain rollback evidence. A server deployment does not create a new TestFlight binary. Password hash upgrades are lazy on successful login/new credentials; rollback must retain support for scrypt-v2 hashes, never revert to a binary that only understands the old hash. Test the CPU profile on the Render-sized host before enabling the commercial workload.

The 79-item historical register is retained unchanged; individual bounded fixes
above do not automatically resolve those broader findings. Render remains the
host. Live charges, subscription enforcement and paid monitoring remain disabled.

## Review references

- [OWASP ASVS 5 file handling](https://github.com/OWASP/ASVS/blob/master/5.0/en/0x14-V5-File-Handling.md)
- [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
- [OWASP password storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [ICO: the right to be informed](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/individual-rights/right-to-be-informed/)

These references inform the review, not an assertion of audited compliance.

## Changed-candidate acceptance

Runtime candidate: `a9fe5a7a4724231b3491517abed35224f3f8d011` on the existing
`codex/ios-beta-20261019` branch / PR 34. This report and the continuation handover
may be updated separately without changing that validated runtime scope.

- [Application CI 40301485867](https://github.com/davidwilson92-cpu/DataMaxxing/actions/runs/40301485867): **passed**.
- SQLite: **707 passed, 2 skipped**. PostgreSQL: **708 passed, 1 skipped**.
- Interactive client and isolated Chromium checks: passed, including Studio,
  attachment handoff, Next Move, onboarding, keyboard/focus and mobile layout.
- Synthetic PostgreSQL restore: passed for credentials, sessions, revocation,
  unresolved publication, AI choice and media.
- Hosting image build/startup smoke and package audit: passed; no known package
  vulnerabilities reported. Infrastructure template validation passed without
  provisioning or changing hosting.
- Password-cost probe in the image restricted to **512 MiB / 0.5 CPU**: four
  concurrent hash-and-verify tasks completed in **4.698 seconds** total, individual
  durations 4.599–4.697 seconds. This is bounded synthetic resource evidence, not
  a production latency guarantee or full load/abuse test.
- [Native CI 40301485777](https://github.com/davidwilson92-cpu/DataMaxxing/actions/runs/40301485777): **passed**, including iPhone simulator tests and release compilation. No new binary was signed or uploaded to Apple.
- The duplicate push-triggered run 40301479522 completed PostgreSQL successfully;
  its separate browser step was still running when this report was saved. The
  complete PR-triggered application run above, for the same exact commit, passed.
- Local focused regression set: **83 passed**. Exact beta scope validation passed.

Earlier candidate failures were investigated, not ignored: an old hash-format
assertion was corrected, and persisted request counts from independent test
journeys were isolated. The final hosted application run above is green.

**Not deployed.** Live Render remains `d090e6e`; no TestFlight build was released.
Deployment still needs the media/rollback acceptance described above. No customer
charges, subscription enforcement, paid monitoring or real social posts enabled.
