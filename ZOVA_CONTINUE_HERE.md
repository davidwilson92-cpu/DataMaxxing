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
