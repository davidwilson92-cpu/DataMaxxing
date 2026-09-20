# Readiness implementation and evidence — 20 September 2026

## Outcome and scope

Incremental changes on the existing `codex/stripe-billing` candidate, based on a0528f9. No rebuild, working canvas, production deployment, paid enforcement, real publication, permission change, invitation or customer charge. Existing users/authentication/encrypted social connections, immutable approval and separate brands are preserved. The authoritative root handoff identifies the final commit and CI outcome.

**The all-areas-at-least-5 objective is not yet met.** Candidate commercial/support readiness improves from 4 to 5 through a working coherent journey and escalation links. Unit economics remains 4 until real assumptions/measurements replace missing inputs; customer validation/retention remains 3 until actual study/cohort evidence exists. Building a calculator or instrumentation does not establish these business outcomes.

## Finding → implementation → acceptance → limit

| Original evidence | Change | Acceptance evidence | Remaining limit / deployment |
|---|---|---|---|
| Offer differed across entry/account/help; support absent from Help | Shared central offer, explicit off/test/live copy, direct support links, assisted-plan-change guidance | Template checks across home/signup/help/account/billing/recovery; browser billing prices/status/support inspected | Candidate only; live checkout remains disabled; named support responder and tax review required |
| Recovery unavailable live and missing operator in footer | Shared branded context, background mail send, fail-closed tokens on known failure, delivery status signals | Original recovery/session suite retained; failure invalidation and mail status/privacy tests; recovery preview shows operator/support | Live SMTP/DNS/inbox delivery not configured or claimed; background send is not a durable queue |
| Email/password signup does not prove ownership | User-initiated hashed, expiring verification; same-account explicit confirmation; optional checkout gate | Wrong user, replay, expiry and existing-session/access tests; gate rejects before contacting provider | Flag remains off; existing users not locked out; delivery external; complete trial-abuse protection not claimed |
| Action allowances were not a cost ledger | Provider token counts, model/outcome, dated rate snapshot and nullable GBP estimate; threshold and coverage signal | Mocked response/timeout arithmetic and allowance-refund separation; unknown cost stays unknown; monitor attention tested | No real cost inputs loaded; estimates are not invoices; low score retained |
| No reproducible margin analysis | Offline 12-scenario calculator for both plans/intervals, normal/ceiling/retries incl. fees/tax/support | Calculation tests; empty real input file produces null margins for all 12 scenarios | Populate dated sources and measured distributions before profitability claims |
| No actual activation/retention evidence | Optional privacy-conscious milestones, explicit useful-draft feedback, deduplication, cohort report, study materials | Synthetic ownership/cross-brand/deduplication/D7 maturity checks; client cannot claim publication; browser feedback persisted | Collection off by default; zero real participants; retention still 3 |
| Generic Studio guidance and hidden voice/grounding limits | Saved voice disclosure in Post options; attachment-time notice; weekday-led revision prompt grounded in current draft | Local saved draft reload/options/feedback verified; contextual prompt fills composer for user review and does not auto-send | No new real-model quality evaluation or actual media/source inspection |
| Small controls and unclear labels/timezones | Minimum 44px menu/upload targets, analytics label, associated signup labels, concise Account hierarchy, timezone guidance | Measured 390×844 local billing/Studio; no horizontal overflow on billing; dialog focus and Tab navigation checked | Not a physical-phone, screen-reader or WCAG certification |
| Unverified operational recovery | Existing signals extended to billing/mail/cost; read-only monitor probe; release/restore/escalation guidance | Existing worker/restore regressions retained, monitor unit tests; exact-head PostgreSQL/restore/container CI result in handoff | No external alert route or managed production restore performed |
| Whole-account lifecycle not demonstrated | Operator-only all-brand export, dry-run blockers, local active-store erasure, access revocation and receipt | Synthetic file removal, secret exclusion, foreign-account preservation, shared-path/remote/billing blockers | No public erasure endpoint; operator verification, paused writes, provider/backups/S3/retention review still required |
| Stale feature matrix mentioned rejected canvas | Replaced with one current matrix, explicit implementation/provider/deployment columns | Documentation cross-check against current code and handoff | Older dated audits retained as history, not current implementation claims |

## Validation

Baseline 110 tests passed after the first changes. New targeted readiness/security suite: 20 passed at the intermediate stage. Expanded full suite: 123 passed before the last two ownership regressions; final count/outcome is recorded in the handoff. Tests use disposable databases, uploads, mock HTTP and synthetic users. The existing suite continues to cover concurrency, save failures/reloads, media rejection, immutable approvals, partial results, retries and brand isolation. No provider calls were needed for this increment.

Browser preview used a new disposable database and loopback-only server, no Stripe/SMTP/AI/social configuration, and no worker lifespan. An initially malformed synthetic variant fixture was corrected to the existing `{posts:[...]}` schema; it was not a production data change. Checked populated chat, account draft history/reload, saved-voice disclosure, optional useful feedback, billing and recovery. Moved feedback into Post options after mobile inspection to preserve the simple composer. Verified effective CSS viewport 390×844 (billing width 375px within 390px viewport), then reset the override.

Prior 18 September actual Stripe TEST evidence remains distinct: hosted trials, monthly/annual renewal, 3DS, card replacement and manual reconciliation. It was not repeated or upgraded to production certification. New code has no live billing or grant changes.

## Candidate scores using the original rubric

These are **candidate** scores, not a reassessment claiming deployment. Original rubric: 1–2 broken/absent; 3–4 material gaps; 5–6 usable/incomplete; 7–8 strong; 9–10 exceptional/demonstrated. Unchanged higher scores are preserved with their prior limitations; no new comparative industry-leading claim.

| Area | Candidate /10 | Basis |
|---|---:|---|
| Brand and positioning | 7 | Existing identity retained; no wholesale redesign |
| Visual design | 7 | Simpler Account and preserved chat |
| Navigation | 7 | Existing history/navigation retained |
| Customer journey/activation | 5 | Offer/help/recovery guidance improved; real activation not yet measured |
| Studio | 7 | Preserved composition/review; contextual guidance added |
| Mobile | 6 | Measured narrow preview; physical-device gaps remain |
| Accessibility | 6 | Labels/targets/focus improved; no certification |
| AI usefulness/voice | 5 | Correctable guidance; real quality/grounding limits remain |
| Publishing/scheduling | 6 | Existing safety suite retained; provider/operations gates remain |
| Social integrations | 5 | Routes preserved; approvals not reverified |
| Security/account integrity | 6 | Added optional verification and failure checks; live recovery delivery remains a gate |
| Privacy/lifecycle | 5 | Tested scoped export/local erasure; remote/retention/legal gaps remain |
| Analytics | 6 | Existing truthful scope preserved |
| Feature completeness | 6 | Additional recovery/measurement paths; external completion still required |
| Reliability | 6 | Regression and operations checks; managed restore/alerts unproven |
| Commercial/support readiness | 5 | Coherent usable candidate offer and support journey; not paid-launch ready |
| Pricing/unit economics | 4 | Calculator/telemetry work, but tariffs, real costs and margins remain unvalidated |
| Customer validation/retention | 3 | Instrumentation/study ready; no real outcomes |

## Required external inputs and next acceptance

1. Assign the named support/incident owner and backup, approve inbox and coverage; configure and prove recovery/verification email through an approved sender.
2. Supply dated hosting/platform/payment invoices, tax treatment and support workload assumptions; collect real provider token usage. Populate the cost model and demonstrate normal/power-user costs plus alerts. Current prices alone are insufficient.
3. Provide 5–8 representative creators and consent/retention decisions. Run `CUSTOMER_VALIDATION_20260920.md`, including unassisted success and follow-up; retain honest scores if results miss criteria.
4. Complete separately authorised staging/provider/managed restore gates before any paid launch. Do not enable charging just to meet a score.

Rollback and operational limitations: `COMMERCIAL_OPERATIONS_20260920.md`. Updated capabilities: `ZOVA_FEATURE_MATRIX.md`. Both default enforcement flags remain false.
