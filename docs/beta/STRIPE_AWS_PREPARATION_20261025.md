# Stripe sandbox and AWS preparation — 25 October 2026

Owner requested Stripe with free/dummy tester payment, then full AWS migration
before publication. Preparation only: no hosted billing configuration, AWS
resources, DNS cutover, provider posts, real customer charges or iOS release.

## Tester payment choice

Use **Stripe sandbox**, not a live coupon. Card `4242 4242 4242 4242`, any future
expiry and any three-digit CVC. Use synthetic address details; never a real card.
The optional web checkout remains separate from free beta access. Subscription
enforcement and customer charges stay disabled; a test trial ending or cancellation
does not revoke beta access. iPhone beta access remains free without a Stripe
purchase flow. Commercial iOS monetization needs its own Apple/IAP assessment.

The existing application already supports four GBP prices, verified webhook
reconciliation, test/live isolation, retry/duplicate-subscription protection,
the Stripe billing portal and cancellation. Historical **local sandbox** acceptance
is in STRIPE_PROVIDER_VALIDATION_20260918.md; it is not proof of a currently
configured hosted endpoint. Added test-card help appears only when test checkout
is configured/enabled; it is absent from live mode.

Remaining provider work after sign-in: inspect the existing sandbox/account,
reuse or verify its catalog, prepare the real HTTPS `/billing/webhook` endpoint
with the correct event/API version and endpoint-specific secret, transfer test
credentials through approved secure settings, verify all four real hosted test
checkouts, signed webhook delivery/retry and portal cancellation. Never rely only
on the success redirect or prior local/mocked tests.

Reference: https://docs.stripe.com/testing

## AWS preparation

See `infra/aws/README.md` for cost, exact staged execution, retention, rollback and
outstanding gates. Candidate CloudFormation starts with zero tasks and publishing
disabled; one beta task maximum. It uses encrypted private RDS/EFS, TLS ingress,
scoped workload roles, digest-pinned images and retained data stores. Existing
upload paths are preserved. Both web and iPhone retain `zova-social.com`.

The AWS-only entrypoint loads settings without printing secrets, preserves session
and encryption keys, rejects static AWS keys/execution injection/live Stripe keys,
and requires hostname-verified RDS TLS. The public official London CA is bundled.
Infrastructure is now included in the exact release-scope hash. A separate CI
job validates generated CloudFormation and its London resource schemas.

**Not yet verified:** AWS account/credit/Free-plan status, permission and budget
approval, complete provider/settings/sequence inventory,
image startup with real EFS/UID permissions, backup/restore/copy manifests,
migration write freeze, DNS, real hosted payment and device/provider journeys.
No AWS migration or billing activation should be described as completed.

Read-only Render inventory subsequently confirmed PostgreSQL 18.6, database size
12,244,671 bytes, 29 local media records under `/app/uploads`, no path escapes,
four already-missing files and no size mismatch among present files. No S3 is
configured; hosted Stripe is off/unconfigured and outgoing email is configured.
The template now matches PostgreSQL 18.6 / postgres18; AWS's official release
notes confirm support. Actual London account provisioning remains unverified.
The separate cloud-migration write freeze is implemented without granting
account-erasure authority. It requires disabled scheduling, blocks OAuth and
customer/provider writes, keeps health/protected status available and defaults
on in the zero-task AWS template. It is not yet deployed to Render. Visitor
identity is taken only from the trusted ALB subnet chain; a forged leading IP
does not bypass rate limits. Cloudflare proxy-chain acceptance remains a gate
if proxying is retained rather than direct ALB DNS.

https://docs.aws.amazon.com/AmazonRDS/latest/PostgreSQLReleaseNotes/postgresql-versions.html

The current Free-plan decision is still in force until the owner changes it.
Prepared London estimate is roughly US$60–75/month before credits/tax/variable
usage, not a guarantee or hard cap. No awarded cloud credits are assumed.

All 79 known commercial findings remain retained. Commercial readiness is false.
