# PostgreSQL workspace policies and transaction authority

Candidate foundation, not automatically activated on application startup or production. Do not activate on the web/worker database until every affected service has a context/credential rollout. Current application behavior remains unchanged by this isolated migration module.

## Boundary

The offline migration in nova/rls.py installs ENABLE/FORCE RLS and restrictive SELECT/INSERT/UPDATE/DELETE policies on all 16 brand-owned tables. An unrelated permissive policy cannot OR away the workspace boundary. Writes additionally require the current request capability in the explicit per-table manifest. Database ownership guards remain in place. These policies do not replace immutable publication approval or endpoint/object authorization.

A separate context-issuer identity validates current owner membership, role capability, user activity, authentication version and membership revision. The runtime identity cannot mint contexts, enumerate their hashes, mutate authority records or assume the issuer role. A context is a random 256-bit bearer value held only on the server; only its SHA-256 hash is stored in the database. It is bound to a runtime login, backend process and transaction ID, with a default 60-second / maximum 300-second expiry. A plain workspace ID, forged token, another connection, commit/rollback or even a lingering session-level token does not carry authority forward. Membership and session revocation are checked again on each statement. Issuance prunes at most 1000 expired contexts per call using skip-locked cleanup.

The service calling issue_context must obtain user/workspace/version/capability from trusted authentication and authorization, never request-body claims. It uses a separate issuer connection, with only explicit function execution rights. The runtime transaction must use READ COMMITTED so fresh contexts and revocations are visible. Issuer compromise is privileged; its credential isolation, monitoring and per-service authorization remain rollout requirements.

Security-definer functions have a fixed catalog/schema search path and narrowly reviewed bodies. PUBLIC/old function execution grants are revoked before explicit issuer/runtime grants; direct context-table access is refused. Runtime roles with inherited administrative/owner authority, schema creation or direct authority-table mutations are rejected. Database superusers and migration owners remain privileged operators, not valid runtime identities.

## Validation

PostgreSQL tests seed every protected table for two synthetic owners and exercise unfiltered direct reads, forged context/IDs, permissive-policy coexistence, write refusal under read contexts, cross-tenant writes, revocation, expiry, transaction/connection replay and issuer separation. The CI restore fixture also enables these policies and validates default denial, own-workspace reads, read-context write refusal and cleared transaction authority after restoration. At b6e1475, CI SQLite passed 408 tests with 20 expected skips; PostgreSQL passed 427 with one expected skip. Runs 37992138379 / 37992133548 passed restored RLS, image build/smoke and Python dependency audit. Evidence: evidence/workspace-rls-20261009.json. Local SQLite cannot establish RLS correctness.

## Remaining integration and rollback

No production role or schema is changed. Web request/session transaction hooks, OAuth callback authority, worker claims/recovery, global/account operations, final per-operation grants, issuer credential provisioning and account/legacy mapping remain unfinished. The current policies cover existing owner-scoped content, not shared teams or every customer-owned table. Work through those paths before adding this migration to the production runbook or declaring tenant isolation complete.

Pause writes/workers and rehearse on an isolated restored copy first. Existing IDs, credential bytes, uploads, auth keys and publication outcomes are preserved. After activation, use a forward fix maintaining tenant enforcement; never disable RLS or grant broad credentials merely to restore service. Complete policy/grant/context restoration must be verified, not inferred from row counts. Independent security and operational review remain required.

References: PostgreSQL row security policies (https://www.postgresql.org/docs/current/ddl-rowsecurity.html) and built-in SHA-256 (https://www.postgresql.org/docs/current/functions-binarystring.html).
