# X Poster V2 — Multi-Tenant Backend

This upgrades the original one-account service into a shared backend that can safely serve multiple creators.

## What changes

Before:

`one GPT → one Render service → one X account`

Now:

`many GPTs → one Render service + Postgres → the correct X account`

Each creator receives a separate bearer key. The backend hashes that key, maps it to one creator record, decrypts only that creator's X credentials, and posts to that account. The GPT never chooses the target account.

## Safety model

- Creator API keys are stored only as SHA-256 hashes.
- X credentials are encrypted in the database using Fernet.
- The encryption key stays in Render environment variables.
- Admin onboarding uses a separate `ADMIN_API_KEY`.
- Publishing still requires `approved=true`.
- Every publish attempt is written to `post_logs`.

## Upgrade the existing Render service

### 1. Back up first

Keep a copy of the current working repo and note the existing Render environment variables. Do not delete the current GPT Action authentication key until the migration is complete.

### 2. Replace/add the repository files

Upload this package to the same repository and commit it.

### 3. Generate an encryption key

Run locally:

```bash
python generate_fernet_key.py
```

Or run:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output into Render as `CREDENTIAL_ENCRYPTION_KEY`. Keep it permanently. Losing it makes stored X tokens unreadable.

### 4. Add Postgres and environment variables

Sync the updated Blueprint or manually create a Render Postgres database and set `DATABASE_URL` to its internal connection string.

Required service variables:

- `DATABASE_URL`
- `ADMIN_API_KEY`
- `CREDENTIAL_ENCRYPTION_KEY`

To preserve DataMaxxing during the first deployment, also keep:

- `X_API_KEY`
- `X_API_SECRET`
- `X_ACCESS_TOKEN`
- `X_ACCESS_TOKEN_SECRET`
- `X_USERNAME=DataMaxxing`
- `BOOTSTRAP_CREATOR_NAME=DataMaxxing`
- `BOOTSTRAP_CREATOR_API_KEY=<the same key currently used by the DataMaxxing Custom GPT>`

On startup, the app inserts DataMaxxing into Postgres once. Existing GPT authentication therefore continues to work without changing the GPT.

After `/health` works and DataMaxxing can preview successfully, you may remove the four `X_*` bootstrap secrets and `BOOTSTRAP_CREATOR_API_KEY` from Render. The encrypted copy remains in Postgres. Keep `CREDENTIAL_ENCRYPTION_KEY`.

## Add a second creator manually

Use the admin endpoint. Do not put any real secrets into chat or source control.

```bash
curl -X POST "https://YOUR-SERVICE.onrender.com/admin/creators" \
  -H "Authorization: Bearer YOUR_ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Creator Two",
    "x_username": "creator_two",
    "x_api_key": "...",
    "x_api_secret": "...",
    "x_access_token": "...",
    "x_access_token_secret": "..."
  }'
```

The response contains `creator_api_key`. Copy it immediately; only its hash is stored.

Create or duplicate a private Custom GPT, use the same `openapi-action.yaml`, and set its Action bearer key to that creator's new `creator_api_key`.

Both GPTs use the same Render URL. Their different bearer keys determine which X account receives the post.

## List creators

```bash
curl "https://YOUR-SERVICE.onrender.com/admin/creators" \
  -H "Authorization: Bearer YOUR_ADMIN_API_KEY"
```

## Deactivate a creator

```bash
curl -X POST "https://YOUR-SERVICE.onrender.com/admin/creators/2/deactivate" \
  -H "Authorization: Bearer YOUR_ADMIN_API_KEY"
```

## Test a creator key

```bash
curl -X POST "https://YOUR-SERVICE.onrender.com/x/preview" \
  -H "Authorization: Bearer CREATOR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"text":"Testing creator routing"}'
```

The response includes the linked `account`, so you can verify routing before publishing.

## OAuth-ready design

This version still onboards creators by entering credentials through the protected admin endpoint. The database and account routing are now in place for the next phase: adding `/connect/x` and `/callback/x` so a creator can authorize your single X developer app with a Connect X button.

For that phase, the credential columns can store OAuth-issued access tokens instead of manually supplied tokens. The GPT-facing posting endpoints do not need to change.

## Important limitation

A free Render Postgres database has lifecycle and storage constraints. It is fine for proving the multi-tenant flow, but review Render's current database terms before relying on it for paying customers.
