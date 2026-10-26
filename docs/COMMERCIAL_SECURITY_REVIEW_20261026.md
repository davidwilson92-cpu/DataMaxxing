# Commercial engineering review — 26 October 2026

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
| High | Local upload URLs were permanent bearer links; raw delivery did not check a registered asset or active owner. | Owner access or a filename-bound HMAC URL expiring within one hour is now required. Provider URLs are refreshed at dispatch. Check registered assets, active owners, file containment/type/size; reject symlinks and external-file reads. Tests cover anonymous/other-account access, expiry, tampering, substituted filenames and deactivated owners. |
| Medium | Upload storage budget was filtered to the selected brand. | Sum the explicitly identified user's uploads across all brands under the existing user lock. Cross-brand exhaustion and another user's independent allowance tested. |
| Medium | AI insights missed the stricter AI request bucket. | Use the same route classification for AI permission and AI rate limiting. Rejection tested before handler execution. |
| Medium | Studio recent-post links escaped HTML but did not reject executable URL schemes. | Permit HTTPS URLs without embedded credentials; reject javascript/data/relative URLs. Regression test added to CI. |
| Medium | Privacy text omitted the account AI choice and incorrectly described strategy confirmation as a search trigger. | Describe opt-in/withdrawal, named operational providers, actual research trigger, temporary media links, original metadata and assisted deletion limits. This factual correction does not substitute for a lawful-basis/retention/legal review. |
| Low | Brands and account-deletion pages returned raw authentication errors to signed-out browsers. | Redirect to login, preserving API/callback error semantics. |
| Low | Local raw-media paths could be retained in application access logs. | Redact filenames as well as existing secret query strings. |
| Low | Unused unrestricted remote-fetch helper and duplicated local file checks. | Remove the unused helper; share the managed-file boundary check. |

No schema, provider permission, customer data, pricing enforcement or native
runtime change is part of these bounded fixes. No real post was sent. S3 public
base configuration remains a separate deployment concern; the current Render
local-media protection must not be represented as a universal private-bucket audit.

## Evidence and limits

- Before changes: 689 application tests passed, 2 skipped (SQLite). This is baseline evidence, not the changed candidate's acceptance.
- Focused new and affected tests: 27 passed across navigation, media privacy and TikTok Direct Post; 17 passed across media/privacy/storage/security controls. Overlapping counts are not additive coverage.
- Six focused browser-JavaScript tests passed, including unsafe-link rejection and AI permission behavior.
- Render read-only smoke: 15 public/protected URLs returned expected pages or login redirects, with no-store and frame-denial headers. This checks the existing live version, not deployment of these changes.
- Synthetic authenticated crawl renders 22 customer pages and checks at least 50 distinct internal route/form/static references. It does not follow real OAuth authorizations, click destructive controls or prove external sites never fail.
- Local dependency audit after aligning with the repository's already-pinned Pillow 13.0.0 and pip 26.2: no known vulnerabilities reported; pip dependency consistency check passed. Initial findings were stale local packages, not newly verified production vulnerabilities.
- Existing tests cover recovery/session revocation, cross-account/workspace access, immutable publishing review, provider error ambiguity, deletion and Stripe test/live isolation. Provider fixtures are simulated; historical live acceptances are recorded separately.
- Native source review confirms WhenUnlockedThisDeviceOnly, non-synchronizing Keychain storage, owned-origin navigation, PKCE/state and one-use handoff checks. No phone or Apple account was operated in this review.
- The previous native CI run 40233634882 failed because its first loopback WebKit GET lacked the expected cookie; other recent runs passed. A fresh run is required. Do not dismiss this as infrastructure-only without evidence.
- Full changed-candidate application/PostgreSQL/image/native results are recorded in the acceptance addendum below when available.

## What still prevents an unconditional commercial sign-off

1. **Privacy decisions and evidence (owner/legal):** approve a data inventory with purposes/lawful bases, actual retention periods, supplier processing agreements and international-transfer safeguards. The current generic retention wording is not a completed retention programme. Implement approved purge periods and verify backup expiry/deletion replay. Do not invent legal assurances in the public notice.
2. **Operational ownership (owner/engineering):** complete an incident/restore exercise with measured recovery targets and deletion queue ownership. Synthetic restore coverage and yesterday's backup are useful but do not prove a current production recovery drill. The owner declined the paid monitor; it remains inactive. Record a workable manual response arrangement or separately approve monitoring.
3. **Security assurance (engineering/independent reviewer):** finish privileged-account MFA/least-privilege evidence, rotation inventory and independent penetration testing. Broad inline-script CSP, incomplete tamper-resistant security audit coverage, full dependency locking, upload metadata/scanning policy and load testing remain retained findings. These are not all evidence of an exploitable defect, but have not been closed by this review.
4. **Exposed tester credential (owner):** the existing tracker records a credential in a tester recording. Restrict/redact the recording and rotate the affected password; do not put its value in evidence. This review does not assert that remediation occurred.
5. **Release acceptance (engineering/tester):** run exact-candidate PostgreSQL/image/native checks; investigate any repeated native cookie failure. Verify signed local media fetching in the deployed environment without a real post. Confirm all legacy local-media URL origins match PUBLIC_BASE_URL. Before switching raw-media access rules, drain in-flight provider fetches and retain rollback evidence. A server deployment does not create a new TestFlight binary.

The 79-item historical register is retained unchanged; individual bounded fixes
above do not automatically resolve those broader findings. Render remains the
host. Live charges, subscription enforcement and paid monitoring remain disabled.

## Review references

- [OWASP ASVS 5 file handling](https://github.com/OWASP/ASVS/blob/master/5.0/en/0x14-V5-File-Handling.md)
- [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
- [ICO: the right to be informed](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/individual-rights/right-to-be-informed/)

These references inform the review, not an assertion of audited compliance.

## Changed-candidate acceptance

Pending exact-candidate validation. The changes are not yet published.
