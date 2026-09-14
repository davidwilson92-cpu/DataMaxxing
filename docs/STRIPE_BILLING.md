# Stripe billing integration

## Implementation and feature matrix

| Capability | Implementation | Validation |
| --- | --- | --- |
| Monthly/annual subscription checkout | Hosted Stripe Checkout, server-controlled price IDs | Mocked route and HTTP transport tests |
| Repeat/interrupted checkout | Persisted attempt key and exact request, open-session reuse, account locking | Concurrent retry and lost-response tests |
| Existing subscription protection | Retrieve current subscriptions before starting checkout | Active/past-due blocking tests |
| Billing portal | Authenticated POST bound to own customer; configure invoices, payment methods and cancellation in Stripe | Mocked ownership test |
| Webhooks | Raw-body signature + 5-minute tolerance, mode check, durable event deduplication | Invalid/expired signature, duplicate and mode tests |
| Renewal/failure/cancellation | Retrieve current Stripe subscriptions under account lock, not historical event status | Out-of-order and past-due/cancelled tests |
| Return page | Ownership/mode/customer verification; completed Checkout and actual subscription reconciliation | Foreign/pending/paid-but-past-due tests |
| Test/live separation | Separate billing account rows; only verified live state updates legacy User entitlements | Mode isolation and legacy live sync tests |
| Access during testing | REQUIRE_SUBSCRIPTION remains false; checkout has independent mode/live switch | Default-off tests |
| Billing UI | Account link, test badge, cancellation/pending/error states, refresh and portal controls | Synthetic desktop/mobile inspection |

No production Stripe configuration or real charges were performed. Full local suite: 88 passed; final billing-specific suite: 12 passed, including expired checkout and resubscription after cancellation. GitHub CI must also pass PostgreSQL, restore and Docker checks. Provider sandbox and deployment validation remain separate gates.

## Configure a Stripe sandbox first

Keep secrets in the deployment environment or an untracked local environment file, never in source or chat. No publishable key is needed for hosted Checkout.

- `STRIPE_MODE=test`
- `STRIPE_SECRET_KEY`: a sandbox/test secret key (sk_test_ or an appropriately scoped rk_test_).
- `STRIPE_MONTHLY_PRICE_ID`: the approved recurring monthly Price ID. `STRIPE_PRICE_ID` remains a compatible fallback.
- `STRIPE_ANNUAL_PRICE_ID`: optional approved annual recurring Price ID.
- `STRIPE_WEBHOOK_SECRET`: the secret for this specific endpoint/environment.
- `STRIPE_PORTAL_CONFIGURATION_ID`: optional portal configuration with approved cancellation, invoices and payment-method features. Configure default portal settings if omitted.
- `STRIPE_API_VERSION`: pin the API version selected and verified in the Stripe sandbox; use the same version for the webhook endpoint.
- `PUBLIC_BASE_URL`: the exact HTTPS staging origin. Local Stripe CLI forwarding can target localhost.
- `STRIPE_LIVE_CHECKOUT_ENABLED=false` and `REQUIRE_SUBSCRIPTION=false`.

Confirm pricing, currency, tax treatment, interval and any trial before creating/configuring Price IDs. No trial, promotional discounts or tax registration is invented by the code. Stripe Checkout displays the exact price and total before the customer subscribes. If taxes are needed, complete the appropriate Stripe configuration and validate tax-inclusive/exclusive behavior before live activation.

Register POST `/billing/webhook` for: checkout.session.completed, checkout.session.async_payment_succeeded, checkout.session.async_payment_failed, customer.subscription.created, customer.subscription.updated, customer.subscription.deleted, customer.subscription.paused, customer.subscription.resumed, invoice.paid and invoice.payment_failed. Use the endpoint-specific signing secret. The handler also handles other customer.subscription.* notifications by reconciling current state.

## Provider acceptance checks (not yet performed)

Use only Stripe sandbox payment methods documented by Stripe. Complete a monthly checkout; repeat the request; close/resume checkout; test a declined/authentication-required payment; deliver duplicate and delayed events; renew a test subscription; fail an invoice; recover payment through the portal; cancel now and at period end; reopen the portal; test annual pricing if enabled. Verify Zova's last-verified status and exact Stripe customer/subscription match. Confirm existing Studio, users, uploads, reviewer login and both Instagram connection routes remain unaffected. Do not claim these provider checks from mocks.

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
