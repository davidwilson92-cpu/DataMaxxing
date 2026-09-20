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
