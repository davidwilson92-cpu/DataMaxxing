# Zova audit follow-up — 14 September 2026

**Local candidate readiness: 6/10 overall. Production remains unchanged.** This improves the core trust failures, but does not justify declaring all areas 8/10. Scores use the original rubric: 1–2 broken/substantially absent; 3–4 material gaps; 5–6 usable but incomplete; 7–8 strong; 9–10 exceptional and demonstrated. Overall is a judgement, not an average or certification.

## Baseline and preservation

Read the authoritative workspace `ZOVA_CONTINUE_HERE.md` and 13 September audit before editing. Refreshed/inspected main and both existing worktrees. Baseline account diagnostics reproduced the detached-user password/profile/billing writes and non-revocable logout; regression tests failed against those defects before the fixes. Source inspection and the existing/live Studio comparison reproduced omitted workspace fields, stale card/global-state risks, missing mobile controls, mutable publication review, mixed analytics periods and unverifiable deletion status. No production exploit, destructive mutation or new provider test was performed.

Work continues in `work/zova-studio-ux`, branch `codex/studio-attachment-ux`, based on `493fe375a2bb922e2910af47b67f23d014281d25`. Reused the compatible conversational planner concept from the larger development tree after inspection; did not copy or deploy that tree wholesale. Production users, PostgreSQL, uploads, authentication secrets, social encryption keys and grants are untouched. Both Instagram login routes remain. The reviewer account and recorded review instructions were not changed. Subscription enforcement remains disabled; testing checkout is explicitly blocked.

## What changed, in implementation order

1. Fixed password, profile and billing persistence. Added legacy-compatible session versioning/revocation and single-use recovery. Hardened image/video parsing, upload/request limits, quota locking, origin checks, shared rate limits and response headers. Unlink clears encrypted credentials; deletion status now requires a durable verified record with an explicit, limited scope.
2. Persisted conversation, unsent composer, variants, selected platform, attachments and source link. Added optimistic revisions, truthful save/conflict/error status, save-before-new-chat, input restoration and guards against stale cards/late responses. Completed attachment preview/removal, including owner-checked fallback previews for private object storage.
3. Added contextual intent planning, explicit negation safeguards and deterministic creation handling. Preserved rewriting/voice scanning, exposed editable voice preferences/date and disclosed that generation has not inspected media or fetched source pages.
4. Added immutable server review snapshots and a durable per-platform delivery ledger. Review includes exact account, final text/link, media and TikTok controls. Confirmation and worker claims are atomic; partial results, pending/unknown outcomes, failed-only retry, cancellation/rescheduling and timezone/DST handling are explicit. Unsupported multi-image routes fail clearly rather than silently dropping attachments. Optional time suggestions remain and are labelled as unproven starting points.
5. Restored mobile navigation, Account, source input and X format. Added keyboard focus/labels/tab controls, a real upload button, larger controls, country names, retained signup inputs, first-run help, draft search and schedule management. Kept the purple identity and reduced oversized account decoration.
6. Replaced mixed-window/maxima analytics with dated recent-post samples, visible freshness/methodology and missing values. Added capability preflight checks, a clear testing offer, authenticated operational signals, CI/dependency checks and local migration/restore evidence. Added a rollback plan that preserves session revocations and publication records.

## Scores against the original audit

These are scores for the **tested local candidate**, conditional on the limits below. They are not revised production scores.

| Area | Original | Candidate | Why the score stops here |
|---|---:|---:|---|
| Brand and positioning | 7 | 7 | Identity retained; broader marketing claims and real product examples still need editorial work |
| Visual design | 7 | 7 | More useful spacing/type; no comprehensive design-system or contrast audit |
| General UX and navigation | 5 | 7 | Mobile menu/help/search and recovery states work; long Account page remains |
| Customer journey and activation | 5 | 7 | Country selector, retained inputs and first-run guidance; recovery delivery still external |
| Studio composition and review | 4 | 7 | Full saved state and immutable review demonstrated; physical-device and real-model journeys remain unverified |
| Mobile experience | 3 | 7 | Essential controls reachable at tested widths; physical keyboard, zoom and landscape not certified |
| Accessibility | 4 | 6 | Labels/focus/keyboard improved; screen-reader and full WCAG audit outstanding |
| AI usefulness and voice | 5 | 6 | Better intent and honest grounding; no actual vision/link ingestion or broad quality evaluation |
| Publishing and scheduling | 4 | 7 | Durable approvals/results/recovery tested with mocks; real provider and PostgreSQL concurrency gates remain |
| Social integrations | 5 | 5 | Existing integrations preserved and limitations enforced; grants/approvals not newly validated |
| Security and account integrity | 3 | 7 | Critical persistence/revocation defects fixed, request/upload controls and clean package scan; no penetration/load test |
| Privacy and data lifecycle | 4 | 6 | Credential removal and recorded scoped status; full assisted erasure/retention evidence incomplete |
| Analytics accuracy | 4 | 6 | Window and missingness now honest; sampled lifetime counters are not complete historical analytics |
| Feature completeness | 5 | 7 | Core draft/delivery/account management gaps narrowed; feature matrix records remaining limits |
| Reliability and maintainability | 4 | 6 | Stronger tests, atomic claims, local restore and monitoring endpoint; production restore/alerts unverified |
| Commercial readiness and support | 3 | 4 | Testing offer/help clear; paid proposition, support operations and billing readiness not established |

## Evidence

- **Final run: 72 passed, 17 deprecation warnings, 45.01 seconds.** No failing tests.
- Automated results: `validation/tests.txt` and `validation/tests.xml`. Suite uses newly created disposable SQLite/uploads and synthetic users. Provider HTTP is blocked by default and explicitly mocked where needed. `pytest.ini` selects the maintained application suite; the obsolete `nova/test_app.py` targets a superseded standalone API. A new regression verifies the actual retained Custom GPT X endpoints, authentication and explicit approval.
- Critical tests cover independent-session password/profile/billing persistence; copied-session logout rejection and legacy continuity; reset expiry/reuse; hostile MIME/decoded media/safe serving; streamed request limits; workspace ownership/revisions; negation/creation; exact account/final content; concurrent confirms and workers; failed-only retry; cancelled/rescheduled jobs; unknown worker recovery; DST; additive migrations; and synthetic database restore/decryption and upload hash verification.
- Dependency scan: `validation/dependency-audit.json`. The initial installed environment reported 49 advisories across cryptography, multipart, Starlette and pip. Upgraded the vulnerable packages, including the compatible FastAPI/Starlette pair, and updated template call signatures. Final scan and dependency compatibility checks are recorded separately from application tests. This is not a guarantee that no vulnerabilities exist.
- Browser: local application on `127.0.0.1:8772`, temporary data, synthetic account, mocked AI/publication, external HTTP blocked. Verified generated content; source/unsent text/conversation reload; attachment preview/reload/removal; rejected upload retaining prior media; generation failure retaining input; two-tab conflict retaining the losing edit; exact-account confirmation and mocked per-platform result; keyboard focus from source to X format. Inspected 390×844 and 320×740 layouts; 768×1024 and 1280×900 checks found no document-width overflow and composer bottom within viewport. This does not emulate an actual phone keyboard or establish accessibility conformance.
- JavaScript syntax checks passed for the changed scripts. A CI workflow is prepared, **not run remotely**.

## Status separation and remaining work

**Implementation:** local candidate changes and reviewable diff delivered. **Automated tests:** local synthetic/mocked evidence above. **Provider validation:** none newly performed; the handoff's existing direct Instagram demonstration is historical evidence only. **Deployment:** none; no push, production migration, real post, new grant, review submission or charge.

External gates: PostgreSQL staging/restore and concurrency; hosting-image dependency compatibility; secure SMTP and verified delivery; actual platform permission/approval states and synthetic staging provider checks; physical-device and screen-reader assessment; approved monitoring/alert destinations. Engineering limits remain explicitly recorded in `OPERATIONS_AND_ROLLBACK.md`, including CSP inline compatibility, recovery timing, decoder isolation, upload lifecycle, sampled analytics and uncertain provider reconciliation.

The appropriate next step is a separately authorised staging validation, followed by focused fixes based on its evidence. Do not award an 8 for an unverified control, and do not deploy the broader development tree.
