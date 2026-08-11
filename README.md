# Zova Social Studio — V5.1

Zova V5.1 is an AI social manager for content creators. It turns one piece of intent into genuinely different native content for **X, Instagram, Facebook and TikTok**, applies the creator's voice and brings performance back into the creative workflow.

## What is implemented

- Zova landing page and branding layer
- Sign in / sign up with Apple
- Minimal email/password signup with password confirmation
- Production-oriented user profile data (name, normalized email, country, consent and account timestamps)
- Guided onboarding: Account -> Socials -> Writing style -> Studio
- Stripe subscription checkout + Stripe Customer Portal
- Apple Pay support through Stripe Checkout when Stripe/device/region eligibility allows it
- Account management and social unlinking
- Discreet, allowlisted `/admin/users` account dashboard
- X OAuth 2.0 connection
- Meta OAuth connection for Facebook Pages and linked professional Instagram accounts
- TikTok Login Kit OAuth connection
- One brief → platform-specific AI drafts for any combination of the four socials
- X single posts, 3-post threads and 5-post threads
- Creator preferences: tone, audience, topics, avoid list, examples, preferred length and timezone
- One-click rewrite actions
- Image uploads and optional links
- Preview, publish-now and scheduled publishing
- AI-proposed schedule times
- Draft history
- Recent activity
- Right-hand analytics panel by social
- Security/privacy page
- Backward-compatible `/x/preview` and `/x/post` Custom GPT actions

## Important: provider setup is still required

The code is ready for the integrations, but Meta, TikTok, Stripe and persistent media storage require credentials/configuration in their own developer consoles. See `PROVIDER_SETUP.md`.

## Upgrade from V4

1. Back up your current GitHub repo and Render environment values.
2. Replace the V4 application files with this package. Keep your existing Render Postgres database.
3. Commit to GitHub.
4. In Render, sync the Blueprint or add the new environment variables manually.
5. Keep the existing X OAuth values and `CREDENTIAL_ENCRYPTION_KEY` unchanged.
6. Deploy with **Manual Deploy → Clear build cache & deploy**.
7. Open `/health`; expected response:

```json
{"status":"ok","version":"5.1.0","brand":"Zova"}
```

8. Open `/signup` and create a test Zova user.
9. Configure providers one at a time using `PROVIDER_SETUP.md`.

## URLs

- `/` landing page
- `/signup` signup
- `/login` login
- `/subscribe` subscription page
- `/studio` Creator Studio
- `/account` preferences, social connections and billing management
- `/security` security/privacy page
- `/health` health/version check

OAuth callbacks:

- X: `/callback/x` (kept compatible with V3/V4)
- Meta: `/oauth/meta/callback`
- TikTok: `/oauth/tiktok/callback`

## Subscription enforcement

`REQUIRE_SUBSCRIPTION=false` is the migration-safe default. This lets you test V5 without locking your current workspace.

When Stripe Checkout and webhooks are confirmed working, set:

```text
REQUIRE_SUBSCRIPTION=true
```

Then AI generation, image upload, preview/publish and scheduling require an `active` or `trialing` Stripe subscription.

## Admin dashboard

Set `ADMIN_EMAILS` to a comma-separated list of existing Zova account emails, sign in with one of those accounts, then visit `/admin/users` directly. The route is intentionally omitted from navigation and API documentation. Unauthorized visitors receive a generic 404. The page is read-only and never exposes password hashes, provider tokens, or payment details.

## Scheduling

Zova runs an in-process scheduler every 60 seconds while the Render service is awake. There is also a protected endpoint:

```text
POST /internal/run-due
Authorization: Bearer $SCHEDULER_SECRET
```

**Render Free can sleep.** For reliable scheduled posting, use an always-on service or an external scheduler/cron to call the protected endpoint regularly. Do not promise minute-perfect scheduling on a sleeping free instance.

## Images

Immediate image publishing can use the local Render filesystem, but that filesystem is ephemeral. Scheduled Meta/TikTok publishing should use persistent public object storage.

Configure the optional S3-compatible settings in `.env.example`. For TikTok photo posting, the media URL also needs to meet TikTok's verified-domain requirements.

## Multi-social behaviour

The creator chooses any combination of X / Instagram / Facebook / TikTok. The AI receives the same brief plus creator preferences and returns separate platform-native versions.

- X: 280-character enforcement; 1/3/5-part thread support
- Facebook: longer contextual post; link support
- Instagram: caption adapted for a visual post; image required in this V5 build
- TikTok: visual-first caption; image required in this V5 build

## Backward compatibility

Existing Custom GPT X Actions remain available at:

- `/x/preview`
- `/x/post`

Keep the legacy X environment variables in Render if you still use those GPTs. The Zova web product itself uses the new `nova_*` user/social tables.

## Brand profile

The application contains **no hard-coded previous-product branding**. All core Zova colours/styles are centralized in `nova/static/nova.css`.

The exact Zova/Zova brand-profile attachment was not available in the working file set while this package was built, so the supplied interface uses a clean Zova placeholder theme rather than inventing brand rules. Once the actual brand profile is uploaded, update the CSS tokens and wordmark treatment without changing the backend.

## Security

See `SECURITY.md`, `USER_DATA.md` and the in-product `/security` page. Before a public launch, obtain appropriate legal/privacy review for your company, data retention policy and target regions.
