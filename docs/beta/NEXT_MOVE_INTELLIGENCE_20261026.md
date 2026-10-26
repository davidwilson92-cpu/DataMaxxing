# Next Move intelligence — 26 October 2026

Status: shared web/iOS Studio release candidate f6d43dcc8a42040afc4d9ea712b2963a2213de64
passes both mandatory application runs and native validation; NOT deployed.
Scope: shared web/iOS Studio UI and recommendation service. No native binary,
provider permissions, schema migration, billing change or public post.

## Implemented
- Quick topics supplement, rather than replace, the saved goal/audience/strategy.
- Current voice fields, exclusions, explicit writing examples and recently approved
  captions underpin generation and repair. Existing caption drafting uses current
  preferences. Refinement never silently edits the saved strategy or voice.
- Automatically read available connected-account post metrics when requesting
  ideas, with 15-minute cache/backoff, short provider timeouts and an eight-second
  budget checked between requests. No token renewal in this quick read. Existing
  Performance can still renew credentials through its established path.
- Cohort evidence includes up to 30 dated posts (rather than only the six winners),
  reported formats where available, and missing metrics remain missing. Evidence
  older than 24 hours and mismatched/disconnected account snapshots are excluded.
- Recent drafts, scheduled content/platform/time, explicit creative feedback and
  strategy rhythm inform the model. No inferred conversion, sentiment, growth,
  private-comment access or causal performance claims.
- Keep one proposal, short recommendation and strategy invitation. Optional
  Refine idea is a compact reveal with one text box. Refine generates alternatives
  while retaining the original; failure preserves original and typed feedback.
- Recent recommendation history remains browsable across batches: up to 30 ideas
  restored from the server, up to 60 in the open browser. Continued next requests
  generate more ideas. Revision changes invalidate old-strategy actions.
- Existing owner/brand checks, consent, quotas, optimistic revision checks,
  reviewed publication and duplicate prevention remain in force.

## Review and iteration
1. Initial mobile browser run caught the strategy invitation extending below a
   650px viewport. Compact-height spacing was adjusted; repeat 650/760 checks pass.
2. Refinement initially inherited fresh-title rejection. It now permits keeping
   the selected concept/title while changing its execution; unrelated repetitions
   and duplicate batch titles remain rejected.
3. Performance review added connection-identity binding and guards for unavailable
   counters, preventing stale or unrelated results from masquerading as evidence.
4. Feedback stores the complete bounded request in existing JSON and an 80-character
   summary in the legacy field; no database schema change is required.

## Final application validation
- Exact candidate f6d43dcc8a42040afc4d9ea712b2963a2213de64.
- PR application CI 40396580350: PASS.
- Push application CI 40396577140: PASS.
- SQLite: 719 passed / 2 skipped. PostgreSQL: 720 passed / 1 skipped.
- 30 client tests plus Studio clarity, full mobile browser checks and Next Move
  strategy save/reload/refine/history/draft handoff passed.
- Synthetic PostgreSQL restore, hosting image smoke, constrained password-work
  probe, installed-image dependency audit and exact beta-scope guard passed.
- Both dependency audits found no known vulnerabilities in their tested inventories.
- Native CI40396580393: PASS, including iPhone simulator tests and release compilation. No native source changed.
- No production deployment, new TestFlight binary or real social publication.

## Evidence and limitations
The first full run caught stale source checked_at metadata when an identical idea
was regenerated. The fix preserves the idea ID and explicit feedback while updating
its evidence. Corrected exact-candidate full runs pass. Final prompt-memory review
also removed repeated strategy/voice snapshots from prior-action input; current
strategy and voice are still supplied once, with concise creative history.

Focused initial regression: 42 strategy/series/performance tests passed. Expanded
intelligence/product set initially passed 14 tests; final focused trends/intelligence
set passed 32. Full exact-candidate CI results are recorded above. Browser journey and mobile screenshot inspection passed using
explicitly synthetic AI/provider responses; these are not live generation-quality
or platform availability claims. Screenshots: evidence/20261026-next-move/.

Cannot guarantee every stochastic recommendation follows the prompt. Genuine
creator acceptance and available real provider metrics require post-deployment
acceptance. Public search is not full social listening; no automatic publishing,
asset selection, conversion attribution or guaranteed engagement improvement.
All 79 broader commercial findings stay retained. Render remains the host, customer
charges/plan enforcement stay disabled and paid monitoring stays inactive.


## Publication handoff
Deploy the validated runtime candidate f6d43dcc8a42040afc4d9ea712b2963a2213de64
(or an identical validated runtime digest plus documentation only) only when the
owner asks to publish. Follow the existing Render backup/release procedure, retain
scrypt-v2 compatibility, then verify a controlled consenting test account's Next
Move and draft handoff. Do not post publicly. No new iOS binary is produced by
this shared Studio release; existing TestFlight state is unchanged.
