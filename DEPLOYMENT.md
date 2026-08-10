# Zova V5.1 deployment notes

## Deploy

1. Back up the current database and retain all existing X, Meta, TikTok, Stripe, OpenAI, storage and encryption values.
2. Deploy this package from the repository root. The Docker start target remains `app:app`, preserving the V5 architecture.
3. Set `REQUIRE_SUBSCRIPTION=false` for the initial deployment. This is also the Blueprint default.
4. Add the Apple variables below, deploy, then verify `/health` returns `{"status":"ok","version":"5.1.0","brand":"Zova"}`.
5. Test email signup, password mismatch rejection, Socials → Writing style → Studio, Apple signup/login, X connection and one harmless X draft/preview before enabling other providers.

## Sign in with Apple

In Apple Developer, create or reuse an App ID, create a Services ID for web authentication, and associate it with the App ID. Configure the production hostname as the primary domain and this return URL:

```text
https://YOUR-DOMAIN/auth/apple/callback
```

Create a Sign in with Apple key and add:

```text
APPLE_CLIENT_ID=your Apple Services ID
APPLE_TEAM_ID=your 10-character Apple Team ID
APPLE_KEY_ID=the key ID for the Sign in with Apple .p8 key
APPLE_PRIVATE_KEY=the complete .p8 private key
APPLE_REDIRECT_URI=https://YOUR-DOMAIN/auth/apple/callback
```

If the host stores multiline secrets on one line, replace private-key line breaks with literal `\n`; Zova accepts either format. `PUBLIC_BASE_URL` must use the same HTTPS production origin. The Apple button stays hidden until all credential values are present.

Apple may provide a relay address when a user hides their email. Configure Apple's private email relay for any future transactional sender addresses before emailing those users.

## Compatibility and defaults

Keep the existing V5 variables in `.env.example`. Pricing display variables are now `ZOVA_PRICE_LABEL` and `ZOVA_PRICE_NOTE`; the application still reads old `NOVA_*` names as a fallback. Existing database table names, Python package imports and storage prefixes intentionally remain unchanged for an in-place upgrade.

Onboarding runs `/signup` → `/onboarding/socials` → `/onboarding/writing-style` → `/studio`. Socials and writing style can both be skipped. Subscription enforcement remains off unless `REQUIRE_SUBSCRIPTION=true` is explicitly set.
