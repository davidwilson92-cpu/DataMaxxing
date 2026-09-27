# Strategy and Next move — 27 September 2026

## Scope and baseline
Candidate branch `codex/strategy-next-move`, based on deployed commit `b746bada82965baa8f3bf55bf04a921683134b35`. Isolated checkout; original checkout and older worktrees were inspected and left intact. No production deployment, provider grants, real posts or charges.

Read the root handoff and September 22/23 readiness reviews. Their scores are inherited documentary baselines, not a fresh whole-product usability study. Code inspection confirmed no strategy, recommendation or recurrence model in the deployed base. Existing Studio platform formats, brand ownership, immutable final reviews and durable delivery machinery were retained.

Rubric: 1–2 unusable, 3–4 major blockers, 5–6 usable beta with material friction, 7–8 coherent and reliable with bounded verified gaps, 9–10 independently validated exceptional experience.

## Implemented journey
1. Open the compact **Next move** control in Studio. Describe a goal, paste a strategy, import UTF-8 TXT/Markdown up to 20 KB, or edit the fields directly. Existing voice/audience/topics/exclusions prefill the form.
2. Review an AI proposal and its explicit assumptions. Only confirming saves the strategy as approved preferences. Fields remain editable; revision conflicts reject stale changes.
3. Confirming proposes at most three next actions with purpose, effort, missing assets and platform/format. Suggestions use strategy, recent drafts and prior feedback. Live trends are explicitly unavailable; suggestions are evergreen.
4. **Draft this** generates an initial proposal in the existing Studio, preserving the current draft first. Repeated clicks open the same linked draft. Done, Tomorrow and Dismiss persist; Tomorrow lasts 24 hours.
5. Refine through the existing chat and Post/Story controls. Confirmed strategy is added to normal generation and conversation planning.
6. Schedule individually through the existing exact-content review, or create a finite daily/weekly series (up to 26 dates, timezone and weekdays). Preview includes UTC offsets across daylight saving.
7. Fresh occurrences generate only when opened and always need individual review. Repeat occurrences copy a frozen source; the user can review exact destinations/content/media/dates and approve listed occurrences together. Pause, cancel, single cancellation and one/future time edits revoke scheduled jobs and approvals. Resume never silently reinstates cancelled jobs.

## Iteration log
| Pass | Evidence and gap | Severity / customer impact | Correction |
|---|---|---|---|
| Baseline | No strategy-to-action journey or recurrence in deployed code | High: ad hoc drafting only | Add brand-owned strategy, actions and finite series |
| First running review | Initial strategy form showed too many fields | Medium: onboarding effort | Hide details until requested/proposed; reuse existing preferences |
| First running review | Confirming strategy required another manual generation step | Medium: dead end after setup | Generate next moves immediately; retain saved strategy on model error |
| First running review | Linked draft navigation retained busy flag and triggered unload protection | High: Draft this appeared stuck | Clear busy state before navigation; browser verified actual generated draft opens |
| Second review | Repeated schedules lacked collective exact review | Medium: repetitive confirmation | Add expiring, revision-bound batch review using existing immutable approvals |
| Second review | Elapsed snoozes resurfaced but could not draft | Medium: inconsistent next step | Allow elapsed snoozes to reopen; regression test |
| Second review | Cancellation could mislabel completed history | High: inaccurate publication state | Preserve submitted/completed occurrence status; regression test |
| Second review | Cancellation did not release usage; proposal generation bypassed usage accounting | Medium: misleading limits | Release cancelled reservations; use existing AI allowance context, keep enforcement off |
| Visual review | New help/privacy sections initially fell outside main content wrapper | Low: inconsistent page layout | Move sections inside existing content containers |

## Evidence and validation boundaries
Automated: 203 tests passed, 17 existing dependency deprecation warnings (56.78 seconds). The first full attempt hit three temporary-directory permission errors; rerunning with a disposable workspace-local base directory resolved them. JavaScript syntax and git whitespace checks passed. Final targeted subscription-guard regression: 21 passed (2 existing warnings); no enforcement flags changed. New tests cover account/brand separation, revision conflicts, proposal versus confirmation, idempotent and concurrent draft actions, generation failure retention, elapsed snoozes, finite plans, daylight-saving gap/overlap rejection, cancellation, one/future time edits, exact approvals, duplicate confirmation, changed-content partial results, unconfirmed delivery protection and privacy export. Existing security, media, recovery, billing, scheduling and worker tests are retained.

Browser (synthetic localhost, model/provider mocks, scheduler disabled): proposal -> confirm -> three actions -> generated linked draft; reopening linked draft; reload; timezone preview spanning spring DST; create fresh series -> start generated draft. At 390 × 844 CSS pixels, measured document width 390 (no horizontal overflow), conversation region 536 px and text input 38 px. Next move fits the viewport and scrolls; Escape closes it and returns focus to its trigger. Desktop and mobile screenshots inspected. See `strategy-mobile-20260927.png`. This is responsive browser evidence, not a real-device or screen-reader certification.

No real AI quality benchmark, live trend retrieval, actual provider acceptance, production PostgreSQL concurrency run or deployment validation was performed. Mocked output validates the journey, not recommendation usefulness. Existing regression tests cover failed saves/uploads; these failure paths were not all manually repeated in the browser. No claim of independent customer research.

## Re-score (whole-product unless explicitly scoped)
| Area | Documented baseline | Candidate | Evidence / remaining limit |
|---|---:|---:|---|
| Commercial readiness | 5 | 6 | Complete local strategy journey; customer validation/provider gates remain |
| Privacy | 6 | 7 | New records scoped and included in export/erasure; legal/retention review remains |
| Security | 7 | 7 | Ownership, revision, approval and usage protections; no independent security audit |
| Overall UX / journey | 7 | 7 | Strategy leads directly to generated work; real-user friction unmeasured |
| Simplicity | 7 | 8 | One compact default control, progressively disclosed details, useful first proposal |
| Consistency | 6 | 7 | Reuses Studio, brand state and review; broader screens not re-audited |
| Visual brand | 7 | 7 | Existing Zova purple, typography, rail and translucent mark retained |
| Visual clarity | 7 | 8 | Clear action hierarchy, accurate state copy, mobile overflow/proportions checked |
| Studio trust | 7 | 8 | Confirmed preferences separate from assumptions; honest source limitations; immutable approvals |
| Strategy quality / recommendations | Not measured | 6 | Functional context and feedback loop; real-model usefulness unverified |
| Drafting / publishing / scheduling | 6 | 7 | New finite plans and approval regressions; PostgreSQL/live-provider validation remains |
| Mobile / accessibility | 6 | 7 | Responsive layout and keyboard Escape/focus verified; real devices/screen readers outstanding |
| Analytics | 6 | 6 | Unchanged; not a strategy effectiveness measurement system |
| Operations | 4 | 4 | Local rollback plan and synthetic restore tests; managed restore/monitoring gates unchanged |
| Billing clarity | 8 | 8 | Existing offer unchanged, enforcement remains disabled |
| Customer value / economics | 3 | 3 | No new retention, conversion or unit-economics evidence |

No unsupported blanket 8/10 or “industry leading” claim. No known unresolved critical/high defect in the changed local journeys after the listed fixes. Deployment readiness remains conditional on the external gates below.

## Remaining gaps and follow-ups
- Select a licensed/available current-topic source and validate freshness/provenance before advertising live trends. Evergreen fallback is implemented.
- Evaluate real-model strategy and generated drafts against representative customer briefs; no keys/customer data were used here.
- Run new concurrency/rollback scenarios against staging PostgreSQL and a worker before release; SQLite cannot establish PostgreSQL lock behavior.
- Validate final scheduled publishing and Stories with approved provider accounts. Unknown outcomes remain protected; do not resend speculatively.
- Batch repeat UI uses existing default destination selection; TikTok-specific settings should use individual Studio review. It must not be presented as a complete batch TikTok experience.
- Future-scope editing currently changes timing. To change future content, create a new series from an edited draft and cancel the old remaining plan; generated occurrences can be edited individually. Automatic rolling series replenishment is not included.
- TXT/Markdown import is supported; PDF/Word requires pasting relevant text. Strategy file originals are not uploaded.
- Independent accessibility, customer usability, real-device and production backup/restore validation remain open.

## Rollback
Before a release, back up and restore-test PostgreSQL. Additive tables are created by existing startup schema creation; no user/draft/auth/media/social columns are changed. Keep the new tables on rollback. Before reverting to base `b746bad`, cancel pending series deliveries and verify no sending/unknown job is being rolled back as cancelled. The old worker understands individual jobs and would otherwise continue them. Keep completed publication history and encrypted connections intact. Revert candidate code/assets only; never delete production records to undo this feature.
