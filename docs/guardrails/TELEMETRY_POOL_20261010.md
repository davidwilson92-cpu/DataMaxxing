# Isolated product and AI measurement writes

Candidate only; local and PostgreSQL validation pending. No production roles,
credentials, account records, provider calls or deployment changed.

Previously, readiness.event and record_ai opened the shared SessionLocal pool.
Restricted draft tests mocked product events, leaving the real post-save path
unverified. Configured service requests now establish a task-local telemetry
factory in middleware. Synchronous handlers and asynchronous child tasks inherit
their request's factory. The parent restores its previous context even when a
handler fails. Background ASGI child tasks retain their own context copy.

create_services optionally accepts a separate telemetry engine, alongside the
identity/content/issuer and optional authentication/recovery engines. It verifies
distinct restricted credentials, the same database/schema, no cross-role
membership or context-function execution, exact column grants and no sequence
rights. The telemetry role may only insert named product-event and AI-call
metadata columns. It cannot read, update or delete measurements or access user,
draft, social credential or account authority records. New ORM columns do not
automatically gain write permission.

When configured services omit telemetry, requests bind an explicitly unavailable
factory rather than reverting to shared credentials. Unavailable measurement
writes produce a generic warning without exception details, leave committed
customer output intact and do not trigger provider retries. Duplicate product
events remain harmless in their separate transaction. The existing application
mode is unchanged when separated services are absent.

Synthetic tests cover real draft save and persisted event metadata without
mocking readiness.event, duplicate events, telemetry outages after successful
saves, missing-pool behavior with shared factories poisoned, append-only grants,
metadata-only AI records and a successful mocked AI response during a recording
failure. Concurrent task/exception tests check context isolation and restoration.

Limits: the telemetry role is a trusted append service across account IDs, not
account-level RLS or a read/reporting service. Worker/non-HTTP execution must
explicitly establish telemetry_scope during its later service integration.
Production alert delivery, retention, reporting access, cost calibration and
complete worker/callback/account routing remain open. AI routes remain unmapped
in staged mode; a mocked provider scope test does not prove those full routes.
The partially mapped service mode must not be enabled for customers yet.

Before activation, rollback is code-only. After activation, preserve measurement
and customer records; investigate a role/configuration failure without granting
broad access or retrying completed content/provider actions. Observability repair
must not reset credentials, duplicate posts or lose a saved draft.
