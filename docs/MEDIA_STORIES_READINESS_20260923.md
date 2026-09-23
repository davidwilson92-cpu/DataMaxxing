# Zova: media, Stories and readiness — 23 September 2026

## Status
Tested local candidate on `codex/media-stories-readiness`, based on the tree deployed as 012b7d7 (local equivalent 7926741). Not deployed. No real posts, billing activation, grants, customer data changes or Meta submission changes. Existing users, PostgreSQL, uploads, passwords, session/encryption keys and both Instagram login routes must remain intact. Subscription and allowance enforcement remain disabled.

Three implementation/review cycles were used: media/Stories and tests; customer journey and regression fixes; browser inspection, publishing recovery and final regression. This is a substantially improved beta candidate, not an unsupported 8/10 paid-launch claim.

## Implemented and reproduced
| Finding | Change | Evidence and limit |
|---|---|---|
| Attachments never inspected | Owned images become resized JPEG inputs to OpenAI Responses. Videos are decoded locally into up to eight timestamped frames. Cached observations are scoped to asset/user/brand and invalidated by file digest/model/version. | Real local image/video decoding and mocked API tests; actual recognition accuracy is not yet measured against the real model. |
| Unsupported visual claims | Visible coverage and correctable observations; failed inspection explicitly says unavailable. Audio, unsampled moments, first-frame-only animation and source links are not falsely claimed as inspected. | Browser mocked inspection, error/retry tests, ownership and brand boundaries. A still horse image cannot prove dancing; a video can support action inference only from sampled frames. |
| Privacy of media processing | OpenAI disclosure at attachment/send and in Help/Privacy/Security. Responses use store:false. Observations included in assisted export and erased with media records. | No claim of zero provider retention, legal compliance or automated complete erasure. No access tokens sent in visual inputs. |
| Caption differs from chat proposal | Generate/rewrite actions use one editable generated variant card instead of an independent caption from the planner. Invalid/blank captions and incomplete threads are rejected instead of being padded. | Browser canonical card and review flow; synthetic validation tests. Real-model editorial-quality evaluation remains required. Final media review also fixed transparent-image contrast and deferred cache writes so multiple image calls do not block usage telemetry. |
| Instagram Story missing | Select Post/Story in composer only when Instagram selected. Placement survives reload, review, scheduling and dispatch. Story sends STORIES and media only; planning text/link omitted. | 13 Story regression cases: both login routes, image/video, Business-only gate, tamper rejection, persistence, scheduling, duplicate prevention and allowance. No live Story published. |
| Unknown publishing outcome | Persist validation/container/send/confirmed checkpoints. A failed permalink lookup cannot erase a confirmed post ID. Pre-send failure remains retryable; uncertain send stays blocked. Refresh resolves only an authoritative PUBLISHED container status, never resends. | Mocked checkpoints, timeout and reconciliation tests. Old unknown records without container IDs still need manual reconciliation. |
| Mobile menu clipped | Drawer has its own vertical, scrollable navigation; no nested collapsed mobile menu. Links, legal links, sign-out and Close are reachable. | Browser iteration caught and fixed remaining flex clipping. Escape returned focus to opener. |
| Composer crowds exchange | Compact attachments, short inspection/format hints; format and toolbar placement corrected. | Measured with attached Story at actual CSS 1280x720: chat 406px, composer 250px; 400x845: chat 453px, composer 328px. No horizontal overflow. Browser inherited 60% zoom; actual CSS dimensions were measured, not assumed. |
| Generic empty state and premature Saved | “What do you want to share?”; blank workspace says Ready, persisted work Saved. | Browser empty/drafted/reloaded states. |
| Switching brands interrupts work | Header opens explicit brand choices; switch saves first and blocks on save failure or active AI/upload. | Existing brand ownership tests; browser dialog and current-workspace label. Full two-brand browser switching remains a follow-up. |
| Optional onboarding competes with value | Create first draft is primary; writing-style setup secondary. Email address label and show-password control improve sign-in clarity. | Template/client regression checks; signup obligations/password requirements preserved. |
| Tall, duplicated settings | Smaller Account sections; explicit labels/password autocomplete; brand voice/connections named; remove duplicate guidance field. Name changes preserve voice guidance; explicit legacy guidance clearing still works. | Regression found then fixed empty-form handling. Mobile profile is 412px high; no horizontal overflow. |
| Hidden older drafts | Thirty-item paginated Drafts page and all-record search; compact cards. | 32-record pagination test. Sidebar remains recent work, with search/all-drafts link. Filters currently apply to the displayed page. |
| Dense empty analytics | One connect-account next step; hide empty metric/recommendation panels. Retrieval time distinguished from provider counter freshness. | Client changes reviewed; historical-series and provider data completeness not invented. |
| Contradictory billing copy | One testing-access state; future GBP plans collapsed; no nonexistent cancellation control for non-subscribers. | Browser and route regression. Existing prices/trials/customer subscriptions unchanged. |
| Operational visibility | AI failure count added to authenticated status/probe; dedicated shared AI request-rate bucket. | Synthetic suite. No external alert destination or responder installed. |

## Validation
- Local full suite before final two media regressions: 180 passed, 17 existing dependency/test-client deprecation warnings. Final targeted media suite: 19 passed. Final code e5babb8 CI: SQLite 182 passed; PostgreSQL 181 passed, one SQLite-only restore test skipped; PostgreSQL backup/restore, dependency checks and hosting image smoke all passed. Run: https://github.com/davidwilson92-cpu/DataMaxxing/actions/runs/35835048025 . Tests use disposable data and block unmocked external HTTP.
- All JavaScript syntax checks passed; diff whitespace checks passed.
- Fresh dependency audit: 49 resolved dependencies, zero known advisories in this audit. This is not a penetration test or proof against unknown vulnerabilities.
- Additive migration runs twice against an old synthetic schema and preserves records. Existing local SQLite/upload/hash/credential restore test passes. Final synthetic PostgreSQL restore and hosting-image checks passed in CI; these do not validate a managed production restore.
- Browser: synthetic localhost account; drafting, image upload, visual-analysis message, Story selection, exact Story approval, reload retention, account/billing, mobile drawer and Escape/focus behavior. No Confirm publish clicked in browser; dispatch uses mocks in tests. No browser console errors observed.
- Not claimed: real OpenAI horse/video recognition, live Instagram Story acceptance, actual-device keyboard/200% zoom/screen-reader coverage, live recovery delivery, managed production restore, independent security review or customer study.

## Re-score using original rubric
1–2 unusable; 3–4 major blockers; 5–6 usable beta with material friction; 7–8 reliable/coherent with bounded verified gaps; 9–10 independently validated exceptional experience. These scores describe the candidate; production is unchanged.

| Area | Before | Candidate | Remaining reason below exceptional |
|---|---:|---:|---|
| Commercial readiness | 4 | 5 | Recovery/provider/operations/customer gates remain |
| Privacy transparency and operations | 4 | 6 | Precise legal bases, retention/transfers and deletion operations require verification |
| Security readiness | 6 | 7 | Ownership/regression/advisory evidence; independent assessment and operational assurance absent |
| Overall customer UX | 5 | 7 | Clearer core; real customer tasks not observed |
| Simplicity | 5 | 7 | Less duplicated setup/state; surrounding navigation still differs |
| Journey consistency | 4 | 6 | Brands/Billing still use public header; some Account anchors remain |
| Visual impact and brand | 7 | 7 | Z identity retained; no independent brand/user validation |
| Visual clarity | 5 | 7 | Proportions and drawer verified; broader device/zoom coverage pending |
| Studio usefulness/output trust | 4 | 7 | Grounding/canonical text implemented; real-model recognition and editorial evaluation pending |
| Publishing/scheduling reliability | 4 | 6 | Durable evidence and mock coverage; live Story and interrupted-provider acceptance pending |
| Mobile/accessibility | 4 | 6 | Drawer/focus/proportions improved; actual keyboard/screen-reader coverage incomplete |
| Analytics decision value | 5 | 6 | Better empty/freshness handling; data coverage still provider-limited |
| Support/recovery/operations | 3 | 4 | Recovery delivery, responder and production restore not proven |
| Billing/offer clarity | 5 | 8 | Coherent tested testing state; this does not score paid billing readiness |
| Customer validation/economics | 3 | 3 | No fabricated participants, retention or margins |

Do not continue changing scores merely to reach 8. The next cycle must use missing evidence: synthetic real-model media set (horse/still/motion/ambiguous logo/text injection), staging Story image/video on an eligible account under explicit posting approval, PostgreSQL CI/restore, recovery email delivery, actual devices and consenting target creators. Account navigation unification, visible source-inspection limitations, full voice provenance, draft filter pagination and automated pending-provider polling remain product follow-ups.

## Rollback and release gates
1. Before any authorised release: verified database/upload backup and secret recovery; stop parallel migration starts; run the additive migration once. New column: nova_media_assets.analysis_json, default empty JSON. Retain it on rollback.
2. Deploy frontend/backend together only after explicit approval and staging/provider checks. Preserve all application configuration, media, grants and billing flags. Do not change the active Meta submission.
3. Roll back application code to deployed 012b7d7 (equivalent local 7926741), retaining database, uploads and all secrets. Never restore an old database over new user work or clear publication ledgers to retry. Stop Story scheduling before rolling back: the previous worker does not understand Story placement. Leave those jobs held for reconciliation; do not silently execute them as feed posts.
4. Cache inspection is additive; previous code ignores it. A Story review/session must be freshly reviewed after any forward release; never reinterpret a prior immutable approval.
5. Logs and evidence must contain synthetic data or counts, not customer captions/tokens. A provider/model failure remains an error with retained user input, not a success badge.

References: OpenAI image inputs https://developers.openai.com/api/docs/guides/images-vision ; Meta's official Instagram API collection https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api (Stories Business-account restriction). Limits and provider acceptance are distinct from mock tests.
