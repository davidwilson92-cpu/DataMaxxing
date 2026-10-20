# Cloud credits and migration preparation — updated 20 October 2026

## Decision and current state

Render stays live. Phase 0 (portable runtime and planning) has begun. The owner is signed in to AWS Startups through Builder ID and the Founders package is saved in the application flow. No AWS billing account has been selected/linked, and no paid service, final application submission, DNS change, customer-data copy or migration cutover has occurred. Commercial gates in `../COMMERCIAL_READINESS_20261019.md` are still open.

**Provisional first credit application: AWS Activate**, because this application already has a container, PostgreSQL and an S3-compatible storage adapter. This is an engineering-fit inference, not a claim AWS is cheapest. Compare the actual AWS award and post-credit estimate with Microsoft before selecting a destination. Minimal beta cost remains the owner preference. Do not buy an elaborate platform merely to spend credits.

## Verified credit routes

Checked against current primary sources on 19 October 2026; AWS Founders eligibility and application steps rechecked on 20 October. Amounts are ceilings in USD, not awarded cash or a promise to Zova.

| Programme | Current offer / meaningful eligibility | Decision |
|---|---|---|
| [AWS Activate](https://aws.amazon.com/startups/credits/) | Self-funded Founders starts at $1,000; selected applicants may reach $5,000. Portfolio up to $200,000 requires an Activate Provider Org ID. Pre-Series B, founded within ten years, qualifying previous-credit history and a paid-tier AWS account are listed requirements. | Best initial fit if self-funded. Larger amount needs a genuine eligible investor/accelerator referral. AWS paid-tier account acceptance/billing is a separate step, never silently enabled. |
| [Microsoft for Startups](https://learn.microsoft.com/en-us/startups/microsoft-for-startups/overview) | Credits grow with verified progress and Azure adoption, up to $150,000. Investor-network benefits may accelerate access. Company-owned software, private for-profit status, supported country, no Series C and lifetime Azure free-credit limits apply. | Strong alternative; do not assume the headline sum is available immediately. |
| [Google for Startups Cloud](https://cloud.google.com/startup) | Start tier $2,000: founded within two years, working MVP/business model and plans to seek venture funding. Funded tiers $200,000–$350,000 require qualifying funding. Larger two-year awards have second-year coverage limits. | Consider if eligibility and award are stronger. Do not describe the maximum as automatic or as full second-year coverage. |

Direct OpenAI usage is billed separately today. Moving the web host does not automatically make those invoices credit-eligible, and changing AI vendors is not part of this migration. Obtain written coverage/expiry/exclusions from the selected programme.

## Application facts and current handoff

Owner confirmed self-funded and started August 2026. On 20 October the owner provided **david@zova-social.com** as the company email and said, **"No credit history for the company (new company)."** App Store Connect identifies the existing developer organisation as ZOVA SOCIAL LIMITED. Product start date is not proof of the legal incorporation date. Preserve the owner's wording: a borrowing history and previous promotional cloud-credit awards are different facts. Confirm the latter against the actual application question before making an eligibility declaration; do not turn the statement into an unsupported financial or credit-award attestation.

| Field | Prepared answer / evidence |
|---|---|
| Product and website | Zova Social; https://zova-social.com |
| Business contact | david@zova-social.com — owner supplied 20 October |
| Developer organisation | ZOVA SOCIAL LIMITED — observed in Apple; confirm legal fields if the form requires them |
| Funding | Self-funded — owner confirmed; owner selected No Funding and No Valuation in AWS, with no external funding date; no investor/accelerator Org ID supplied |
| Founded | 12 August 2026 — owner entered directly in AWS; not independently verified as a legal incorporation date |
| Founder / role | David Wilson / CEO — owner changed job-title field; duplicate founder role aligned to match |
| Headcount | 1–10 band — owner entered directly; no exact number claimed |
| AWS experience | 0–2 years — owner entered directly; this does not establish an existing hosting account |
| Planned launch | 1 December 2026 — owner entered directly; a target, not evidence of commercial readiness or a deployment instruction |
| Product stage | Existing web beta and iPhone TestFlight client; not a public App Store release |
| Credit history | Owner states no company credit history; prior promotional-credit question requires precise confirmation |
| Revenue, customer numbers, address, registration number | Not established; do not invent |
| Intended AWS billing account | Not yet selected or linked |

The owner completed Builder ID sign-in. **Founders** was selected and saved. The owner supplied the missing profile and product answers directly and continued, then both saved steps were reopened and reviewed. Founder contact is David Wilson/company email, founder Yes, job title and founder role CEO, Zova website, Social Media Marketing customers, scalable architecture / technology choices / reduced burn as goals, and cost management / containers / security as technical interests. Unsupported optional LinkedIn/public-profile/service selections remain blank.

Product values are consumers and businesses; web browser and mobile app; launched initial product and iterating; AI/ML to improve the product; planned launch 1 December 2026. The owner replaced the initial Bootstrapped selection with **No Funding**, selected **No Valuation**, and left external-funding dates inapplicable. Preserve those choices. AWS spend share is **I'm not sure** because no cloud estimate or commitment exists; optional marketing budget remains blank.

Both steps are confirmed saved. The application is now at `https://startups.aws.com/credits/apply/link-aws-account`. AWS requires a hosting/billing account separate from Builder ID. The console sign-in tab is open; the owner has been asked to sign in to the intended existing account, or report that none exists. No linking/verification control has been activated. No billing account identity, final submission or credit award has been verified. Screenshot: `social-proof/aws-account-link-needed-20261020.png`.

AWS's [current credits page](https://aws.amazon.com/startups/credits/) says to use a professional email for Builder ID, while its [application guide](https://aws.amazon.com/aws-startups/learn/applying-for-aws-activate-credits-a-step-by-step-guide/) describes Builder ID as a personal profile and requires the business-domain email for the Activate profile/application. Reuse an existing Builder ID if the owner already has one; the supplied company-domain email is the application contact. Do not create duplicate cloud billing accounts. Account IDs, verification codes and keys stay out of public documentation.

Next steps: establish the intended existing AWS hosting account or prepare a new company account if the owner confirms none exists; review account identity and the actual linking permission before action-time confirmation, then show the completed application and terms before final submission. A paid-tier account is listed as an Activate requirement, but that is not permission to provision services or accept unbounded charges. Award amount, expiry, coverage and a budgeted migration still need evidence. [AWS promotional-credit terms](https://aws.amazon.com/awscredits/) checked 20 October (page updated 24 September): charges can arise for ineligible services and use beyond available credit, and taxes are excluded. Review these with the final application; do not claim the account cannot incur charges.

Draft factual product description for the application:

> Zova Social is an AI-assisted social media workspace for creators and small brands. Customers develop a content strategy, draft and refine platform-specific captions, inspect uploaded media, review destinations and content, and publish or schedule approved posts. The product has an existing web beta and an iPhone TestFlight client using a shared Python backend. PostgreSQL stores account and workflow records; social tokens are encrypted. We are preparing managed cloud hosting, private media storage, separate publishing workers, monitored recovery and a controlled commercial release.

The application's 250-character field contains this saved 249-character version:

> Zova Social helps creators and small brands plan, draft and publish social posts with AI. Web and iPhone beta share a Python/PostgreSQL backend. We plan container hosting, private S3 media storage and publishing workers; captions use the OpenAI API.

Do not claim revenue, number of customers, external funding, security certification, public TikTok paid-content acceptance or App Store release. Those statements require evidence. The short description is saved in the draft application; the final application has not been submitted.

## Low-complexity target

- One versioned container image for web and publishing worker; one web instance initially, one worker. Avoid Kubernetes/microservices for this beta.
- Managed PostgreSQL with encrypted storage/backups, restricted runtime and separate migration identity. Confirm selected region and data-processing terms before copying data.
- Private object storage, blocked public ACLs, short-lived authorised delivery links, checksum manifest and restore evidence. Preserve TikTok's verified media domain/path and all existing media references.
- Managed secret storage and workload identity where supported. Preserve `SESSION_SECRET` and credential-encryption keys during cutover; changing them invalidates sessions/decryption. Inventory by secret name, never log values.
- TLS/custom domain `zova-social.com` stays stable, including OAuth callbacks, Apple association, Stripe webhook and provider media endpoints.
- Health checks, protected readiness/status, structured request references, alerts, log retention and budget notifications. A status endpoint is not an alert service.

AWS implementation candidate: a small managed container deployment, managed PostgreSQL and S3; choose the smallest supportable service combination after a regional estimate. Azure Container Apps/PostgreSQL is an alternative requiring storage and platform validation. Neither target is provisioned.

## Portability controls implemented in this increment

| Control | Current compatibility | Future separate services |
|---|---|---|
| `ZOVA_SCHEDULER_MODE` | `embedded` default retains the existing single-web scheduler; `disabled` stops polling | `external` stops the web poller and rejects the old manual dispatch endpoint |
| Worker command | Not running separately | `python -m nova.worker`; PostgreSQL session advisory lock permits one poller; heartbeat reports missing/stale/error |
| `ZOVA_SCHEMA_MODE` | `initialize` retains current additive preparation | `verify` checks tables/columns without startup DDL; explicit offline preparation first |
| Pool budget | Defaults preserve size5 + overflow10 | Configure size/overflow/timeouts/recycle and declared web replica count; startup checks web+worker pool demand against `DB_CONNECTION_BUDGET` |
| Shared media | Existing storage untouched | External mode requires configured private S3-compatible bucket and no public-base setting |

`scripts/prepare_database.py --confirm-target-backed-up` requires an explicit target database and must run with writes stopped using the migration identity. It does not certify a backup or install complete RLS/grants. Schema verification checks compatibility, not full constraints/indexes/permissions. CI now includes a dedicated synthetic recovery fixture for credential decryption, passwords, live/revoked sessions, uncertain publications, withdrawn AI permission and media checksums after pg_dump/pg_restore; require its receipt before counting it as passed. This tests a preserved filesystem path, not S3 IAM or a changed storage layout. A configured bucket is not proof of its actual IAM/public-access policy. These are preparatory controls, not a finished distributed scheduler or safe-cutover certificate.

## Migration stages and evidence required

1. **Eligibility and economics:** owner facts, signed-in existing cloud account, application/terms review, written credit award with expiry/exclusions. Compare twelve-month cash cost before/after credits. Do not start chargeable services on an assumed award.
2. **Budgeted isolated environment:** cost-approved small staging stack; no production grants/mail/posts. Use synthetic accounts, mock providers and non-production secrets. Apply exact candidate image and offline schema; service identities cannot run DDL. Inspect effective grants/private-bucket settings.
3. **Recovery rehearsal:** restore a synthetic PostgreSQL dump, media files and isolated encryption keys. Compare row counts, owner/brand boundaries, workspace/media checksums and credential decryptability. Test refresh/session continuity, stale jobs, partial results, and worker death after provider acceptance. Never re-send uncertain publications.
4. **Production-like rehearsal:** with specific authorisation, validate a protected production backup copy using controlled access and deletion/retention rules. Record measured recovery time and data-loss point. Confirm signed media URLs/verified provider prefix, OAuth callback routing, Apple association and webhook signatures/replays.
5. **Cutover:** release gates closed, exact source/image digest approved, verified fresh backup, low-traffic window. Pause writes and old dispatch; wait for in-flight outcomes and reconcile ledger. Copy final delta, verify manifests, start target web with dispatch disabled, smoke-test domain/TLS/auth/read-only flows, switch traffic, then enable exactly one target worker. Keep old service isolated as rollback infrastructure.
6. **Observe and retire:** monitor acknowledged alerts and customer flows through the agreed window. Retain old encrypted backups only under the approved policy. Delete old hosting/resources after verified recovery and provider acceptance; do not leave public media or unused credentials behind.

## Cost worksheet before provisioning

Estimate the same workload on each eligible provider: web CPU/RAM/hours, always-on worker, PostgreSQL instance/storage/backups, media GB/requests/egress, load balancer/NAT/public IPv4, secret/log/monitoring charges, email, support and VAT/FX. Include temporary double hosting during migration and separate OpenAI invoices. Record monthly run rate after expiry and a 2× usage case. [AWS pricing calculator](https://calculator.aws/), [Azure calculator](https://azure.microsoft.com/en-us/pricing/calculator/), [Google calculator](https://cloud.google.com/products/calculator).

No numeric cost saving is claimed without a chosen region, measured workload, award and quote. Budget alerts do not necessarily stop spending. Agree a cap and a safe response plan before provisioning.

## Rollback and stop conditions

Before target writes: route back to Render with existing data untouched, stop target dispatch. After target writes: pause both dispatchers/writes, reconcile new records and uncertain provider outcomes before restoring routing; never point customers to an older stale database. Reuse the same session/encryption authority and retain ledgers. Do not run two active worker owners across different databases. A rollback to pre-consent code must keep AI blocked or retain the consent gate. Stop on missing media, failed key decryption, session loss, failed ownership check, unexpected charge or unconfirmed publication.
