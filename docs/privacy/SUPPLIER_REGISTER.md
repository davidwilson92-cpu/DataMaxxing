# Supplier and transfer register

Reviewed public primary sources 26 October 2026. Zova Social Limited / David.
Public documentation located is not proof that this specific account has accepted
the applicable terms, enabled a feature or selected a region. No new terms were
accepted in this exercise. Contract/entity/settings evidence remains restricted.

| Supplier/service | Data and purpose in Zova | Role / evidence to complete | Official reference |
| --- | --- | --- | --- |
| Render | Database, uploads, app processing, operational logs, configured secrets; hosting/backup | Processor for customer content; separate account data purposes. Existing deployment in Oregon noted in prior inspection. Confirm contracting entity, account terms, UK transfer mechanism, subprocessors, log and backup settings | [DPA](https://render.com/dpa), [trust](https://render.com/trust), [DB backups](https://render.com/docs/postgresql-backups), [disk snapshots](https://render.com/docs/disks) |
| OpenAI API | Relevant prompt/draft/strategy/voice/feedback, sampled media and public-research queries when AI allowed | Processor for submitted customer content under applicable business terms; verify account contract, region, feature retention and subprocessors. `store=false` does not prove zero retention or zero abuse monitoring. Never list social tokens as intended AI input | [DPA](https://openai.com/policies/data-processing-addendum/), [API data controls](https://platform.openai.com/docs/guides/your-data) |
| Resend | Recipient email and transactional account/reset/verification content; delivery metadata | Processor for application email; standard DPA/subprocessors located. Confirm acceptance, region, message/log retention and deletion process. Restrict staff dashboard access | [DPA](https://resend.com/legal/dpa), [subprocessors](https://resend.com/legal/subprocessors) |
| Cloudflare | Domain service, routing addresses, forwarded support-message content; website traffic only where proxy actually enabled | Verify which products are enabled and applicable processor/controller roles. Do not assume DNS registration means all customer traffic is proxied | [customer DPA](https://www.cloudflare.com/cloudflare-customer-dpa/), [privacy](https://www.cloudflare.com/privacypolicy/) |
| Google Gmail support inbox | Forwarded customer emails and attachments at the owner-controlled Gmail destination | Additional recipient omitted from the earlier short supplier list. Determine whether this is consumer Gmail or a managed business Workspace account; do not assume Workspace DPA applies to a free consumer mailbox. Review MFA, sharing, retention and business suitability | [Google privacy](https://policies.google.com/privacy), [Workspace processing terms](https://workspace.google.com/terms/dpa_terms.html) |
| Stripe, currently test-only | Email, customer/subscription references, checkout metadata; card data entered directly at Stripe | Mixed processor and independent-controller purposes; verify UK applicable agreement and transfer terms. Test mode still can contain personal data; live charges remain off | [DPA](https://stripe.com/legal/dpa), [privacy](https://stripe.com/privacy) |
| Apple / TestFlight / Sign in with Apple | Tester identity/device/build diagnostics and feedback; Apple sign-in subject/relay email if used | Distribution/authentication platform with its own purposes; record actual accepted developer terms and permitted diagnostic handling. Do not label all Apple processing a Zova subprocessor | [privacy](https://www.apple.com/legal/privacy/), [developer agreements](https://developer.apple.com/support/terms/) |
| Meta: Instagram/Facebook | Authorisation, selected professional account/Page identity, authorised post/media and available metrics | User-selected social destination; review platform/data terms and each role. Record permissions and revocation/deletion requirements. Connection approval is not a general privacy certification | [platform terms](https://developers.facebook.com/terms/), [privacy](https://www.facebook.com/privacy/policy/) |
| TikTok | Authorisation, profile, user-reviewed media/caption/visibility/disclosures and publishing status | User-selected destination; direct-post approval is distinct from supplier privacy obligations. Preserve explicit review/confirmation | [developer terms](https://developers.tiktok.com/terms/), [privacy](https://www.tiktok.com/legal/page/eea/privacy-policy/en) |
| X | Authorisation, profile, reviewed post/media and delivery/metrics | User-selected destination; applicable developer and privacy terms; preserve scoped token and deletion obligations | [developer agreement](https://developer.x.com/en/developer-terms/agreement-and-policy), [privacy](https://x.com/en/privacy) |
| GitHub / Codemagic | Source/build artifacts and signing/build secrets; developer collaboration/CI | Confirm access restrictions, developer terms, subprocessors and signing-secret handling. Production DB/uploads/customer support must not enter source, CI logs or test artifacts | [GitHub privacy](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement), [Codemagic privacy](https://codemagic.io/privacy-policy/) |

## Contract and transfer completion record (one per supplier)

Record: business account ID/reference (restricted); contracting legal entity;
services/features; controller/processor role; purpose/categories/subjects; source
and destination countries/access; current agreement version and applicability;
acceptance evidence/date; subprocessor list/review/notification arrangement;
retention/deletion/return terms; security assurance/access/MFA; transfer mechanism
and assessment; owner/review date; outstanding actions. Link to the agreement;
do not paste secret keys or customer content into the register.

Where a restricted UK transfer exists, assess the actual contracting chain and
current applicable mechanism. Server geography alone does not decide whether a
restricted transfer occurs. Do not assert every US supplier is automatically
covered by adequacy or that EU clauses alone establish a valid UK transfer.
[ICO transfer guidance](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/international-transfers/a-guide-to-international-transfers/are-we-making-a-restricted-transfer/).

The Render DPA and the located supplier DPAs are useful source material, not an
account-specific compliance opinion. Supplier subprocessor lists do not mean every
listed service receives all of Zova's data. Resolve actual feature/data flow.

## Prioritised actions

1. Verify business account/terms and UK transfer arrangements for Render, OpenAI,
   Resend and Cloudflare. Archive signed/applicable versions privately.
2. Resolve Gmail's account type and support-data arrangement. Do not migrate mail
   or purchase Workspace without an agreed plan/cost and preserve existing delivery.
3. Verify Apple/social terms and data-use restrictions; include GitHub/Codemagic
   access and secrets in the internal security register.
4. Review privacy notice and business customer processing terms with adviser.
5. Review supplier changes quarterly; subscribe to change notices only with owner
   approval where required. No notification subscriptions were created here.

Status: **register prepared; account-specific DPA/transfer verification pending**.
