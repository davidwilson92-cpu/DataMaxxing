# Zova user data model

Zova deliberately keeps the account record small. `nova_users` stores the user's normalized email, display name, ISO 3166-1 alpha-2 country code, account state, Stripe references/status, consent records, and account timestamps.

## Storage decisions

- **Hash, never encrypt:** passwords. Zova stores a unique salted `scrypt` hash and never stores or logs the original password. Passwords only need comparison, not recovery.
- **Application-level encryption:** OAuth access/refresh tokens and other provider credentials. Zova must recover these values to call providers, so they cannot be hashed. They use `CREDENTIAL_ENCRYPTION_KEY`.
- **Queryable plaintext, protected by managed database encryption:** normalized email, display name, and country code. Signup/login, uniqueness checks, support, billing, and personalisation need to query or display these fields. Encrypting them in the application would complicate exact lookup, indexing, key rotation, and operational support without removing the need to protect the running application. Production must use encrypted database volumes/backups, TLS connections, least-privilege database credentials, and restricted staff access.
- **Plaintext operational metadata:** subscription state, Stripe opaque IDs, consent flags/timestamps, verification/login/update timestamps, and the active flag. These are not secrets, but access must still be restricted and audited.

Do not store card details: Stripe owns that data. Do not add date of birth, street address, phone number, IP history, or free-form demographic data unless a defined product/legal need and retention period exist.

## Migration

`nova.migrations.run_migrations` records forward-only migrations in `zova_schema_migrations` and safely adds the new columns to existing SQLite or PostgreSQL databases at application startup. Back up the production database before deploying any schema change.

## Recommended follow-ups before public launch

Add email verification, password reset, account export/deletion, login/signup rate limiting, short retention periods, and automated deletion of expired authentication state. Keep secrets in the deployment secret store and rotate `CREDENTIAL_ENCRYPTION_KEY` only with a planned token re-encryption migration.
