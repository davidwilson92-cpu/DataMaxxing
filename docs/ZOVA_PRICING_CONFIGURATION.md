# Zova pricing and Stripe test catalogue — 17 September 2026

Source: project task "Create Zova pricing strategy" (019fed3f-5300-73a3-8e3b-c2e305a6d6cc), read in full on 17 September. User explicitly directed use of this discussion and confirmed GBP. The latest seven-day trial instruction supersedes its older fourteen-day proposal. Basic maps to its Normal tier. No permanent free tier. Business remains a working proposal outside this two-tier setup.

| Plan | Monthly | Annual total | Brands | Social accounts | Publications/month | AI actions/month |
| --- | --- | --- | --- | --- | --- | --- |
| Basic | GBP 9.99 | GBP 99 | 1 | 4 | 100 | 150 |
| Premium | GBP 19.99 | GBP 199 | 2 | 8 | 250 | 400 |

The strategy also proposes Business at GBP 49.99/month or GBP 499/year, 5 brands, 20 accounts, 750 publications, 1,000 AI actions and 3 users. It is not created or enabled here.

## Strategy versus implementation

Update 18 September: the candidate now implements the numeric brand/account/publication/AI allowances above with opt-in enforcement, separate brand workspaces and a visible pricing/usage journey. Read BRANDS_AND_BILLING_20260918.md for counting rules, tests, provider evidence and exclusions. The earlier target-only paragraph below is retained as strategy history; it no longer describes the numeric allowance implementation. Nothing is deployed or enforced in production.

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

Test catalogue and isolated localhost integration are complete. All four prices were used in completed hosted test checkouts with seven-day trials and saved Zova status. Existing test credentials, CLI-forwarded signed webhooks and portal configuration were connected locally. Trial conversion/cancellation, failed renewal/recovery and repeat-trial exclusion were verified against Stripe. See STRIPE_PROVIDER_VALIDATION_20260918.md for the evidence matrix and remaining release gates. Fresh local suite: 95 passed. No live products, real charges, production changes or deployment. These prices are not installed in production.

Pricing changes: create a new recurring Price and deliberately update the corresponding environment mapping; preserve old prices/subscriptions for existing customers unless a migration is explicitly approved. Stable lookup keys help identify the tier, but current Zova code selects configured Price IDs. Never replace a prior subscriber's terms silently.
