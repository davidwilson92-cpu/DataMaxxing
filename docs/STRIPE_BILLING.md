# Stripe billing integration

Latest candidate update: [brand workspaces, plan allowances and extended payment validation](BRANDS_AND_BILLING_20260918.md). This supersedes earlier provider-test gaps for 3DS, annual clock renewals, portal card replacement and manual recovery after missed webhook delivery. Public staging and live activation remain separate gates.

## Implementation and feature matrix

| Capability | Implementation | Validation |
| --- | --- | --- |
| Basic/Premium monthly/annual checkout | Four server-controlled recurring price IDs; legacy Creator IDs remain compatible | All four choices and interval checks tested with mocked Stripe |
| 7-day free trial | Card collected at Checkout; new subscribers receive seven days; a recorded prior subscription prevents another trial | Four new-subscriber cases and cancelled-subscriber case with mocked Stripe |
| Repeat/interrupted checkout | Persisted attempt key and exact request, open-session reuse, account locking | Concurrent retry and lost-response tests |
| Existing subscription protection | Retrieve current subscriptions before starting checkout | Active/past-due blocking tests |
| Billing portal | Authenticated POST bound to own customer; configure invoices, payment methods and cancellation in Stripe | Mocked ownership test |
| Webhooks | Raw-body signature + 5-minute tolerance, mode check, durable event deduplication | Invalid/expired signature, duplicate and mode tests |
| Renewal/failure/cancellation | Retrieve current Stripe subscriptions under account lock, not historical event status | Out-of-order and past-due/cancelled tests |
| Return page | Ownership/mode/customer verification; completed Checkout and actual subscription reconciliation | Foreign/pending/paid-but-past-due tests |
| Test/live separation | Separate billing account rows; only verified live state updates legacy User entitlements | Mode isolation and legacy live sync tests |
| Access during testing | REQUIRE_SUBSCRIPTION remains false; checkout has independent mode/live switch | Default-off tests |
| Billing UI | Account link, test badge, cancellation/pending/error states, refresh and portal controls | Synthetic desktop/mobile inspection |

No production Stripe configuration or real charges were performed. Billing-specific suite: 18 passed, including all four tier/interval choices, trial parameters, cancelled-subscriber trial exclusion, expired checkout, resubscription and mismatched intervals. Full-suite and CI evidence is recorded in the handoff. Provider sandbox and deployment validation remain separate gates.

## Configure a Stripe sandbox first

Keep secrets in the deployment environment or an untracked local environment file, never in source or chat. No publishable key is needed for hosted Checkout.

- `STRIPE_MODE=test`
- `STRIPE_SECRET_KEY`: a sandbox/test secret key (sk_test_ or an appropriately scoped rk_test_).
- `STRIPE_BASIC_MONTHLY_PRICE_ID` and `STRIPE_BASIC_ANNUAL_PRICE_ID`: approved Basic recurring Price IDs.
- `STRIPE_PREMIUM_MONTHLY_PRICE_ID` and `STRIPE_PREMIUM_ANNUAL_PRICE_ID`: approved Premium recurring Price IDs.
- Legacy `STRIPE_MONTHLY_PRICE_ID` (or `STRIPE_PRICE_ID`) and `STRIPE_ANNUAL_PRICE_ID` remain the fallback only when no Basic/Premium IDs are configured.
- `STRIPE_WEBHOOK_SECRET`: the secret for this specific endpoint/environment.
- `STRIPE_PORTAL_CONFIGURATION_ID`: optional portal configuration with approved cancellation, invoices and payment-method features. Configure default portal settings if omitted.
- `STRIPE_API_VERSION`: pin the API version selected and verified in the Stripe sandbox; use the same version for the webhook endpoint.
- `PUBLIC_BASE_URL`: the exact HTTPS staging origin. Local Stripe CLI forwarding can target localhost.
- `STRIPE_LIVE_CHECKOUT_ENABLED=false` and `REQUIRE_SUBSCRIPTION=false`.

The user has approved a 7-day trial. GBP pricing is now recovered from the user-selected strategy: Basic 9.99/month or 99/year; Premium 19.99/month or 199/year. See ZOVA_PRICING_CONFIGURATION.md for source, target allowances and verified test Price IDs. Confirm pricing and tax treatment before creating Price IDs. Checkout collects a payment method and explicitly requests a seven-day trial for a customer with no current or recorded prior Zova subscription. A returning cancelled subscriber does not receive another trial. Trial-end missing-payment-method behaviour is cancellation. No promotional discounts or tax registration is invented. Basic/Premium names currently select billing prices; feature entitlements and limits are not differentiated without an approved feature matrix. Stripe Checkout displays the exact price and total before the customer subscribes. If taxes are needed, complete the appropriate Stripe configuration and validate tax-inclusive/exclusive behavior before live activation.

Register POST `/billing/webhook` for: checkout.session.completed, checkout.session.async_payment_succeeded, checkout.session.async_payment_failed, customer.subscription.created, customer.subscription.updated, customer.subscription.deleted, customer.subscription.paused, customer.subscription.resumed, invoice.paid and invoice.payment_failed. Use the endpoint-specific signing secret. The handler also handles other customer.subscription.* notifications by reconciling current state.

## Provider acceptance checks

Actual local Stripe test acceptance was performed on 17–18 September 2026. See [the evidence matrix](STRIPE_PROVIDER_VALIDATION_20260918.md) for completed checks, observed account-default fixes and remaining release gates. All four hosted card checkouts, seven-day trial length, portal cancellation, clock-driven conversion/cancellation, failed renewal/recovery, repeat-trial exclusion and duplicate/invalid webhooks were verified. This supersedes the earlier mocked-only status; public staging and production remain unvalidated.

Use only Stripe sandbox payment methods documented by Stripe. Complete each Basic/Premium monthly/annual checkout; verify the exact amount, currency, seven-day trial end and subsequent renewal; use Stripe test clocks to validate trial conversion and cancellation before the trial ends; verify a returning subscriber receives no repeat trial; repeat the request; close/resume checkout; test a declined/authentication-required payment; deliver duplicate and delayed events; renew a test subscription; fail an invoice; recover payment through the portal; cancel now and at period end; reopen the portal; test annual pricing if enabled. Verify Zova's last-verified status and exact Stripe customer/subscription match. Confirm existing Studio, users, uploads, reviewer login and both Instagram connection routes remain unaffected. Do not claim these provider checks from mocks.

## Operational recovery

Stripe should retry non-2xx webhooks. A failed reconciliation returns 503 and does not mark the event processed. Alert on webhook 4xx/5xx delivery failures in Stripe and service monitoring; inspect the billing row's synced_at. Use the authenticated Refresh billing status action to reconcile after an outage. Unknown/unmapped customers are acknowledged without linking by email or untrusted metadata; investigate and verify ownership before repairing an unmapped legacy customer. Legacy live customer IDs already stored on User are imported lazily into the live billing record.

Unknown checkout outcomes retain the same key and parameters for retries. Open sessions are reused; an expired session permits a new attempt. After 23 hours an unconfirmed attempt is deliberately blocked: inspect Stripe's request/session records before clearing it. Never blindly reset the key or create a second subscription. Existing unrelated/extra Stripe subscriptions require support review; the application only considers its configured prices and previously linked subscription. Accounts with more than 100 subscriptions fail closed for support review.

## Activation and rollback

Production activation is a separate decision: configure verified live keys, prices, portal and webhook; set STRIPE_MODE=live; enable STRIPE_LIVE_CHECKOUT_ENABLED only after provider validation and explicit live charging authorization. Keep REQUIRE_SUBSCRIPTION=false for reviewer testing until separately approved. Test records never grant or revoke live access.

Before deploying, back up the database and verify additive creation of zova_billing_accounts and zova_billing_events. No existing columns or data are removed. Retain both new tables on rollback; dropping them would lose checkout retry keys and event deduplication. Keep live webhook processing running if there are active subscriptions. To stop new checkouts, set STRIPE_LIVE_CHECKOUT_ENABLED=false without turning off webhook sync. Reverting to the old billing module reintroduces unsafe redirect/webhook behavior; prefer a forward fix, and do not re-enable its paid endpoints.

## Primary references

- https://docs.stripe.com/api/checkout/sessions/create
- https://docs.stripe.com/api/idempotent_requests
- https://docs.stripe.com/webhooks
- https://docs.stripe.com/customer-management/integrate-customer-portal
