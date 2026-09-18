# Brands, allowances and billing journey — 18 September 2026

## Implementation

The user approved finishing payment validation, implementing plan allowances and polishing the customer journey, and explicitly chose separate brand workspaces for Premium. This candidate extends the existing application; it is not deployed.

| Capability | Basic | Premium | Candidate behavior |
| --- | --- | --- | --- |
| GBP pricing | £9.99/month or £99/year | £19.99/month or £199/year | Visible before Checkout; mismatched Stripe currency/amount fails closed |
| New subscriber trial | 7 days | 7 days | Card collected; actual Stripe status and trial/renewal/end date shown |
| Brand workspaces | 1 | 2 | Separate voice, conversations, drafts, media, connections, schedules and activity |
| Connected accounts | 4 | 8 | Account-wide active connection cap; reconnecting an existing active account needs no new slot |
| Publications/month | 100 | 250 | Reserved at confirmation; one unit per destination post, each X thread post counts |
| AI actions/month | 150 | 400 | Successful generation, rewrite, voice analysis, schedule suggestion or AI analytics answer |
| Billing management | Included | Included | Hosted portal, cancellation status, verified dates, failed-payment guidance |
| Core tools | Included | Included | Existing drafting, voice, scheduling and available analytics retained |

Plan limits remain **disabled** by default (`PLAN_LIMITS_ENABLED=false`), independently of `REQUIRE_SUBSCRIPTION=false`. Testing access remains open. Setting a flag is not authorization to enable it in production. Test subscriptions cannot affect live limits; isolated test enforcement additionally requires `STRIPE_MODE=test` and `PLAN_LIMITS_MODE=test`.

Counts are shared across brands, reset by UTC calendar month and also apply monthly to annual subscribers. Scheduled publications reserve in the confirmation month, not the eventual delivery month. Cancellation before dispatch releases the reservation. A provider result that is pending or unknown retains its reservation to prevent an unsafe resend. Known pre-provider failure or a confirmed TikTok failure releases it. Reusing a publication does not reserve twice. Historical work is retained and not back-billed. No automatic overage charges.

Conversation routing and deterministic analytics are included rather than separately metered. A rewrite of multiple platform variants currently performs one action per rewritten variant. Legacy Custom GPT publishing endpoints retain existing behavior and are outside these Studio allowances; do not sell legacy access as a metered Studio feature. Weighted model tokens, proposed X sublimits, deeper Premium-only analytics/templates and a priority-support service remain outside this implementation and are not advertised as delivered.

## Workspace compatibility and isolation

All existing rows retain `brand_id=0`; no records or encrypted connections are moved. Existing CreatorPreferences remain the default workspace voice. Additional workspaces use a separate voice table. Brand names can be edited without changing the user's profile or credentials. New workspaces start empty and never duplicate credentials. There is no destructive workspace-delete or automatic reassignment flow.

Request sessions enforce user and brand scope on ORM reads, updates, deletes and inserts. Browser fetch requests, forms, dynamic links and Studio history URLs pin the rendered workspace, so switching another tab does not redirect a late save to a different brand. OAuth state records the workspace at connection start; the verified callback restores that scope even when another tab switches. Both Instagram routes retain their existing providers and grants. Scheduler sessions process all workspaces using exact reviewed destinations; created activity retains the publication's brand.

The additive migration creates brands, brand voices and usage entries, adds zero-default brand columns to scoped records and OAuth state, and adds the default brand display name to User. No password, session version, upload, token encryption, publishing approval or existing billing records are replaced.

## Tests and provider evidence

Automated coverage includes cross-user/cross-brand drafts, media references, connections, schedules and approvals; separate voice persistence; late-tab workspace headers; OAuth return to the initiating brand; concurrent allowance reservations; failure refunds; monthly reset; schedule cancellation refunds; quota rejection rolling back the reviewed submission; renamed workspace preservation; retired Stripe price aliases; and checkout price mismatch rejection. Existing publishing/auth/security/Studio tests continue to run. Exact final suite and CI results are recorded in the handoff.

Real Stripe TEST evidence, separate from mocks:

- All four hosted checkouts and seven-day trials were completed in the preceding validation.
- Basic annual and Premium annual test clocks each converted from trial and completed an annual renewal at GBP 9900/19900 pence. These annual clock scenarios verify Stripe billing; they use separate provider-only synthetic customers. The application's event synchronization was exercised with the mapped monthly scenarios and all four hosted checkout returns.
- The actual hosted returning-subscriber checkout showed £9.99 due, required 3DS, handled a deliberately failed challenge without completing payment or activating the local subscription, and succeeded when the same session was retried and authenticated. Zova then showed Active.
- The customer portal accepted a new test Mastercard. Its subscription-specific payment selector was also updated, and the Stripe subscription's default payment method was verified. Merely changing the customer default did not replace the subscription's explicit card; the billing guidance therefore points users to their subscription settings.
- The webhook forwarder was stopped, a real test subscription cancellation was scheduled, and the local state remained unchanged until the authenticated Refresh billing status action reconciled the missed update. This verifies manual outage recovery, not a public webhook endpoint's retry schedule.

Evidence outside Git: `work/zova-stripe-validation/annual-evidence.json` and `extended-provider-evidence.json`, alongside the preceding checkout/clock/failure evidence. Synthetic renewals were scheduled to cancel. No real cards, live charges, real posts, grant changes or production database were used.

Desktop and 390px mobile layouts were inspected in-browser. The second brand was created through the interface; composer text and its history entry survived a reload in the same brand. Native selects/details and explicit labels retain keyboard operation. The membership page uses the existing Zova logo, purple accent and typography, readable prices and restrained cards.

## Pricing changes and operations

`nova/allowances.py:PLANS` is the central price/allowance catalogue. Create a new Stripe recurring Price, update the relevant environment mapping and catalogue together, and validate in test mode. Checkout rejects an amount/currency mismatch. Preserve prior price IDs with the corresponding `STRIPE_<TIER>_<INTERVAL>_LEGACY_PRICE_IDS` comma-separated setting; this retains existing subscribers' labels and allowances without silently changing their Stripe price. No plan migrations or portal upgrades are enabled automatically.

Reservations surviving a process crash remain counted until support verifies the operation outcome. Do not release ambiguous publication reservations automatically. Review stuck AI reservations against saved results/provider logs before releasing them; this candidate does not invent success or blindly grant usage back. Before enforcement, monitor those operational cases and agree the rollout policy for existing users and legacy subscribers.

## Remaining launch gates

Public staging hosting/webhook delivery monitoring and retry behavior still need the deployment environment. Alternative wallets were not exercised. Live tax, legal, support settings and customer-facing rollout remain a separate activation decision. No production release, paid enforcement, new credentials or live Stripe setup has been authorized or performed here.

## Rollback

Before a later deployment, take and verify a database backup, preserve existing encryption/session configuration and validate the additive schema. To stop paid operations, keep live checkout, subscription enforcement and plan limits disabled while retaining billing reconciliation. Do not drop usage, billing or brand records. Do not revert to a pre-brand binary after additional workspaces contain data: that code does not understand brand boundaries. Prefer a forward fix or revert only the membership UI while keeping scope enforcement; a full restore requires a coordinated backup/restore plan that preserves new customer work. The synthetic PostgreSQL restore check includes brand columns, voices and usage records.

Primary Stripe references: https://docs.stripe.com/testing and https://docs.stripe.com/api/test_clocks/advance.
