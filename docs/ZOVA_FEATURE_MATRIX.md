# 18 October 2026 — sent-media and TikTok outcome candidate (not deployed)

| Capability | Implementation / evidence | Remaining boundary |
|---|---|---|
| Sent image/video message | Playable attachment moves into conversation; survives reload; removal changes active post only; ownership/brand/forged URL/failure tests and desktop/mobile preview | Synthetic UI/provider tests; deployed sandbox remains previous2fa13f7 |
| First-caption creation | “Post this shlop” with video/TikTok becomes an editable caption proposal; no review or publication is implied; API and client regressions | Live dead-end reproduced on draft2; new behavior not deployed |
| TikTok result accuracy | Safe rejection reasons, durable receipts, status/worker race protection and no automatic resend | Existing publication-1 error evidence lost in old version; must remain unknown |
| Commercial disclosure | Own brand vs third-party partnership retained; sandbox private-only limit shown and enforced; paid visibility Everyone/Friends only | TikTok public-access audit still required; no live paid partnership validation |

Runtime1bd3b9486ea79c82413978c07e7d82a4c26ef52c passed hosted CI39161889443:440 passed/1 skipped on each database, restore/container/dependency/frontend and exact beta gates. Providers mocked; attachment desktop/mobile visually checked; live first-caption dead-end observed, new first-caption path API/client tested. No deployment or real post. See current handoff for evidence and rollback. All79 wider beta findings remain open.

---

# Social beta validation - 16 October 2026

| Capability | Implementation and tests | Live provider / deployment evidence |
|---|---|---|
| Instagram Post / Story | Existing routes/scopes preserved; regressions pass | Owner-confirmed working; Instagram routes and scopes preserved through PR32 |
| Facebook Page text / image | Actual-grant checks, posting scope, reviewed snapshots and receipts tested with mocked provider | Page use case and all three permission review requests saved, not submitted/approved; narrowed Page grant and connection verified; approved text test published once and independently verified on Facebook (122119807485439972). General customer permissions review still pending; live images not tested |
| X text / thread / image | Media scope and immutable review/adapter tests; partial thread prevents resend | Callback corrected, account connected; authorised text test independently verified on X (2111033940157055189). Live images/threads not tested |
| TikTok video to inbox | Approved scopes, review, chunk upload, inbox/published status and duplicate prevention tested | Approved inbox-only Web app; connected David Wilson; corrected live inbox final review verified after PR32. Synthetic draft27 sent once after exact approval; owner confirmed inbox receipt. Public completion remains in TikTok; pending label needs refinement |
| TikTok Direct Post | PR33 deployed dormant; consent, disclosures, verified media URL and actual duration checks;315 tests pass on both databases | Approval draft prepared; separate audit unsubmitted; real Direct Post recording, grant and feed test outstanding. Inbox mode retained |
| TikTok analytics | Outside current integration scope | Not validated |
| Shared iOS | Shared API foundation remains draft PR28, flags off | Native registration/device/provider tests and deployment outstanding |

Candidate d844afa passed CI38882996566: SQLite299 passed/1 skipped; PostgreSQL299 passed/1 skipped, restore/container/dependency and exact beta scope checks pass. Owner-approved X and TikTok connections saved; exact approved X text test published once. PR30/31/32 required checks passed and deployment verified; Facebook approved text test independently verified and TikTok inbox delivery owner-confirmed; no TikTok Direct Post sent. See [social evidence and rollback](SOCIAL_BETA_COMPLETION_20261016.md). All79 broader gaps retained; no commercial certification.

---

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

Next move simplification: automatically fills empty/stale recommendations; post-first card with one draft action; compact alternatives/context/settings; linked draft title and explicit platform saved. Browser synthetic goal-to-draft/reload and failure/late-navigation harnesses validated. Live model relevance remains a separate check. See NEXT_MOVE_SIMPLE_20261010.md.

## 18 October 2026 — focused draft recovery (deployed to TikTok sandbox only)

Exact runtime 2fa13f72009fa4629129070c14b8e15fa9f73631 is Live on Render dep-dbai30rrjlhs73akkom0. CI39146945668 passed all release gates (359 passed / 1 skipped each on SQLite/PostgreSQL); public health/login and exact deployed assets verified. Browser needs fresh sign-in; live account/provider path was not repeated. Production unchanged. See the current handoff for rollback and ephemeral sandbox restrictions.

| Capability | Implementation/evidence | Remaining boundary |
|---|---|---|
| Sent-message composer | Sent idea moves to conversation; empty composer persists; separate recoverable retry | Synthetic desktop/mobile/reload/keyboard/fork tests passed; exact sandbox assets verified; signed-in live retest pending |
| TikTok sponsor captions | Selection-bound planning; first caption generated instead of missing X rewrite | Mocked model coverage; no real paid post |
| TikTok disclosure | Own/paid flags, labels, consent reset, privacy restrictions and immutable review tested | Sandbox private-only; public-access audit needed for paid partnership delivery |

Existing users/data/auth/social integrations and all 79 broader beta findings remain preserved.
