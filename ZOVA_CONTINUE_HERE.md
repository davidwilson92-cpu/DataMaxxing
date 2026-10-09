# Current increment: restricted draft and issuer privileges

Validated e2d9534: local/CI SQLite 415 passed / 58 expected skips; PostgreSQL 472 passed / one expected skip. CI run 38001835142 passed real restricted-role attachment/Story/planning/delete flows, privilege attacks, migrated restore, image build/smoke and dependency audit. Evidence: docs/guardrails/evidence/draft-grants-20261009.json. Production unchanged; full gate blocked and publication goal active.

Read docs/guardrails/DRAFT_GRANTS_20261009.md. nova/service_permissions.py defines exact table/column grants for mapped draft database operations, verified by create_services. Draft role cannot read social credentials, private media locations, approval payloads or account secrets; it cannot mutate approval content, ownership, draft delivery status or publishing records. Issuer has zero direct table grants. All configured pools verify sequence rights: draft allocator USAGE only, no resets or other allocators. clean_workspace and draft activity summaries select only needed metadata. Service fixtures use these grants, while the broader RLS foundation fixture remains isolated policy-test machinery.

NEXT: isolate product/AI telemetry factories before enabling mapped routes; current draft-save tests still mock readiness.event, whose implementation uses shared SessionLocal. Then signup/profile/account lifecycle, Apple/social/billing callback brokers, worker/legacy routing and their final grant manifests. Signup must atomically provision account/workspace/membership without broad authority grants or restoring revoked memberships. Account-level immutable references/RLS and production grant/restore rehearsal remain open. Do not enable partial staged mode for customers. Preserve all users/data/keys, explicit publishing approval and unknown outcomes; no paid staging, forced MFA or gate bypass.

---

# Current increment: complete installed workspace policy verification

Validated e3376ef: CI SQLite 415 passed / 50 expected skips; PostgreSQL 464 passed / one expected skip. CI run 38000761139 passed policy drift attacks, migrated RLS restore, full restored policy/context definitions, image build/smoke and dependency audit. Evidence: docs/guardrails/evidence/policy-verification-20261009.json. Production unchanged; full gate remains blocked (80 entries) and publication goal active.

Read docs/guardrails/POLICY_VERIFICATION_20261009.md. create_services now verifies all 16 table policy sets, forced/enabled state, actual role OIDs, commands, permissiveness and full canonical predicates/checks with exact capability lists. It rejects disabled/missing/weakened/extra policies without DDL or automatic repair. Tests reproduce the previous startup acceptance and unbound draft disclosure when isolation is disabled/weakened. The restore script validates both context functions and the complete policy manifest. Unknown PostgreSQL deparser formatting fails closed; CI validates PostgreSQL 18.

NEXT: final content/worker column-grant manifests; signup/profile/account lifecycle, Apple/social/billing callback brokers, telemetry and worker/legacy routing. Signup must atomically provision User/workspace/membership without broad authority grants or restoring revoked memberships. Account-level immutable references/RLS remain open. Do not enable the partial staged service mode for customers. Runtime post-startup integrity monitoring and operational/independent assurance remain open. Preserve all users/data/keys, explicit publishing approval and unknown outcomes; no paid staging, forced MFA or gate bypass.

---

# Current increment: verify installed database context functions

Validated 18d1fa7: local/CI SQLite 415 passed / 41 expected skips; PostgreSQL 455 passed / one expected skip. CI run 37999971907 passed altered-definition attacks, migrated RLS restore, image build/smoke and dependency audit. Evidence: docs/guardrails/evidence/context-verification-20261009.json. Production unchanged; full release gate blocked and publication goal active.

Read docs/guardrails/CONTEXT_VERIFICATION_20261009.md. Offline migration and startup now share context_function_definitions in nova/rls.py. create_services verifies catalog bodies and execution properties, parameter/default semantics and the exact issuer runtime audience before accepting service pools. It rejects changed/missing definitions without executing or repairing them. Tests demonstrate the old grant-only check accepted the altered functions. This verifies the two functions only, not exact table policies or live post-startup integrity.

NEXT: complete exact installed table-policy expressions/role/operation verification and final content/worker column grants. Continue signup/profile/account lifecycle, Apple/social/billing callback brokers, telemetry and worker/legacy mapping. Signup must provision User/workspace/membership atomically without broad authority grants or restoring revoked memberships. Account-level RLS and immutable account references remain open. No customer activation until all routes and operational assurance pass. Preserve users/data/keys, explicit publishing approval and unknown outcomes; no paid staging, forced MFA or release-gate bypass.

---

# Current increment: password races and restricted recovery service

Validated 212794e: CI SQLite 415 passed / 32 expected skips; PostgreSQL 446 passed / one expected skip. Runs 37998910309 / 37998904763 passed concurrent password/MFA races, real restricted recovery lifecycle with mocked SMTP, migrated RLS restore, image build/smoke and dependency audit. Evidence: docs/guardrails/evidence/recovery-pools-20261009.json. Production unchanged; full gate still blocked and publication goal active.

Read docs/guardrails/RECOVERY_POOLS_20261009.md. Password change captures the validated session version, conditionally updates active User with that version and old hash, and issues a cookie only at the expected next version. Concurrent changes cannot reuse one security version or bypass intervening MFA enrollment. Default engines now hide SQL bound parameters. create_services accepts recovery_engine only alongside authentication_engine; the fifth role has User SELECT and UPDATE only password_hash/auth_version/updated_at, plus recovery-token and mail-status SELECT/INSERT/UPDATE. It cannot touch MFA, billing, email, membership or social credentials. Forgot/reset and their background mail/status callbacks carry explicit factories; rate limits use the identity pool. Existing mode remains compatible when services are absent. No production activation switch exists.

NEXT: map signup and profile/account lifecycle, Apple/social/billing callback brokers, telemetry and worker/legacy paths. Signup must atomically provision User/workspace/membership without broad authority-table grants or silently restoring revoked memberships. Authentication/recovery pools are trusted cross-account services; account-level RLS and immutable account references remain open. Complete exact policy/function verification, staged Studio/public-page routing, final grants and operational assurance before deployment configuration. Preserve all users/data/keys, explicit publishing confirmation and unknown outcomes; no paid staging, forced MFA or release-gate bypass.

---

# Current increment: restricted password sign-in, optional MFA and logout

Validated a9dd94b: CI SQLite 412 passed / 31 expected skips; PostgreSQL 442 passed / one expected skip. CI runs 37997449697 / 37997443303 passed password sign-in, opt-in MFA, concurrent one-use recovery, logout and column-grant attacks with shared factories poisoned, plus migrated RLS restore, image build/smoke and dependency audit. Evidence: docs/guardrails/evidence/authentication-pools-20261009.json. Production unchanged; full gate remains blocked and publication goal active.

Read docs/guardrails/AUTHENTICATION_POOLS_20261009.md. create_services accepts an optional separate authentication_engine. Its role reads User/revoked sessions, inserts revocations, SELECT/INSERT/UPDATE MFA settings, CRUD MFA challenges; User UPDATE is column-limited to last_login_at/auth_version/updated_at. Password/email/active/membership/content and MFA-settings DELETE are denied. verify_pool_grants checks exact table/column manifests. With this fourth pool configured, staged middleware/dependency allow password login, MFA routes and logout. Cookie verification and factor rate limits use the identity pool. Existing application mode is unchanged when services are absent; there is still no production activation switch. Existing password-only accounts are not enrolled. Password and Apple concurrent-MFA-enrollment regression checks pass; Apple routing in staged mode is still blocked.

NEXT: map signup, password reset/change and account lifecycle with validated authority, plus Apple/social/billing callback brokers, telemetry and worker/legacy identities. Authentication service has cross-account authentication-record authority; account-level RLS and immutable account ownership remain open, so do not equate limited column grants with tenant isolation. Verify exact installed policy/function definitions and full service grants, then complete staged Studio/public-page routing and deployment configuration. Preserve users/data/keys/session continuity, explicit publishing confirmation and unknown outcomes. No paid staging, forced customer MFA or gate bypass.

---

# Current increment: real draft requests through separated service identities

Validated 4038fb2: CI SQLite 411 passed / 29 expected skips; PostgreSQL 439 passed / one expected skip. CI runs 37995650285 / 37995645267 passed normal get_db/current_user/rate-limit draft flows with no dependency override or shared-credential fallback, privilege attacks, migrated RLS restore, image build/smoke and dependency audit. Evidence: docs/guardrails/evidence/service-pools-20261009.json. Production unchanged; full gate blocked, publication goal active.

Read docs/guardrails/SERVICE_POOLS_20261009.md. create_services(identity_engine,runtime_engine,issuer_engine) verifies distinct restricted logins in the same database/schema, no cross-role membership, exact identity table/column grant manifest and separated context-function execution/ownership. Identity can SELECT users/revocations/brands/workspaces/memberships and mutate request limits, not content or account authority. Configured services attach through trusted app.state.database_services; get_db/current_user/middleware use them. Middleware rejects every unmapped route, including handlers without get_db. Current allowlist: draft CRUD, health, static only. There is NO production activation switch; do not enable this partial mode for customers. Existing mode stays unchanged when absent. Tests use actual restricted identities and poison the old shared factories; readiness telemetry remains mocked.

NEXT: extend isolated services to sign-in/signup/account mutations, session logout/recovery/MFA and telemetry; signed OAuth/billing callback brokers; worker claim/recovery and legacy identities. Add exact installed policy/function and full service/column grant verification before rollout configuration. Direct SessionLocal/worker paths remain unintegrated, so enabling database policies globally is still unsafe. Keep no paid staging, no forced customer MFA, explicit publishing confirmation and all data/credentials/unknown outcomes. No gate bypass.

---

# Current increment: brand and draft deletion compatibility under RLS

Validated cc70b7d: local/CI SQLite 410 passed / 25 expected skips; PostgreSQL 434 passed / one expected skip. CI runs 37994384382 / 37994380750 passed second-brand draft HTTP create/save/reload, reproduced old policy deletion failure and verified corrected atomic cleanup, migration/RLS restore, image build/smoke and dependency audit. Evidence: docs/guardrails/evidence/draft-policy-20261009.json. Production unchanged; full gate blocked, publication goal active.

Read the follow-up in docs/guardrails/WORKSPACE_SESSIONS_20261009.md. The content factory explicitly installs existing brand ownership hooks. RLS operation_capabilities grants posts.delete only for review DELETE and strategy-action/occurrence UPDATE, enabling delete_unsubmitted_draft without granting review creation/content mutation or plan deletion. Tests preserve other-workspace references and published history. Final column-level service grants remain open. The RLS factory remains opt-in and no production roles/policies were changed.

NEXT: integrate independently restricted auth/account and content pools into web dependencies. Map signed OAuth callbacks, billing, legacy API identities, account telemetry and worker claim/recovery. Verify startup policies and exact grants before activation. Audit remaining compound operations and cross-record workspace references. Do not globally enable RLS while shared SessionLocal account/worker flows remain unintegrated. Preserve all existing user/data/provider state and unknown publication outcomes; no paid staging or forced MFA, no gate bypass.

---

# Current increment: protected application content transactions

Validated 5ac264d: local/CI SQLite 409 passed / 23 expected skips; PostgreSQL 431 passed / one expected skip. CI runs 37993492489 / 37993486479 passed draft HTTP integration under restricted content credentials, transaction/revocation attacks, migrated RLS restore, image build/smoke and dependency audit. Evidence: docs/guardrails/evidence/workspace-sessions-20261009.json. Production unchanged; full gate still blocked and publication goal active.

Read docs/guardrails/WORKSPACE_SESSIONS_20261009.md. nova/workspace_session.py derives frozen workspace claims from validated authentication through a separate auth session, preserves the original auth_version and rejects revoked claims. content_session rebinds a fresh issuer context on every outer transaction, including commit/refresh and rollback. Savepoints retain transaction authority. Session.get refreshes against policies instead of trusting cached identity. Require hidden SQL parameters and no engine echo. This factory is opt-in and NOT globally wired into SessionLocal. Tests use fixture-admin authentication/rate-limit pools and mocked readiness telemetry; final restricted auth grants are unvalidated.

NEXT: integrate independently restricted auth/account and content pools into web dependencies; explicitly register existing brand ORM hooks for factory-only entry points and test nonzero-brand inserts. Map signed OAuth callbacks, billing, legacy API identities, account telemetry and worker claims/recovery. Reconcile per-table write capabilities with legitimate compound operations (draft deletion also dismisses strategy actions/series occurrences). Add active-policy/grant startup verification before activation. Do not just enable RLS globally; shared account/worker flows would break. Preserve all user/data/provider state, no paid staging or forced customer MFA, no gate bypass.

---

# Current increment: tested PostgreSQL workspace policy foundation

Validated b6e1475: CI SQLite 408 passed / 20 expected skips; PostgreSQL 427 passed / one expected skip. Runs 37992138379 / 37992133548 passed direct SQL attacks, restored RLS, image build/smoke and Python dependency audit. Evidence: docs/guardrails/evidence/workspace-rls-20261009.json. No production changes; full release gate blocked, publication goal active.

Read docs/guardrails/WORKSPACE_RLS_20261009.md. nova/rls.py provides an offline apply_rls migration for all 16 brand-owned tables with forced restrictive policies. It is NOT called by application startup. Separate runtime/issuer identities are mandatory. The issuer validates live owner membership/capability/auth version/revision; a random server-only token is stored only as a hash, bound to runtime login/backend/transaction and 60-second (maximum 300-second) expiry. issue_context takes the issuer engine AND the current runtime connection; bind_context sets transaction-local authority. READ COMMITTED is required. Commit/rollback/session-setting replay, other connections, forged IDs/tokens and revocation fail closed.

Runtime cannot mint/read/edit contexts or mutate authority tables. Migration rejects owner/admin/inherited broad privileges, destructive table rights and overlapping issuer/runtime identities. Write capabilities are per-table; RLS does not replace endpoint/object checks or immutable publishing approval. Security-definer search paths and execution grants are fixed/restricted. CI dump/restore now rehearses restricted-login policy behavior too. No production roles, credentials, grants or posts were changed.

NEXT: integrate web/auth/account transaction pools and worker claim/recovery authority before activating RLS. Existing SessionLocal is still shared across those paths, so simply enabling policies would break legitimate account/worker operations. Map every route/service to exact credentials/capabilities; introduce isolated issuer credentials without fallback; use parameter-hidden database engines and never log server tokens. Extend startup verification to require expected active policies/grants for the integrated mode. Complete account-level/legacy mapping and shared-role service routing. Keep the production gate intact; no paid staging or forced MFA.

---

# Current increment: restricted runtime startup and verified image pins

Validated 80db06c: CI SQLite 405 passed / 7 expected skips; PostgreSQL 411 passed / one expected skip. Runs 37990057499 / 37990050801 passed application, real restricted-login/DDL attack checks, migrated restore, build/smoke and Python dependency audit. Local SQLite also passed 405 / 7. Evidence: docs/guardrails/evidence/restricted-startup-20261009.json. No production change; goal active, full production gate still blocked.

Read docs/guardrails/RESTRICTED_STARTUP_20261009.md. PostgreSQL now defaults to ZOVA_SCHEMA_MODE=verify, doing read-only schema/version/guard checks and rejecting privileged runtime identities (including original login masking, built-in roles and CREATE/TRUNCATE/ownership). Offline scripts/prepare_database.py requires --apply --writes-paused and explicit ZOVA_MIGRATION_DATABASE_URL; existing users still require registry/reference backfill first. CI fixtures explicitly bootstrap. Candidate blueprint sets verify; the live host has NOT been changed.

Docker Hub quotas blocked earlier CI pulls. Pinned Python/PostgreSQL manifest bodies were independently fetched and matched across Docker Hub and Docker's official ECR mirror. CI uses the mirror; Dockerfile defaults to the identical pinned Docker Hub Python image. See image-pins-20261009.json / CI_SECURITY.md. No paid account or infrastructure was created.

Next: RLS with validated transaction context, final per-operation service grants and separate application/worker/auth/analytics identities; account-level and legacy authority mapping. Current test DML grants are compatibility evidence, not the final production manifest. Do not call this complete read isolation. Preserve explicit publishing approval, both Instagram routes, existing data/keys/auth and unknown sends. No forced MFA or paid staging; no guardrail bypass.

---

# Current increment: canonical workspace runtime integration

Validated dc55d2b: local/CI SQLite 398 passed / 6 expected skips; PostgreSQL 403 passed / one expected skip. Runs 37988211823 / 37988205275 passed application, migrated restore, build/smoke and dependency checks. Evidence: docs/guardrails/evidence/canonical-runtime-20261009.json. Production gate remains blocked; publication goal remains active. No production change.

Read docs/guardrails/CANONICAL_RUNTIME_20261009.md. All 16 brand-owned ORM models now map workspace_id; inserts validate/populate it, immutable updates are rejected and scoped content queries use it alongside existing owner/brand predicates. Fresh installs activate reference guards. Existing populated databases verify references and version before startup: offline migration is mandatory before deployment. Both Instagram routes and explicit publishing confirmation remain in the regression suite.

Next: restricted PostgreSQL identities/RLS, validated transaction contexts for web and workers, account-level and legacy creator authority. Inspect startup DDL and global worker/session queries before enabling restrictions. Do not claim ORM filtering protects raw SQL or unscoped jobs. Do not remove controls, force MFA or provision paid staging. Keep additive data and pending/unknown publication outcomes; use forward recovery.

---

# Current increment: bounded migration safety

Validated commit 09c5771: SQLite 393 passed / 6 expected skips; PostgreSQL 398 passed / one expected skip. Runs 37986816507 / 37986810059 passed application, contention/cancellation, migrated restore, build/smoke and dependency checks. Evidence: docs/guardrails/evidence/migration-limits-20261009.json. No production changes; release goal remains active.

Both registry/reference migrations now bound PostgreSQL lock acquisition to five seconds and statements to two minutes, using transaction-local settings before advisory locks. Contention rolls back cleanly and subsequent retry succeeds. Reference preview now rejects incorrect existing canonical values. These are per-statement limits, not a total migration deadline. Full production gate remains blocked; no waiver or deployment.

Next: runtime canonical read binding/fresh-schema integration, restricted PostgreSQL roles/RLS, account-level and legacy authority mapping. Inspect db.py startup DDL and unscoped worker sessions before enabling restrictions. Preserve write compatibility, current identities and all pending/unknown publishing outcomes. Do not claim offline integrity guards establish read isolation.

---

# Current increment: canonical reference migration and database write guards

Validated commit a3b7610: CI SQLite/PostgreSQL each 387 passed, one expected backend-specific skip; migrated-reference restore, restored-trigger attack, build/smoke and dependency checks passed. Runs 37985711932 / 37985706379. Evidence: docs/guardrails/evidence/tenant-references-20261009.json. No production changes; gate remains blocked.

Read docs/guardrails/TENANT_REFERENCES_20261009.md. Migration machinery now covers all 16 brand-owned tables, preserves old ORM inserts and rejects direct-SQL owner/brand/workspace reassignment. CLI has a separate references phase with read-only planning and controlled apply. Not activated on production or wired into application read isolation yet.

Next: integrate fresh-schema/reference migrations and canonical runtime reads; PostgreSQL restricted roles/RLS; account-level and legacy authority mapping. Do not count these integrity guards as read isolation. Publication goal remains active and the production gate remains intact.

---

# Current increment: active owner membership checks

Validated at 447b357: CI SQLite and PostgreSQL each 370 passed and one expected backend-specific skip. Backup restore including workspace/membership content, build, smoke and dependency checks passed. Runs 37983897804 / 37983892861. Production guardrail remains blocked; no deployment. Evidence: docs/guardrails/evidence/tenant-access-20261009.json.

Read docs/guardrails/TENANT_ACCESS_20261009.md first. The registry is now integrated with transactional signup/brand creation, owner-scoped request permissions, session revocation and Studio/older scheduled worker preflight. New account memberships are created explicitly; missing/revoked memberships never self-repair. Existing databases require an offline registry migration before startup. This has NOT been performed on production.

Still next: workspace references on every customer record, legacy authority mapping, complete shared-team routing/capabilities, and restricted PostgreSQL identities/RLS. The release goal stays active. No staging charges, forced customer MFA or gate bypass authorised.

---

# Active release goal — 9 October 2026

Owner asked to iterate until publication. Goal remains active; do not stop merely because the production check is red. Work through compatible changes and verified evidence; never weaken the gate or claim independent review. No production change has been made.

Latest validation at 6a31f1a: local and CI SQLite/PostgreSQL each 355 passed, one expected backend-specific skip; restore/build/smoke/dependency checks passed. CI runs 37982302845 and 37982293248. Production gate remains blocked. Evidence: docs/guardrails/evidence/tenant-registry-20261009.json.

Current increment: canonical workspace registry migration and six-role policy foundation. Read docs/guardrails/TENANT_REGISTRY_20261009.md. It is deliberately not yet used as an authorization boundary. Next: workspace references, transactional identity lifecycle, route/worker capability enforcement, restricted PostgreSQL roles/RLS. No paid staging or mandatory customer MFA authorised.

---

# Current guardrails integration — 9 October 2026

Worktree: zova-guardrails; branch codex/guardrails-closure-20261009. Candidate only, not deployed. Combines guardrails PR #16 and UX PR #17 with owner-authorised optional MFA. Read docs/guardrails/OPTIONAL_MFA_20261009.md and assessment.json first. Earlier deployment statements below are historical.

Validation: local SQLite 338 passed / 1 PostgreSQL-only skip. CI SQLite and PostgreSQL each 338 passed / 1 expected backend-specific skip; synthetic restore (including MFA tables), dependency audit, image build, smoke test and Studio behaviour checks passed at f331164. CI runs 37920657711 and 37920651549. Production guardrails remain red. PR #18 is a draft integration candidate, not deployed. See docs/guardrails/evidence/optional-mfa-20261009.json. Browser authenticator UX and real-provider acceptance remain unvalidated.

Preserve all users, credentials, data, explicit publishing confirmation and testing billing settings. No paid staging provisioning authorised. Do not force MFA enrollment. Do not roll back to MFA-unaware authentication once enrolled accounts exist. Production guardrail check remains fail-closed; engineering tests do not certify all 79 requirements.

---

# Focused UX release candidate — 8 October 2026

Publication authorised. Read `docs/UX_RELEASE_20261008.md` for exact scope and rollback. This separate release excludes the broader September authentication, recovery, storage and newsletter candidate. Remote release checks and live verification are required before marking it live.

---

# Next move top-right and current-topic search — LOCAL CANDIDATE, 27 September 2026

Current increment is NOT deployed. Branch `codex/next-move-sources` in the existing `zova-strategy` workspace, based on production-equivalent 653528a / 021aad7. Read `docs/NEXT_MOVE_SOURCES_20260927.md` for details, evidence, limitations and rollback. Sources under the mirrored project remain read-only.

Implemented: top-right branded Next move; compact expandable source cards; bounded web/public-social search using public content themes; cited URLs and 14-day reported-date checks; strategy-ranked recommendations; 24-hour source expiry; explicit evergreen fallback and existing draft/approval continuity. No schema changes. Full suite 224 passed; final focused suite 43 passed including 2 additional tests. Desktop and 390/320px mobile, keyboard and generated-draft reload reviewed locally. Provider/model acceptance remains unvalidated: no local OpenAI key. No live posts, grants, charges, settings or production changes. Fresh CI/PostgreSQL and a synthetic provider search are release gates.

Rollback this increment to production-equivalent 653528a / 021aad7, retaining all data. Prior live strategy release details below remain valid; this increment does not supersede production until separately published.

---

# Strategy and Next move LIVE — 27 September 2026

User explicitly approved repository upload and deployment. PR #13 merged as 021aad77292abc95c499191789bc50c5cda69436, identical tree to validated 653528a02a53b1575509bcc05c3f8adafaaac7a3. Both candidate CI runs 36347400542 and 36347397624 passed (SQLite/PostgreSQL, synthetic restore, dependency audit and hosting image checks). PostgreSQL validation found a pre-existing concurrent-first-request limiter race; corrected without changing limits, with 22 focused local tests passing.

Render deployment dep-dasnmcc9v7es73f7jvrg confirmed Deploy succeeded / Live; service-live log at 21:24:02 BST. Fresh managed PostgreSQL export available at 21:18 BST; three-day point-in-time recovery available. Production backup was not downloaded/restored. Public health and homepage return 200; all four changed Studio JS/CSS assets match tested files. Existing signed-in browser session and saved draft 9 remained visible; Next move opens without error and purple sparkle renders in both heading and composer. Opening panel initialized an empty strategy row for the existing session; no preferences confirmed, AI calls, posts, grants or charges. No credentials/settings changed.

Release evidence: docs/validation/strategy-release-20260927.json and strategy-live-20260927.png in the local zova-strategy checkout. Provider/real-model quality and verified live trends remain unproven; rollout does not close these gaps. Rollback: retain additive tables; cancel pending series jobs before code rollback to b746bad, preserve unknown/completed outcomes and all user/media/auth/social records. Earlier candidate-only statements below are historical.

---

# Zova continuation — local strategy candidate, 27 September 2026

This candidate is NOT deployed. Current production base: b746bada82965baa8f3bf55bf04a921683134b35. Branch: codex/strategy-next-move. Workspace: C:/Users/david/.codex/.chatgpt-projects/g-p-6a8a0aa881c88191a2835a8d53316369/zova-strategy.

Read docs/STRATEGY_NEXT_MOVE_20260927.md first for the iteration log, scores, limitations and rollback, and docs/ZOVA_FEATURE_MATRIX.md for current feature status. Earlier live history remains in the original root handoff under Documents/Codex/2026-08-29/referenced-chatgpt-conversation-this-is-an.

Implemented: confirmed brand strategy separate from proposals; up to three compact Next moves; generated idempotent linked drafts; feedback; finite recurring plans; exact repeat batch approvals; fresh drafts separately reviewed; pause/cancel/time edits; privacy lifecycle and usage integration. Existing users/data/auth/media/social connections and explicit publishing approval preserved. Testing billing flags unchanged.

Validation: 203 automated tests passed (17 existing warnings), JavaScript syntax/whitespace checks passed. Local synthetic browser journey and 390x844 responsive check, no horizontal overflow; Escape returns focus to Next move. Mocked AI/providers, no live posts. Final targeted subscription-guard regression: 21 passed (2 existing warnings).

Before release: run staging PostgreSQL concurrency and worker recovery; real-model usefulness evaluations; approved provider scheduling/Story validation. Live trends are unavailable with explicit evergreen fallback. Batch TikTok settings use individual Studio review. Future content changes require an edited new series; one/future time changes are supported. Do not claim whole-product 8/10 or deploy without authorization.

Rollback: cancel pending series deliveries before returning code to b746bad; do not automatically cancel sending/unknown outcomes. Keep additive tables and completed history. Restore-test a database backup before any release.

Local git origin points to the original local checkout, not GitHub. Do not push to it. No PR or deployment created in this task.
