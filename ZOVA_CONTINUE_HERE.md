# Next move live-model follow-up — 10 October 2026

PR19 is live as ebb6f48. The compact UI and synthetic journey passed, but live recommendations failed strict validation. Current follow-up supplies the exact schema/platform constraints and one bounded repair; awaiting full CI and live verification. Read docs/NEXT_MOVE_SIMPLE_20261010.md. Broader beta gaps remain open.

---

# Next move simplification candidate — 10 October 2026

Read docs/NEXT_MOVE_SIMPLE_20261010.md. Current update responds to the owner-reported empty/cluttered Next move journey. Implements automatic missing/stale recommendations, one featured post, compact disclosures, explicit draft platform/title, save failure and late-navigation protection. Local synthetic browser end-to-end setup/draft/reload and two design review passes completed. Broader security gaps remain required follow-up in docs/beta/KNOWN_GAPS.md. Await CI and live verification before calling this update published.

---

# Beta is live — 10 October 2026

Verified Render deployment dep-db52dg3rjlhs73abnrr0, commit 4c0b0419beb6944bd8e0db3189432d259e9efded, live at 11:52:45 UTC. PR 17 merged after all three required checks passed. CI 38049756412: SQLite 265 passed / one skip; PostgreSQL 265 passed / one skip; restore/image/dependency and exact-scope beta gate passed. Health/login/signup returned 200; live Studio asset matched candidate and browser retained existing session/draft21. Transient 502 during startup recovered. No real post/charge/provider grant or secret change was used for validation.

Known gaps and next-update requirements: docs/beta/KNOWN_GAPS.md and docs/beta/deferred-register.json. Commercial readiness remains unapproved. Broader PR18 security migration is deferred and must not be deployed wholesale. When the owner next requests updates, address/reconcile the saved defects and security gaps first. Local screenshot contains the owner's draft: do not commit or share it publicly. Sanitised release evidence: docs/validation/beta-live-20261010.json.

---

# Limited beta authorisation — 10 October 2026

Owner requested publication as a beta for personal testing and deferral of the remaining commercial work. This supersedes the all-sections-complete requirement for this focused beta only. Read docs/beta/KNOWN_GAPS.md and docs/beta/deferred-register.json on every future update and address the recorded issues before unrelated expansion.

Use focused UX PR 17; do not publish the broad unfinished security/service migration in PR 18. The beta excludes later optional MFA and account/usage hardening, which remain next-update priorities. Required application/PostgreSQL/migration/restore/image and scoped beta checks must pass. Deployment has not yet been confirmed; append actual revision and evidence after verification. Existing billing test settings, data, sessions and publishing approvals must remain intact.

---

# Publication blocked by enforced production gate — 8 October 2026

User authorised publication. A focused release was prepared in the sibling `zova-ux-release` worktree, branch `codex/ux-release-20261008`, PR #17 (https://github.com/davidwilson92-cpu/DataMaxxing/pull/17), candidate `1398c7ececae2de5ab9370e7c43fa9021ba4c11d`. It is NOT merged or deployed. Production remains `38f1c265`.

Both push and PR CI passed synthetic-tests and postgres-release. Final suites: 261 passed / one expected skip on SQLite; 261 passed / one expected skip on PostgreSQL (SQLite-only backup test). PostgreSQL old-schema title migration DID pass, as did dump/restore, Docker smoke and all three frontend harnesses. Dependency audit is clean after oauthlib 4.0.0 and direct OAuth1 signing for the legacy X text path. No real post was sent. Render export was created 8 October 2026 20:35 UTC; three-day point-in-time recovery is available. Backup stayed in Render.

GitHub refused merge because active ruleset `Zova production guardrails` (24140009) requires `Production guardrails`, synthetic-tests and postgres-release. No bypass actors. The missing gate exists in separate unmerged PR #16 and intentionally blocks until its open requirements/evidence are resolved. Do not remove the rule, fabricate a green check, force-merge or manually deploy around it. The prior broader candidate is still local and must not be deployed wholesale. No infrastructure or billing changes were made.

Release manifest: `../zova-ux-release/docs/UX_RELEASE_20261008.md`; remote evidence: Actions run 37841005196; local downloaded artifacts: `../zova-ux-release/docs/validation/ux-release-ci-final/`. Next step is reconcile the focused UX release with the enforced guardrail release process and resolve its required evidence. The owner MFA and paid-staging deferrals in PR #16 remain relevant; they are not release waivers.

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
