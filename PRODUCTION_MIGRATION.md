# Zova production migration checklist

This checklist is intentionally value-free: it documents configuration names, never credentials.

## Live inventory checked 29 August 2026

- Production web service: `x-chatgpt-poster` (`srv-d9rqg6navr4c739thoeg`), deployed from `main` with auto-deploy enabled.
- TikTok sandbox web service: `zova-tiktok-sandbox` (`srv-d9u4joad0e5s73afpu10`).
- Managed database: `x-chatgpt-poster-db` (`dpg-d9sdpdvavr4c73b2b0bg-a`), PostgreSQL 18, database name `x_poster`.
- The database is on Render's Free tier, so point-in-time recovery and exports are unavailable.
- Render warns that the free database expires on 8 September 2026 and will be deleted unless upgraded.
- The production service has `DATABASE_URL` and `CREDENTIAL_ENCRYPTION_KEY` configured. Values were not revealed.
- TikTok client credentials and `TIKTOK_SEND_TO_INBOX` are configured on the separate sandbox service, not the production service.
- Meta and Instagram app credentials are configured on the sandbox service, not the production service.

## Data preservation gate

Before merging or deploying:

1. Confirm the Render web service's `DATABASE_URL` references the existing managed PostgreSQL database.
2. Take a PostgreSQL backup or recovery-point snapshot and record its timestamp outside the repository.
3. Keep `CREDENTIAL_ENCRYPTION_KEY` unchanged. Rotating or losing it makes existing OAuth tokens unreadable.
4. Keep `SESSION_SECRET` unchanged unless intentionally invalidating every login session.
5. Do not rename or replace the existing Render database resource during this migration.

`APP_ENV=production` makes Zova fail closed if `DATABASE_URL` is absent or points to SQLite.

## Environment-variable inventory

Required application/security values:

- `APP_ENV`
- `DATABASE_URL`
- `PUBLIC_BASE_URL`
- `SESSION_SECRET`
- `CREDENTIAL_ENCRYPTION_KEY`
- `ADMIN_API_KEY`
- `ADMIN_EMAILS`
- `PRIVACY_CONTACT_EMAIL`

Provider values to preserve and verify:

- `OPENAI_API_KEY`, `OPENAI_MODEL`
- `X_OAUTH2_CLIENT_ID`, `X_OAUTH2_CLIENT_SECRET`, `X_OAUTH2_REDIRECT_URI`
- `META_APP_ID`, `META_APP_SECRET`, `META_GRAPH_VERSION`, `META_REDIRECT_URI`
- `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REDIRECT_URI`, `TIKTOK_DEFAULT_PRIVACY`, `TIKTOK_SEND_TO_INBOX`
- `APPLE_CLIENT_ID`, `APPLE_TEAM_ID`, `APPLE_KEY_ID`, `APPLE_PRIVATE_KEY`, `APPLE_REDIRECT_URI`
- `STRIPE_SECRET_KEY`, `STRIPE_PRICE_ID`, `STRIPE_WEBHOOK_SECRET`
- `S3_BUCKET`, `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_PUBLIC_BASE_URL`, `S3_ENDPOINT_URL`
- `SCHEDULER_SECRET`, `SCHEDULER_INTERVAL_SECONDS`

Temporary review values:

- `REQUIRE_SUBSCRIPTION=false`
- `REVIEWER_SEED_ENABLED=true`
- `REVIEWER_EMAIL=tiktok-review@zova-social.com`
- `REVIEWER_PASSWORD` (unique temporary value; environment only)

Legacy X variables must remain if the backward-compatible Custom GPT action is still used:

- `BOOTSTRAP_CREATOR_API_KEY`, `BOOTSTRAP_CREATOR_NAME`
- `X_USERNAME`, `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`

## Production URL values

- `PUBLIC_BASE_URL=https://zova-social.com`
- `APPLE_REDIRECT_URI=https://zova-social.com/auth/apple/callback`
- `X_OAUTH2_REDIRECT_URI=https://zova-social.com/callback/x`
- `META_REDIRECT_URI=https://zova-social.com/oauth/meta/callback`
- `TIKTOK_REDIRECT_URI=https://zova-social.com/oauth/tiktok/callback`

## Deployment verification

- Public: `/`, `/signup`, `/login`, `/terms-of-service`, `/privacy-policy`, `/refund-policy`, `/health`
- Authenticated: `/studio`, `/drafts`, `/account`, `/analytics`
- OAuth: start and callback for X, TikTok and Meta
- Reviewer: login, sample draft, sample analytics, no pre-attached social connections
- TikTok sandbox: connect, creator-info query, upload video, send draft to inbox, confirm processing state

Do not submit TikTok externally until the user explicitly approves the final submission. Do not resubmit Meta App Review yet.
