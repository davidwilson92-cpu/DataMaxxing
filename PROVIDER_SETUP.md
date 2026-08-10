# Zova V5 — Provider setup

Add secrets only to **Render → Environment**. Do not commit credentials to GitHub.

## 1. X

V5 preserves the callback used by the existing V3/V4 integration:

```text
https://YOUR-DOMAIN/callback/x
```

Required Render variables:

```text
X_OAUTH2_CLIENT_ID
X_OAUTH2_CLIENT_SECRET
X_OAUTH2_REDIRECT_URI
```

Requested scopes are `tweet.read tweet.write users.read offline.access`.

## 2. Meta: Facebook + Instagram

Create/configure a Meta developer app for Facebook Login and the Instagram API.

Callback:

```text
https://YOUR-DOMAIN/oauth/meta/callback
```

Render:

```text
META_APP_ID
META_APP_SECRET
META_GRAPH_VERSION=v23.0
META_REDIRECT_URI=https://YOUR-DOMAIN/oauth/meta/callback
```

Zova requests:

```text
pages_show_list
pages_read_engagement
pages_manage_posts
instagram_basic
instagram_content_publish
instagram_manage_insights
```

The callback reads Pages the user manages. Each Page becomes a Facebook connection. If the Page has a linked Instagram professional account, Zova creates an Instagram connection too.

For external customers rather than app-role test users, expect Meta App Review / Advanced Access requirements for permissions.

Instagram publishing in this build is for **professional Business/Creator accounts** and publishes an uploaded image plus caption. Consumer/personal Instagram accounts are not supported by this Meta flow.

## 3. TikTok

Create a TikTok developer app and add:

- Login Kit
- Content Posting API
- Direct Post capability

Callback:

```text
https://YOUR-DOMAIN/oauth/tiktok/callback
```

Render:

```text
TIKTOK_CLIENT_KEY
TIKTOK_CLIENT_SECRET
TIKTOK_REDIRECT_URI=https://YOUR-DOMAIN/oauth/tiktok/callback
TIKTOK_DEFAULT_PRIVACY=PUBLIC_TO_EVERYONE
```

Zova requests:

```text
user.info.basic
video.list
video.publish
```

V5 implements TikTok photo Direct Post. TikTok requires the app to query creator information before posting and Zova does this. If `PUBLIC_TO_EVERYONE` is not available, Zova falls back to an allowed privacy level, preferring `SELF_ONLY`.

Important launch requirement: unaudited TikTok Direct Post clients are restricted to private posts. Complete TikTok's Content Posting API audit before promising public direct posting to customers.

TikTok photo URLs must be from a verified domain/URL prefix. Configure persistent public media storage and verify that domain in TikTok.

## 4. Stripe subscriptions + Apple Pay

Create one recurring Stripe Price and add:

```text
STRIPE_SECRET_KEY
STRIPE_PRICE_ID
STRIPE_WEBHOOK_SECRET
```

Configure a webhook endpoint:

```text
https://YOUR-DOMAIN/billing/webhook
```

At minimum subscribe it to:

- `checkout.session.completed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`

Zova uses Stripe Checkout for subscription creation and Stripe Customer Portal for management/cancellation.

Apple Pay is not a separate Zova credential. When Apple Pay is enabled in Stripe and supported for the customer/device/region, it is offered by Stripe Checkout. Eligibility rules for digital subscriptions vary by region/platform, so validate your launch market before advertising it universally.

After successful testing set:

```text
REQUIRE_SUBSCRIPTION=true
```

## 5. OpenAI

Keep your working values:

```text
OPENAI_API_KEY
OPENAI_MODEL=gpt-5-mini
```

The key is server-side only. A restricted key should allow the Responses API calls required by the app.

## 6. Persistent media storage

Recommended for scheduled posts and TikTok/Meta media URLs:

```text
S3_BUCKET
AWS_REGION
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
S3_PUBLIC_BASE_URL
```

`S3_ENDPOINT_URL` is optional for an S3-compatible provider.

If `S3_PUBLIC_BASE_URL` is omitted, Zova can generate temporary S3 signed URLs. For TikTok, a stable URL on a verified domain is preferable.

## 7. Scheduler

Render environment:

```text
SCHEDULER_SECRET
SCHEDULER_INTERVAL_SECONDS=60
```

If the web service can sleep, configure an external scheduler to POST to `/internal/run-due` with the Scheduler secret as a Bearer token. An always-on instance is the cleaner production setup.
