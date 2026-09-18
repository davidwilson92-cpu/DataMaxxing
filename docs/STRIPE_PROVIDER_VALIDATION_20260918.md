# Stripe test acceptance — 17–18 September 2026

## Scope and implementation

Validated the real Zova billing candidate against Stripe TEST account `acct_1U3LuQCpb4pF4cGH`, API `2026-07-29.dahlia`, using six synthetic local users, isolated SQLite/uploads, localhost port 8773 and Stripe CLI webhook forwarding. No production database, social connections, production deployment or live payments were used. Existing test credentials stayed Windows-DPAPI encrypted outside the repository. Subscription enforcement and live checkout stayed disabled.

Real provider testing exposed two account defaults: Managed Payments rejected checkout without a product tax code, and Adaptive Pricing presented a converted EUR price. Checkout now explicitly disables both per session, retaining standard Stripe subscriptions and the configured GBP price. Regression assertions cover both settings across all four plan choices. Account-wide defaults were not modified.

## Provider evidence and feature matrix

| Capability | Real test result | Boundary |
| --- | --- | --- |
| Basic monthly | Hosted checkout completed; GBP 999 pence/month; trial 604800 seconds; Zova Trialing | Synthetic card only |
| Basic annual | Hosted checkout completed; GBP 9900 pence/year; trial 604800 seconds; Zova Trialing | Synthetic card only |
| Premium monthly | Hosted checkout completed; GBP 1999 pence/month; trial 604800 seconds; Zova Trialing | Synthetic card only |
| Premium annual | Hosted checkout completed; GBP 19900 pence/year; trial 604800 seconds; Zova Trialing | Synthetic card only |
| Retry prevention | All four repeated creation requests returned the same open session; exactly one completed session per customer | Concurrent/lost-response paths additionally covered by mocks |
| Return ownership | Another local user received 403 for the Basic checkout return | No email-based reassignment |
| Existing subscription | Trialing subscriber could not create a second subscription | Also mocked active/past-due coverage |
| Portal | Actual Zova portal session displayed subscription, invoice and test card; period-end cancellation submitted and reflected in Zova | Payment-method replacement via portal UI not exercised |
| Trial conversion | Stripe test clock advanced beyond seven days; GBP 999 paid; webhook made local account Active | Basic monthly clock; annual renewal not clock-tested |
| Trial cancellation | Separate clock subscription canceled at trial end; paid amount zero; local Canceled | Actual portal cancellation also verified separately |
| Failed renewal and recovery | Declining test payment method produced Past due; replacement test method and invoice payment produced Active via webhook | Recovery through Stripe API, not portal UI |
| Returning subscriber | Canceled local subscriber received no trial; real checkout amount due GBP 999; unused session expired | Trial history depends on retained billing records |
| Webhook integrity | Actual subscription/invoice/checkout notifications delivered; duplicate historical event replay did not regress active state; invalid signature rejected | Public staging endpoint/retry outage not exercised |
| Test/live isolation | Existing User live billing columns stayed null for all synthetic users | No production records touched |
| Plan allowances | Pricing strategy recorded separately | Brand/account/publication/AI allowances not implemented or enforced |

Test portal configuration: `bpc_1UGlMsCpb4pF4cGHYn0UJjMu`. Invoice history, payment-method updates and cancellation at period end enabled; plan/quantity changes disabled; optional cancellation-reason collection disabled. Return URL is localhost, not a deployed staging service. No public portal login link activated. Legal links and tax setup still need live-readiness review.

After verification, synthetic subscriptions were set to cancel at period end and the unused returning-subscriber checkout expired. Audit records were retained. Basic annual's first browser return was interrupted by the browser runtime; a fresh local tab confirmed its saved Trialing state. Both Premium returns completed normally.

## Automated tests

Billing regression: 18 passed. Fresh full local suite: **95 passed**, 17 dependency/test deprecation warnings, 18 September 2026. These are distinct from the actual Stripe acceptance checks above. Exact candidate CI status is recorded in the handoff; do not infer it from local results.

Local evidence outside Git: `work/zova-stripe-validation/{checkout-evidence,clock-evidence,failure-evidence,final-evidence}.json`, redacted webhook delivery log, isolated database, and validation scripts. Checkout URLs, credentials and signing secret are excluded from this report and repository.

## Remaining release gates

- Hosted public staging configuration and endpoint-specific webhook secret; delivery/retry monitoring and outage recovery validation.
- Authentication-required/3DS checkout, alternate wallets, portal payment-method replacement and annual renewal timing. Do not claim these from card-success or API-recovery tests.
- Implement and validate target plan allowances before selling them as delivered; keep reviewer access open.
- Confirm live tax/legal/customer-support settings and pricing presentation. Live product/key/portal/webhook setup and charging activation require a separate decision.
- Production compatibility checks, backup and deployment remain separate. This test pass is not production deployment approval.

## Restart and rollback

The isolated `listen_test.py` and `run_app.py` runners use the existing encrypted test key and an allowlisted environment. Start the listener first, wait for its ready message and saved signing secret, then start the application using `work/zova-audit-py312/Scripts/python.exe`. Both bind/forward only to localhost. Stop both when finished. Application restart replaces its temporary signing/session keys; synthetic users must log in again. Do not copy this disposable key behavior to production.

To undo this validation, stop the two local processes; retain synthetic evidence and test subscription records. Production has nothing to roll back. For a later billing deployment, disable new live checkouts while preserving webhook processing, billing account/event tables, retry keys and prior subscription history. Preserve existing users/uploads/social tokens. Use the additive migration and backup guidance in STRIPE_BILLING.md; never reactivate the obsolete unsafe paid endpoints.
