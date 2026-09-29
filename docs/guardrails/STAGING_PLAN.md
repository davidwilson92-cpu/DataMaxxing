# Isolated Zova Social staging proposal

Status: deferred by the owner on 28 September 2026 until the app is approved.
No resources created or existing services changed; spending is not authorized.

## Saved follow-up

After app approval, revisit this plan with the owner, recheck current pricing and
obtain explicit cost approval before creating the separate staging app/database.
The meaning and evidence of app approval must come from the owner; do not infer
it from passing tests, a merged PR or platform status. Continue guardrail fixes
that can be tested locally in the meantime. Environment separation, migration,
load and recovery evidence remain open. This deferral is not a release waiver.

## Initial scope

Create a new Docker web service `zova-social-guardrails-staging` from
`davidwilson92-cpu/DataMaxxing`, branch `codex/production-guardrails`, and a new
PostgreSQL 18 database `zova-social-guardrails-staging-db`. Use Oregon for both,
manual deployments, and synthetic accounts/data only. Start with one web process
and the existing embedded worker; this is suitable for functional/migration
validation, not proof of independent worker availability or production scale.

Neither existing service will be repurposed. `zova-cs-staging` runs the separate
customer-service repository; the TikTok sandbox was observed pointing at the
production database. Do not copy either service's environment variables.

## Isolation and acceptance before application use

- A new database name/user and new session, encryption and operations secrets.
  Verify the database host/identifier is different from production before any
  app import, because the existing application creates/migrates tables at import.
- No production data, OAuth tokens, provider client secrets, payment secrets,
  email credentials, storage bucket or admin API key copied across.
- Initially no live social, payment, AI or email integrations. Use isolated test
  adapters/accounts only after explicit configuration. Do not claim full provider
  validation while these integrations are disconnected.
- Restrict database network access and place the web service behind a staging
  access gate before accepting test users. This gate is separate from Zova login
  and does not introduce customer MFA.
- Use a staging-only media location with synthetic uploads. Add separate object
  storage before persistence/private-media validation; ephemeral local files do
  not satisfy those requirements.
- Run register integrity, application/PostgreSQL tests and image checks before
  staged deployment. The production gate remains blocking and must not be
  weakened to permit staging. Stage only the reviewed candidate branch; never
  switch the production service to that branch.
- Verify no external writes, separate cookies/hostnames, fresh empty database,
  cross-account denials and rollback/recovery on synthetic records. A separate
  worker, restricted database roles/RLS, monitoring, load and recovery exercises
  follow as later increments.

## Cost proposal

Render prices checked 28 September 2026:

| Resource | Plan | Base monthly price (USD) |
|---|---|---:|
| Web service | `0.5c-512mb` | $7 |
| PostgreSQL | `0.1c-256mb` | $6 |
| Initial total | Before storage/usage/tax | $13 |

Source: [Render pricing](https://render.com/pricing). Additional database storage
is listed at $0.30/GB; bandwidth and build usage can add charges. Confirm the
actual provisioning summary and included storage before submitting. No workspace
plan upgrade is proposed. Render's network-isolated environment feature is a
separate paid-plan feature; independent data/secrets alone do not establish that
network control. This proposal does not claim full environment compliance.

Proposed authorization: up to $20/month additional recurring infrastructure base
charges, with approval again if the quoted setup exceeds that amount or needs a
workspace upgrade. This is an approval ceiling, not an automatic billing cap.
Do not provision until the owner approves. A dedicated worker (currently another
$7/month at the smallest paid plan), private media storage and wider load tests
are outside this initial setup and need separately reviewed costs.

Render's free PostgreSQL expires after 30 days and free web instances have
limitations, so the free tier is not proposed for ongoing migration/recovery
work. [Free-tier limitations](https://render.com/docs/free).

## Current release status

MFA remains deferred by the owner; existing Zova sign-in is unchanged. Other
security work continues. Staging provisioning does not make the application
production-ready or close the open assessment by itself.
