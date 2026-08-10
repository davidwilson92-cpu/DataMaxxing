# Nova — security notes for V5

## Implemented controls

- Social tokens are encrypted at rest with Fernet using `CREDENTIAL_ENCRYPTION_KEY`.
- User passwords use salted `scrypt` hashes; plaintext passwords are not stored.
- Browser sessions are signed, HttpOnly and SameSite=Lax; Secure is enabled when `PUBLIC_BASE_URL` is HTTPS.
- OpenAI, X, Meta, TikTok and Stripe secrets stay server-side in environment variables.
- Social account selection is derived from the signed-in user's database connections.
- Each user can unlink a social connection from Account settings.
- Existing Custom GPT bearer keys remain hashed in the legacy creator table.
- Stripe card/payment details are handled by Stripe Checkout; Nova stores Stripe customer/subscription references and status.
- Publication attempts and status are logged to support history and troubleshooting.

## Production hardening still recommended

Before public launch:

1. Put the product on a dedicated Nova domain.
2. Use persistent managed object storage for uploads and apply lifecycle/retention rules.
3. Configure strict CORS / trusted hosts and a Content Security Policy.
4. Add email verification, password reset and account deletion workflows.
5. Add rate limiting and bot/abuse controls to signup/login/AI endpoints.
6. Add provider webhook verification and TikTok post-status webhooks where useful.
7. Add structured audit logging and alerting without logging secrets/tokens.
8. Rotate any token or deploy hook ever exposed in a screenshot or chat.
9. Define deletion/retention periods for drafts, media, analytics and logs.
10. Have final Terms, Privacy Policy, processor/subprocessor wording and regional compliance reviewed professionally.

## Media caution

The fallback local media directory is not durable on ephemeral hosting. It is suitable only for development/immediate testing. Use persistent storage for production.

## Scheduling caution

A scheduler running inside a sleeping free web instance cannot guarantee execution at the requested minute. Use an always-on deployment or external job scheduler before selling scheduling as exact/reliable.
