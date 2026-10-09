# 9 October workspace protection candidate

| Capability | Implementation | Validation / deployment |
|---|---|---|
| Workspace membership | Atomic account/brand provisioning, current owner capability checks and revocation | SQLite/PostgreSQL regression evidence in tenant-access-20261009.json; not deployed |
| Canonical content references | Offline backfill and immutable write guards across all 16 brand-owned tables | SQLite/PostgreSQL migration, direct SQL attack and restore evidence in tenant-references-20261009.json; not runtime read isolation |
| Migration contention safety | Bounded PostgreSQL waits and truthful reference preview | SQLite 393 passed / 6 skipped; PostgreSQL 398 passed / 1 skipped at 09c5771; not deployed |
| Runtime canonical binding | All 16 brand-owned models, scoped content queries, fresh-install guards and populated-database migration checks | SQLite 398 passed / 6 skipped; PostgreSQL 403 passed / 1 skipped at dc55d2b; not deployed |
| Restricted runtime startup | PostgreSQL verifies schema without DDL and rejects privileged/destructive credentials; explicit offline preparation | Real restricted-login application/attack tests; CI 405 SQLite / 411 PostgreSQL passed; not deployed |
| Build image consistency | Pinned official Python/PostgreSQL manifests; byte-identical official mirror used in CI | Build/smoke passed after Docker Hub quota failures; OS image scan still outstanding |
| Database workspace policies | Forced/restrictive RLS and expiring transaction-bound server contexts for all 16 brand-owned tables | Direct SQL, revocation, replay and restored-policy tests passed; isolated migration only |
| Protected content transactions | Frozen authority across transactions; default/second-brand draft save/reload and reference cleanup | 434 PostgreSQL tests passed; opt-in, auth/account/worker routing incomplete; not deployed |
| Separated web service identities | Normal draft/session/rate-limit flows use restricted identity, content and issuer pools; unmapped routes fail closed | CI 439 PostgreSQL tests passed; staged mode, not production-enabled |
| Restricted authentication pool | Password sign-in, optional MFA and logout through a fourth role with limited User column updates | CI 442 PostgreSQL tests passed, including concurrent recovery; account RLS/lifecycle and production rollout open |
| Restricted password recovery | Version-safe password changes; explicit recovery/mail pool, single-use reset and truthful failed-attempt records | CI 446 PostgreSQL tests passed with mocked SMTP; account RLS, real delivery and production rollout remain open |
| Database context integrity | Read-only startup verifies actual function bodies, security properties, defaults and runtime audience against installation source | CI 455 PostgreSQL tests passed including altered-definition attacks; table-policy verification and production activation remain open |
| Database policy integrity | All 16 forced policy sets, exact roles/operations/capabilities and full expressions verified at startup and after restore | CI 464 PostgreSQL tests passed; service routing/final grants and production activation remain open |
| Draft service least privilege | Exact table/column grants; no social credentials, approval text, media locations or delivery mutations; issuer has no direct table grants; sequence rights checked | CI 472 PostgreSQL tests passed including attachment/Story/planning cleanup; telemetry and other service integration still open |
| Database read isolation rollout | Web/auth/worker context integration, final grants and account/legacy mapping unfinished | Release blocker; no production activation |

Earlier entries below are historical, not evidence of current deployment.

---

## 9 October candidate update

| Capability | Implementation | Validation / deployment |
|---|---|---|
| Optional authenticator MFA | Setup, confirmation, recovery codes, password/Apple challenges and session revocation | Synthetic regression suite; candidate only |
| MFA account lifecycle | Secret-free export, assisted erasure, readiness and restore checks | No real users enrolled; operational recovery review outstanding |
| Production assurance | Full 79-section register retained | Unresolved; no production deployment |

# Focused UX release — 8 October 2026

See [release scope and evidence](UX_RELEASE_20261008.md). Implemented: Studio scope/state/recovery UX; editable titles and status summary; goal-first strategy; bounded Performance context; weekly scheduling and reschedule race fix; compact signup and truthful beta offer. Local focused and frontend checks passed; remote CI/provider/deployment status remains separate. Earlier unreleased security/recovery/newsletter work is excluded.

---

# Current local increment — 27 September 2026

The previous strategy release is live at 021aad7. The top-right Next move/source-discovery increment is NOT deployed. See [current evidence and release gates](NEXT_MOVE_SOURCES_20260927.md).

| Capability | Implementation | Validation / remaining gate |
|---|---|---|
| Next move placement | Top-right purple sparkle pill; composer simplified; compact source details | Desktop + 390/320px mobile and keyboard checked locally |
| Current topics | Forced web and public-social search; cited links, reported dates, 14-day window, 24-hour check expiry | Mocked provider contract/outage/provenance tests; actual provider search not validated |
| Strategy fit | Confirmed goal/audience/resources/exclusions + recent drafts/feedback rank evidence; explicit evergreen fallback | Context/source/draft tests; real-model relevance evaluation pending |
| Safety and continuity | Existing brand ownership, review approval, draft idempotency; source metadata in existing JSON | 224 full tests + final 43 focused; no migration or production changes |

The sections below describe historical candidates and do not establish the release status of this increment.

# Local candidate — 27 September 2026

Strategy candidate is based on deployed `b746bad`; it is not deployed. Historical sections below retain their original dates/status. See [iteration evidence and scores](STRATEGY_NEXT_MOVE_20260927.md).

| Capability | Implementation | Validation / release gate |
|---|---|---|
| Brand strategy | Editable confirmed strategy, separate AI assumptions, TXT/Markdown import | Ownership/revision tests and local browser; real AI quality pending |
| Next move | Up to 3 actions; generated linked draft; done/snooze/dismiss feedback | Concurrent idempotency/failure tests, browser journey |
| Topics | Evergreen strategy-based ideas, explicit unavailable live trends | No current-topic source configured |
| Recurring drafts | Finite daily/weekly dates, fresh or frozen repeats, timezone preview | DST/cancellation/revision tests; staging PostgreSQL pending |
| Recurring approvals | Exact-content batch repeats; fresh drafts individually approved | Duplicate/tamper/partial results tests; provider acceptance pending |
| Privacy / usage | New data export/erasure and existing allowance controls | Synthetic tests; enforcement remains disabled |
| Studio | Compact Next move, existing chat/format flow preserved | Desktop/mobile local review; no deployment |

# Current candidate update — 23 September 2026

`codex/media-stories-readiness` is not deployed. See [evidence, scores and rollback](MEDIA_STORIES_READINESS_20260923.md). This section supersedes older candidate/media-status statements below; historical validation is not proof for this candidate.

| Capability | Implementation | Validation | Deployment |
|---|---|---|---|
| Image understanding | Actual resized visual input; owned, cached, correctable observations | Decode/ownership/cache/failure mocks; real recognition pending | Candidate only |
| Video understanding | Up to 8 timestamped frames, <=10-minute clips; no audio analysis | Real synthetic video decoder + mock model | Candidate only |
| Instagram Post/Story | Explicit placement; Business eligibility; image/video; immutable review/scheduling | Both OAuth adapters mocked; no real Story acceptance | Candidate only |
| Delivery recovery | Durable phase/container/post IDs; confirmed delivery survives link failure; read-only reconciliation | Synthetic timeout/phase/reconciliation tests | Candidate only |
| Studio/account/mobile | Canonical variant card, compact composer, accessible drawer, saved brand switch, clarified settings | Local browser and synthetic regression | Candidate only |
| Draft library | All-record search and 30-item page navigation | Synthetic 32-record test | Candidate only |
| Billing/analytics | Testing state and empty/freshness clarity | Browser/route/client checks; charges remain disabled | Candidate only |
| Operations/privacy | Media export/erasure field, AI failure probe, rate bucket, explicit disclosures | Synthetic migration/restore and dependency audit | External monitoring/legal/managed restore gates remain |

# Current feature matrix — 21 September 2026

Current production baseline: main `78d9924` (21 September Instagram reauthentication correction). Candidate: `codex/studio-proposal-layout`, not deployed. Instagram Post/Story remains separate PR #7. Billing and subscription enforcement remain off.

| Capability | Candidate implementation | Validation / remaining gate |
|---|---|---|
| Chat Studio | Compact attachment row, header brand switch, bounded composer and contextual first proposals; simple chat, composer platforms, conditional X format, translucent Z, account draft history; no working canvas | Desktop and measured 390px local preview; reload, options and keyboard focus checked |
| Draft persistence | Full workspace, revisions, retained errors, conflict recovery, private owner media | Existing regression suite retained |
| Grounding and voice | Selected-platform editorial feedback, bounded AI recovery, concise proposals; attachment notice, source limitation, editable voice shown in Post options; contextual weekday-led revision prompt where grounded in current text | Local preview; real-model usefulness/voice fidelity study pending |
| Personal onboarding | Named welcome, fresh account workspace/voice, explicit exact-account confirmation after all social callbacks; switch/cancel and one-Page selection | 10 new synthetic tests, desktop/mobile/keyboard browser checks; real provider acceptance pending |
| Account integrity | Password persistence, session revocation and legacy continuity | Existing tests retained |
| Recovery | Single-use hashed links; background delivery with failed/stuck attempt signals; operator branding/support fixed | Replay/ownership/failure tests; live SMTP/DNS/inbox/bounces still external |
| Email verification | User-initiated account-bound expiring links, explicit POST; optional new-checkout gate off | Synthetic wrong-user/replay/expiry/access tests; real delivery pending |
| Brands | Separate voice/drafts/media/connections per brand; tabs and OAuth retain initiating brand | Existing cross-brand/concurrency tests; live baseline includes separate workspaces; provider flows newly require account confirmation |
| Pricing | Basic £9.99/£99, Premium £19.99/£199, seven-day trial; central offer reused across entry/help/account | Template tests and browser billing; live checkout remains disabled |
| Stripe | Checkout/portal, account-bound reconciliation, deduplication, test/live isolation | Prior actual TEST trials, renewal, 3DS, card change and manual reconciliation; durable public webhook monitoring/retries pending |
| Plan changes | Assisted support guidance; data retained | No self-service upgrade/downgrade or grace-period promise; policy/implementation gate |
| Allowances | Atomic account-wide AI/publication/account/brand caps; failure refunds and known-outcome retries | Tests retained; enforcement disabled; legacy Custom GPT excluded |
| X | Text, threads, up to four images | Mocked adapter/review tests; current production access unverified; no video claim |
| Instagram | Post/Story choice saved per draft; Post images go to feed, videos become Reels shared to feed; Story publishes one visual with explicit no-caption guidance; both login routes preserved | 13 focused format/eligibility/approval/schedule tests plus synthetic mobile/keyboard/reload checks; real Story acceptance and provider media restrictions remain unverified; no carousel/overlay editor claim |
| Facebook Pages | Text/link or single image, exact Page | Mocked tests; current `pages_manage_posts` grant/approval unverified |
| TikTok | Existing photo/video inbox/direct-mode paths and reviewed controls | Mocked pending handling; operating mode/approval/provider completion require verification |
| Review/publishing | Immutable exact destinations/content/settings; partial states and failed-only retries | Existing tamper/duplicate/concurrent/ownership tests; no real posts in this task |
| Scheduling | Cancel/reschedule, timezone/DST checks, worker claim/recovery | Synthetic tests; named worker monitoring/production acceptance pending |
| Analytics | Explicit seven-day post cohort/lifetime counters, missing data/freshness; readable question label | Tests and prior live sample; not historical time-series analytics |
| Cost measurement | Token counts, configured GBP estimate/rate snapshot, unknown cost coverage, monthly threshold | Synthetic success/timeout/alert tests; real tariffs/invoices and observed costs not populated |
| Cost scenarios | 12 monthly/annual normal/allowance/retry scenarios incl. support/tax/fees | Arithmetic tested; missing inputs yield null margin, not profit claims |
| Customer measurement | Optional first-party server milestones; explicit useful-draft feedback; mature D7 cohort reporting | Off by default, synthetic/UI tests; no real participants or retention evidence |
| Support/help | Direct links, drafting-first guidance, recovery and subscription escalation | UI/tests; named responder and coverage unconfirmed |
| Operations | Authenticated worker/billing/mail/cost signals plus read-only monitoring probe | Synthetic checks; external monitor/alert destination not installed |
| Export/erasure | Operator-only cross-brand export, dry run, blocked unresolved billing/publishing, local active-store erasure | Disposable data/files tested; remote objects, backups, third-party posts and final retention decisions external |
| Backup/rollback | Existing synthetic PostgreSQL restore and image checks; additive tables retained | Fresh CI recorded in handoff; managed production database/upload/key restore remains required |
| Privacy | Measurement disclosure and assisted workflow documented | Legal bases, exact retention/transfer/provider facts and operator approval remain external; no compliance certification |

See `COMMERCIAL_OPERATIONS_20260920.md`, `CUSTOMER_VALIDATION_20260920.md` and `COMMERCIAL_READINESS_EVIDENCE_20260920.md`. Provider approval is never inferred from code, old credentials, a connected status or a mock.

