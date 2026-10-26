# Stripe test payments on Render — 25 October 2026

Owner chose Render instead of AWS and approved creating the test webhook and
storing the existing test API key/signing secret in the existing Render service.
No AWS provisioning, real customer charging, subscription enforcement or plan
limits are authorised by this test connection.

## Configuration

- Stripe account: `acct_1U3LuQCpb4pF4cGH`, test mode only.
- Basic: GBP 9.99 monthly (`price_1UGlAnCpb4pF4cGHGEvcPxYi`), GBP 99 annual
  (`price_1UGlAnCpb4pF4cGH1jG8NUa1`).
- Premium: GBP 19.99 monthly (`price_1UGlC4Cpb4pF4cGHvlXXtra9`), GBP 199 annual
  (`price_1UGlC4Cpb4pF4cGHY6mNntds`). Existing prices were reused.
- New webhook `we_1UUYEsCpb4pF4cGHJMTv5HMk` at
  `https://zova-social.com/billing/webhook`, ten documented billing events,
  snapshot payload, API version `2026-07-29.dahlia`.
- Existing test portal `bpc_1UGlMsCpb4pF4cGHYn0UJjMu`: invoice history and payment
  method updates enabled; cancellation at period end, without a reason survey.
  Default return corrected from localhost to `https://zova-social.com/subscribe`.
  Public portal link remains inactive. Legal links are not set; Stripe hides
  those shared live-account settings in test mode. Retain as live launch work.
- Saved test credentials directly into Render's environment editor; no secret
  was added to source or evidence. `STRIPE_MODE=test`, live checkout false,
  subscription required false, plan limits false. Other settings preserved.

## Release

Candidate `4f2089abbb810257d97d80e3ba06051d1c9b8f86` passed application PR CI
40230234088, push CI 40230231326 and native CI 40230234076. Local exact-scope
gate passed again before deployment. All 79 known commercial findings retained.

Fresh Render managed database export completed 25 October 20:44 UTC, retained
in Render. Three-day managed recovery window observed; no restore performed.
Deployment `dep-dbf6ll0m7kps73fva070` succeeded at 20:48 UTC with 4f2089a.
Health returned 200 after the expected brief persistent-disk restart.
Hosted testing found low contrast on membership cards and a misleading future
end date after immediate cancellation. Both are corrected in d090e6e.
Final PR CI 40233227548 and push CI 40233225307 passed: 689 SQLite / 690
PostgreSQL tests, client/browser checks, synthetic recovery, image smoke/audit
and production scope guards. Render deployment dep-dbf6s4gm7kps73fvufh0
succeeded (started 21:01:06 UTC, duration 1m11s). Live membership verifies dark
readable cards and no false future end date. Health, landing, Guide and versioned
CSS returned HTTP 200. Native-only repeat CI 40233227576 is still running;
native source is unchanged from the earlier passing 4f2089a run.

Use the existing separate Zova Recovery Check account for hosted UI acceptance.
Do not modify Apple's reviewer account or customers' billing records.

## Tester route

Beta access stays free without checkout. For optional **web** payment testing,
use `/subscribe`, open Optional Stripe test checkout and use Stripe's dummy
card `4242 4242 4242 4242`, a future expiry and any three-digit CVC. Never use a
real card. The iPhone beta remains free with no external Stripe purchase flow.

Screenshots are under `evidence/20261025/stripe-*.png` and
`render-stripe-pre-release-backup.png`. The receipt `stripe-test-acceptance.json` records the final provider/runtime check.

## Hosted acceptance

Completed through the real Stripe TEST hosted checkout from `/subscribe`, using
only the separate Zova Recovery Check account (user 18, customer
`cus_VVZUGlte0XqMUt`). No customer or Apple reviewer billing record was modified.

| Plan | Test checkout result | Subscription |
| --- | --- | --- |
| Basic monthly | Seven-day trial, then GBP 9.99/month | sub_1UUYLlCpb4pF4cGHpQkCL37r |
| Basic annual | GBP 99/year, no repeat trial | sub_1UUYSZCpb4pF4cGHBtxFhC96 |
| Premium monthly | GBP 19.99/month, no repeat trial | sub_1UUYTHCpb4pF4cGHPgFqibWN |
| Premium annual | GBP 199/year, no repeat trial | sub_1UUYUdCpb4pF4cGHr9h1MtYT |

All returned to Zova with the verified plan/status and correct renewal interval.
Closing Basic annual checkout returned safely; selecting it again resumed the
same `cs_test_a1NrqMbjpzjquflPGRrBMFIYJBWTWAdy3d5QPe8AaSClvrEHzU1y5AiGtw`
session, rather than creating a duplicate checkout.

Manage billing opened the hosted portal. Period-end cancellation returned to
Zova with "Cancellation is scheduled" through the actual webhook. The four
synthetic subscriptions were subsequently canceled immediately to leave no
active test renewal. This cleanup was bounded to this test customer and
asserted test mode, matching email/customer, and livemode=false before mutation.

Stripe Event deliveries showed HTTP 200 for checkout completion, subscription
creation, invoice paid and subscription deletion. Manually resending the first
checkout event `evt_1UUYLmCpb4pF4cGHkC8saKfz` returned HTTP 200 again; exactly one
BillingEvent row remained. The older event did not replace the current plan.

Final read-only runtime check: test mode, live checkout false, subscription
required false, plan limits false, test billing status canceled, legacy/live
user status none. All four Stripe subscriptions had livemode=false and canceled
status. No real payment, social post, AWS resource or DNS change occurred.

Twenty focused Stripe tests passed after the fixes. Application/PostgreSQL CI
for the intermediate contrast commit c02f486 passed (40232800268/40232795759).
No new native binary has been distributed: TestFlight remains 0.1.0 (11). Native
welcome/launch changes still require a replacement signed build and device QA.

This is test-payment acceptance, not approval to enable commercial billing.
Portal legal links, tax/live account setup and the native purchase policy remain
separate live-launch work. The 79-item commercial gap register is preserved.
