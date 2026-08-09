# X Creator Studio — V4

V4 adds a creator-facing web interface on top of the existing multi-tenant X posting backend.

## What creators can do

- Connect an X account with OAuth
- Enter Creator Studio automatically after connecting
- Sign in later using their creator key
- Draft manually
- Optionally generate a draft with the OpenAI API
- See the exact connected X account
- Preview character count
- Confirm and publish
- View recent publishing activity

Existing Custom GPT Actions and V3 API routes remain supported.

## New routes

- `/studio` — creator dashboard
- `/studio/login` — sign in with creator key
- `/studio/api/me`
- `/studio/api/preview`
- `/studio/api/publish`
- `/studio/api/recent`
- `/studio/api/ai/draft`

## Upgrade from V3

Replace these files in the existing GitHub repository:

- `app.py`
- `requirements.txt`
- `render.yaml`
- `README.md`

Keep all existing environment variables and database resources.

## New Render variables

`SESSION_SECRET`

- Render can generate this automatically from the Blueprint.
- It signs secure 30-day browser sessions.

`OPENAI_API_KEY` (optional)

- Required only for the in-browser AI drafting button.
- Keep this in Render environment variables; never place it in browser code or GitHub.

`OPENAI_MODEL`

- Defaults to `gpt-5-mini` in `render.yaml`.
- Change it in Render if needed.

## Deploy

1. Upload and commit the V4 replacement files to GitHub.
2. In Render, sync the Blueprint or add the new environment variables manually.
3. Use **Manual Deploy → Clear build cache & deploy**.
4. Confirm `/health` returns version `4.0.0`.
5. Open `/connect/x` and connect a test account, or open `/studio/login` and use an existing creator key.

## Interface flow

New creator:

`/connect/x` → X authorisation → callback → creator key shown once → signed session → `/studio`

Existing creator:

`/studio/login` → creator key → signed session → `/studio`

## Security notes

- X and OpenAI credentials remain server-side.
- Creator keys are hashed in the database.
- X OAuth tokens remain encrypted at rest.
- Browser sessions are HttpOnly, Secure and SameSite=Lax.
- Publishing requires an explicit confirmation modal in the interface.
- Creator Studio never lets the browser choose a different X account.

## Suggested next upgrades

- Creator profile and saved voice instructions
- Threads and replies
- Images
- Scheduling and queued posts
- Passwordless email login instead of creator-key login
- Billing and plan limits
- Admin dashboard
