# Zova pricing and Stripe test catalogue — 17 September 2026

Source: project task "Create Zova pricing strategy" (019fed3f-5300-73a3-8e3b-c2e305a6d6cc), read in full on 17 September. User explicitly directed use of this discussion and confirmed GBP. The latest seven-day trial instruction supersedes its older fourteen-day proposal. Basic maps to its Normal tier. No permanent free tier. Business remains a working proposal outside this two-tier setup.

| Plan | Monthly | Annual total | Brands | Social accounts | Publications/month | AI actions/month |
| --- | --- | --- | --- | --- | --- | --- |
| Basic | GBP 9.99 | GBP 99 | 1 | 4 | 100 | 150 |
| Premium | GBP 19.99 | GBP 199 | 2 | 8 | 250 | 400 |

The strategy also proposes Business at GBP 49.99/month or GBP 499/year, 5 brands, 20 accounts, 750 publications, 1,000 AI actions and 3 users. It is not created or enabled here.

## Strategy versus implementation

These are target allowances, not verified implemented entitlements. Keep subscription enforcement disabled for reviewer testing. Scheduling, images, links and core analytics belong in Basic. Premium targets deeper analytics, reusable variations/templates and priority email support. Do not market unfinished features as delivered. The discussion's weighted token/model allowances were recommendations: Basic 1 million weighted tokens and Premium 3 million, with advanced/reasoning model credit multipliers; these require a defined accounting implementation before enforcement. No named-model promises or silent overage charges.

Internal guardrails: entry-tier X limits proposed at 30 publications/month including no more than 10 external-URL posts, cached analytics and cost alerts near GBP 3/month Basic and GBP 6/month Premium. Historical provider cost estimates from the conversation were not revalidated and must not be treated as current rates.

## Created and verified in Stripe test mode

Account: acct_1U3LuQCpb4pF4cGH. Basic product: prod_VHJospepHS9H12. Premium product: prod_VHJpG397B0S9Nt. Each product detail page verified the two correct amounts and intervals with zero active subscriptions.

| Environment variable | Test Price ID | Lookup key |
| --- | --- | --- |
| STRIPE_BASIC_MONTHLY_PRICE_ID | price_1UGlAnCpb4pF4cGHGEvcPxYi | zova_basic_monthly_gbp |
| STRIPE_BASIC_ANNUAL_PRICE_ID | price_1UGlAnCpb4pF4cGH1jG8NUa1 | zova_basic_annual_gbp |
| STRIPE_PREMIUM_MONTHLY_PRICE_ID | price_1UGlC4Cpb4pF4cGHvlXXtra9 | zova_premium_monthly_gbp |
| STRIPE_PREMIUM_ANNUAL_PRICE_ID | price_1UGlC4Cpb4pF4cGHY6mNntds | zova_premium_annual_gbp |

All four prices use GBP, flat-rate recurring billing and tax-inclusive behaviour, following the strategy's customer-paid headline amount/VAT provision. This does not activate tax collection or establish VAT registration. Verify tax setup separately before live activation. No product feature/entitlement claims were entered. Seven-day trials are requested by Zova's Checkout integration, not a product-level trial configuration; the dashboard product trial section may therefore say No trials.

## Outstanding setup and acceptance

Test catalogue creation is complete. These IDs are recorded here but not deployed into any running application environment. Test secret key, endpoint-specific webhook secret, reachable staging/forwarded webhook endpoint and portal configuration remain to be connected. Complete all provider acceptance checks in STRIPE_BILLING.md, including trial-end conversion/cancellation and own-account return reconciliation. Existing code tests: 95 local passed; CI at candidate 492a02f passed. Creating products is not proof of checkout/webhook operation. No live products, charges, production changes or deployment in this step.

Pricing changes: create a new recurring Price and deliberately update the corresponding environment mapping; preserve old prices/subscriptions for existing customers unless a migration is explicitly approved. Stable lookup keys help identify the tier, but current Zova code selects configured Price IDs. Never replace a prior subscriber's terms silently.
