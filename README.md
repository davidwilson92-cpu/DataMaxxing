# X Poster V3 — OAuth onboarding

V3 keeps existing OAuth 1.0a creators working and adds self-service OAuth 2.0 Authorization Code + PKCE onboarding.

## New public routes

- `/connect/x` — simple onboarding page with a Connect X button
- `/connect/x/start` — begins X authorization
- `/callback/x` — exchanges the authorization code, retrieves the X account and stores encrypted tokens
- `/privacy` — privacy policy page

## X Developer Portal configuration

In the X Developer Portal, enable OAuth 2.0 for the platform app.

Use a Web App / confidential client configuration and set:

- Callback URL: `https://x-chatgpt-poster.onrender.com/callback/x`
- Website URL: `https://x-chatgpt-poster.onrender.com/connect/x`

The app requests:

- `tweet.read`
- `tweet.write`
- `users.read`
- `offline.access`

Copy the OAuth 2.0 Client ID and Client Secret into Render as:

- `X_OAUTH2_CLIENT_ID`
- `X_OAUTH2_CLIENT_SECRET`

Also add/check:

- `PUBLIC_BASE_URL=https://x-chatgpt-poster.onrender.com`
- `X_OAUTH2_REDIRECT_URI=https://x-chatgpt-poster.onrender.com/callback/x`

## Deploy

Replace the repository's V2 versions of:

- `app.py`
- `requirements.txt`
- `render.yaml`
- `.env.example`
- `README.md`

Commit and push, then sync the Render Blueprint or deploy the latest commit.

After deployment, check:

`https://x-chatgpt-poster.onrender.com/health`

Expected response:

```json
{"status":"ok","version":"3.0.0"}
```

Then open:

`https://x-chatgpt-poster.onrender.com/connect/x`

The callback creates a creator record, encrypts the OAuth access and refresh tokens, and shows a one-time `creator_api_key`. That key goes into the new creator's private Custom GPT Action as Bearer authentication.

## Important

- Existing DataMaxxing and JHFootballAgent creator records continue using their current OAuth 1.0a credentials.
- Newly connected creators use OAuth 2.0.
- The creator key shown after connection is displayed only once.
- Keep the GPT private and never put creator keys into GPT instructions or the OpenAPI schema.
