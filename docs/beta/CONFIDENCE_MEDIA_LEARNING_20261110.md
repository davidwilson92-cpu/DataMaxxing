# Publishing confidence, reusable media and visible AI evidence

Review candidate, 10 November 2026. Branch `codex/confidence-media-learning-20261110`.
Baseline: `4a6fc00` (same application tree as the preceding compact-toolbar release).

This is a bounded improvement to the existing product, not commercial certification.
No production deployment, TestFlight distribution, App Store release, social post,
infrastructure change or billing enablement is authorised by this task.

## Customer journey

Studio and Campaign now offer **Saved media** alongside device attachments. Owners
can search photos/videos, select existing owned files and reuse them without another
upload. Cancellation leaves the post alone. Removing an attachment changes that
post's selection; it does not erase the asset or another post's references.

The library distinguishes saved, planned, processing, unconfirmed and published uses.
An asset can have several states. Publication usage comes from the approved media
snapshot; attaching a replacement to an already published draft does not retroactively
mark the replacement published. Repeated references to one canonical post are grouped.

Campaign cards include a compact status summary and recovery guidance. Schedule
shows upcoming deliveries for the next seven days with links to work needing attention.
Publication responses carry safe support references. These are projections of existing
records: they do not dispatch, approve, retry or reconcile an uncertain post themselves.

Next Move and campaign refinement expose a short, expandable evidence control.
Available examples retain missing counters as unavailable and genuine zeros as zero.
Evidence is platform-filtered for a single-platform recommendation, dated and marked
when stale. Sparse evidence produces an idea to test, not a promised result. The
existing strategy, voice, explicit feedback and upcoming-content inputs remain intact.
No additional AI request or model upgrade is introduced by this disclosure.

Bulk upload recovery retains completed assets. Web Studio retries failed files only
and reconstructs the original chosen order; native selection uses ordered photo
picking, tracks original slots across retries and retains failed selections while the screen/session is alive. Saved media
provides recovery for a completed upload whose response or brief save was interrupted.
Uploads are not silently restarted after app termination.

## Finding → change → verification

| Finding | Change | Evidence |
|---|---|---|
| Previously uploaded content required another upload | Owner/workspace-scoped media library in both attachment flows | `test_confidence_media_learning.py`; `confidence_browser.cjs`; native library UI tests |
| Aggregate draft status could mislabel replacement media | Frozen publication and schedule references determine usage | Published-original/replacement/upcoming-use integration test |
| Several uses of one file looked like several copies of a post | References grouped by canonical draft/campaign IDs | Same-title, multi-state, remove-without-delete test |
| Searching/filtering discarded selected saved media | Keep choices across search/type filters on both clients; block application during loading | Phone/desktop selection and delayed-search race tests; native cross-filter UI test |
| A failed brief save could duplicate a selected attachment on retry | Deduplicate existing IDs before applying the selection | Browser abort-first-save test, one attachment after retry/reload |
| Picker controls could re-enable already attached files after failure | Restore each control's previous ownership/selection constraint | Browser disabled-existing-selection check |
| Old workspace replies could affect a new selection | Server ownership checks plus client authority/version guards | Cross-account/brand tests; native authority checks; stale Studio reply suite |
| Mobile toolbar moved between pointer-down and click | Preserve composer focus until the toolbar action executes | Actual 390px browser first-click failure reproduced, fixed and retested |
| Web batch failure obscured completed uploads | Per-file requests, progress, retained successes and failed-only retry | Two-file fault injection; three requests total; original order after retry/reload |
| Native Studio stopped at the first failed file | Continue remaining files, retain retry selections; save failures do not re-upload an already attached file | Source review and native compile/regression; physical picker fault exercise remains unverified |
| Campaign progress disappeared after a later failure | Per-file uploaded/waiting/unconfirmed states and retained IDs | Campaign recovery browser tests and existing media validation suites |
| Native retry could append an early failed file after later successes | Shared ordered-slot tracking with authority/attachment guards | All 256 initial/retry failure subsets for a four-file batch; physical picker fault exercise still unverified |
| Status summaries omitted queued/review states | Shared state labels and explicit preparing/awaiting-approval counts | State projection tests; no publication-side mutation |
| Uncertain outcomes looked retryable | Preserve destination/results checks and no-auto-resend guidance | Reviewed publication, timeout, race and unknown-outcome regression suites |
| Recommendation rationale could not be inspected | Deterministic evidence from the actual performance context, not model-generated metrics | Zero/null/stale/platform tests; Next Move input-capture tests |
| Extra evidence pushed Your strategy off a short screen | Combine secondary evidence/refinement controls and remove repeated basis text | `next_move_focus_browser.cjs`, 390×650 and 390×760 |
| Native evidence could repeat the same basis text | Match concise web labels; disclose detail on expansion | Native Next Move and campaign fixture/UI assertions |
| Selected media had a visual check without an explicit spoken state | Expose Selected/Not selected to iOS accessibility | Native cross-filter/reopen UI assertions; full physical VoiceOver audit remains open |

## Baseline and evidence classification

Already present and preserved: canonical drafts; skippable introduction; draft-before-
connection; reviewed publishing; durable jobs; ambiguous-outcome protection; campaign
pause/move/reuse/refinement; retained strategy/voice; consent enforcement; entitlement
checks; private media delivery; revision conflict handling. This work does not recreate
or claim novelty for those features.

Evidence types are kept separate:

- **Observed:** local browser actions/screenshots against the real application with
  disposable accounts; simulator interaction when recorded in native validation.
- **Automated:** API, database, concurrency, security, client and native tests.
- **Documented:** competitor capabilities stated in their current official material.
- **Synthetic critique:** reasoned persona reactions below. No real participants,
  measured satisfaction or willingness-to-pay study occurred.
- **Unverified:** live provider publishing/OAuth, physical-device backgrounding and
  iCloud downloads, live AI quality/latency, production load and an independent audit.

## Route and journey coverage

The generated `route-inventory.csv` inventories 161 OpenAPI method/path operations.
`complete-route-inventory.csv` additionally traverses included routers and records
182 operations/mounts, including hidden routes, framework documentation and static
delivery. These are inventories, not a claim that every route was manually exercised;
the execution coverage and its limits are mapped below.

| Journey/state family | Coverage approach and test families | Boundary |
|---|---|---|
| Sign-in, recovery, account/workspace switching | Existing account integrity, session, brand/native presentation suites; new media owner/brand matrix | Real Apple/social login not repeated |
| First idea, destination choice, disconnected drafting, recovery | Studio clarity/client, mobile composer and first-use browser suites | Captions supplied by deterministic fixtures |
| Saved post, rename, same titles, reopen, media reuse | New API/browser/native tests plus existing draft/media suites | Library search currently matches filenames, not semantic image contents |
| Campaign brief/build/edit/accept/pause/resume/move/reuse/extend/improve | `test_campaigns`, `test_campaign_brief_qa`, `test_campaign_refinement`, `test_campaign_controls`; phone/desktop control browser journey | Provider/model outputs mocked |
| Draft, review, queued, scheduled, processing, published, failed, partial, unknown | Explicit status projections and reviewed-publication/worker suites | No real delivery made |
| Time zones, DST and rescheduling | `test_schedule_windows`, `test_schedule_editing`, campaign timing tests | Not every global zone/date combination |
| AI consent, voice, strategy, sparse/stale/zero performance | AI privacy, strategy revision/series, Next Move intelligence and evidence tests | No new live-model evaluation or revenue inference |
| Premium eligibility and disabled charges | Brand/allowance and Stripe test-mode suites | No live purchase or billing setting changed |
| Offline/save failure/retry/concurrency | Aborted save/upload browser tests; revision, worker and timeout suites | App termination during a physical Photos upload unverified |
| Navigation/accessibility | 320px enlarged-control keyboard check, 390px and desktop browser, short composer viewports, keyboard/Escape/focus, native normal/largest text | Full VoiceOver audit and all hardware sizes unverified |

Status enumeration and owner/brand access are exhaustively covered for the selected
finite cases. Broader journeys use risk-based combinations (device × workflow,
connection × draftability, media × recovery, evidence × recommendation). This is not
an exhaustive Cartesian product or a certified all-pairs covering array. No claim of
every route/permutation or absolute defect freedom is made.

## Competitor benchmark

Sources checked 10 November 2026. Rubric defined before scoring: **0** absent,
**1** workaround, **2** partial, **3** selected task works with clear control and tested
recovery, **4** independently validated under real customer/provider conditions.
**U** means insufficient evidence. Scores below assess Zova's selected task coverage,
not subjective satisfaction or superiority over a competitor. Paid competitor flows
were not hands-on timed; their latency and accessibility scores remain U.

| Criterion | Relevant competitive bar | Zova baseline → candidate | Evidence/limit |
|---|---|---|---|
| Useful first caption | Editable AI drafting, minimal setup | 3 → 3 | Existing disconnected drafting retained; real caption preference U |
| Campaign creation/refinement | Saved plan, editable posts, approval control | 3 → 3 | Existing controls/regression; no new compulsory step |
| Media organisation/reuse | Reuse without uploading again; visual selection | 1 → 3 | New private library and fault recovery; no folders/tags/semantic search |
| Publishing clarity/recovery | Understand pending/failure; recover without duplicate posts | 2 → 3 | Shared projections, affected-post routes, existing durable-send tests |
| Recommendation evidence/authenticity | Brand context and inspectable relevant results | 2 → 3 for evidence; authenticity U | Deterministic evidence; no fabricated live model quality score |
| Mobile/web consistency | Same work and controls, usable small-screen layout | 2 → 3 for targeted journeys | Web/browser and native simulator checks pass; physical provider parity U |
| Performance/accessibility | Responsive interaction with reachable controls | 2 → 3 locally | Synthetic timings and targeted checks; production/WCAG audit U |
| Trust/control | Reviewable AI changes, consent, accurate limits | 3 → 3 | No silent publish/strategy overwrite or new charges |

No overall score is calculated across unverified cells. Selected functional standards
can be compared with documented competitor capabilities; this is not evidence that
Zova is faster, more reliable or market-leading in real use.

| Competitor | Relevant documented capability and implication |
|---|---|
| [Buffer](https://buffer.com/pricing) | Ideas, AI drafting/refinement, scheduling and insights. Preserve the short path from idea to editable post. |
| [Later](https://help.later.com/hc/en-us/articles/360043246993-Getting-Started-With-Later-Social) | Upload/organise/reuse through a media library; desktop/mobile feature differences are acknowledged. This is the clearest missing capability addressed here. Article updated 21 Oct 2026. |
| [Metricool](https://metricool.com/social-media-analytics-tool/) | Analytics and reporting inform content decisions. Zova must explain measurement scope rather than suggest that engagement proves sales. This vendor-authored comparison is not independent performance evidence. |
| [SocialBee](https://help.socialbee.com/hc/en-us/articles/29979132682391-Social-Media-Copilot-All-You-Need-to-Know) | Editable business context, strategy, categories and generated posts, followed by approval. Zova retains its shorter existing brief rather than adding category setup. |
| [Planable](https://help.planable.io/hc/en-us/articles/28555055158044-Reviewing-content-in-My-approvals-section) | Explicit content review/approval workflows. Keep proposed AI changes distinct from applied and published content. |
| [Predis.ai](https://predis.ai/features/) | Broad creative generation, publishing and approval features. Video generation/editing is outside this bounded scope. |
| [Hootsuite](https://help.hootsuite.com/s/article/get-started-owlygpt) | Current documentation calls Wisdom the successor to OwlyGPT; it uses brand context, supports content and performance questions, and describes social-listening capabilities. Updated 5 Nov 2026. Zova must not imply equivalent listening access. |

Customer reports provide priorities, not verified competitor defects:

- [Buffer Google Play](https://play.google.com/store/apps/details?hl=en&id=org.buffer.android): February 2026 feedback asks for clearer failure explanations; May/June reports describe media/reconnection problems. The listing was updated 6 Oct 2026; the reported versions are unspecified. This motivated retained uploads and honest failure states.
- [Later UK App Store](https://apps.apple.com/gb/app/later-social-media-scheduler/id784907999?platform=iphone&see-all=reviews): a 3 Aug review praises earlier simplicity but describes extra calendar/copying steps after an update. The displayed review omits its year/version. Preserve navigation and avoid compulsory guidance.
- [SocialBee Trustpilot](https://www.trustpilot.com/review/socialbee.io): positive reports value ease and support; a 5 Oct 2026 report describes reliability/support delays. Selected reviews are not a representative failure-rate estimate.
- [Predis G2](https://www.g2.com/products/predis-ai/reviews): a 7 Oct 2026 reviewer values quick creative production but reports uneditable generated audio and an incorrect product pronunciation. Preserve human review and editable output; do not equate generation with correctness.

## Synthetic focus-group critique — hypotheses only

These are separate critical lenses applied to observed screens and task flows, not
people recruited or a timed one-hour usability study. No satisfaction percentages or
willingness-to-pay figures are invented.

| Synthetic participant | Likely friction / dissent | Response and remaining validation |
|---|---|---|
| Impatient Brixton gym owner, six staff | A tap doing nothing is unacceptable; another library tab adds effort | First-tap regression fixed; media picker stays inside the current task |
| Florist, Friday collection | Re-uploading the same bouquets wastes time | Search/reuse/save/reopen observed on web; dates remain editable |
| Barber, last-minute cancellation | Preparing can be mistaken for posted | Distinct preparing/processing/published states; practical results route |
| Bakery with changing collection dates | Reuse can retain stale date wording | Existing date-change warnings retained and regression tested |
| Pottery teacher | Evidence should not bury Your strategy | Short-screen regression fixed; secondary details collapsed |
| Retailer with many photos | Same filenames/titles are hard to distinguish; folders would help | Thumbnails, type/search and canonical use references; folders remain a justified follow-up |
| Creator seeking authentic captions | Likes alone do not show what sells; generic explanations undermine trust | Zero/missing/lifetime limits visible; real caption preference and sales attribution still need real evidence |
| Cautious owner with low AI confidence | Opening a library should not send images to AI | Read-only library performs no model call; existing consent remains at AI task boundary |
| Experienced social manager | Wants automatic asset deduplication and deeper comparative analytics | No false promise of byte-level deduplication or causal analysis; those require separate evidence/work |
| Larger-text/keyboard user | Dense controls, lost focus and clipped filenames | 44-point primary controls, wrapping, Escape/focus restoration and native largest-text checks; full VoiceOver review remains unverified |

Iteration 1 added the capabilities. Iteration 2 caught retry duplication, replaced-media
misclassification and moving mobile controls. Iteration 3 caught the short-screen
strategy-callout regression and strengthened partial-upload and native evidence tests.
Real owners still need to judge their own captions and whether they would pay.

## Performance, security and remaining risks

`before.json` / `after.json` use the same production ASGI benchmark with 1,000 drafts,
five samples, synthetic provider/AI delays and an isolated SQLite database. They are
not production latency, model quality or concurrent-user capacity results. Local
media-library workload results and browser timings are recorded separately. No new
infrastructure, database schema, provider calls, AI calls or caching layer was added.

Security checks cover owner/brand filtering, search and pagination, private URLs,
no-store responses, escaped user text, retained revision/consent boundaries and
unchanged billing gates. Dependency auditing and synthetic database restore are
included in required CI. This does not replace independent penetration testing.

Remaining limitations:

- After app termination, unfinished device files must be selected again. Completed
  assets can be recovered from Saved media. No resumable byte-level background uploader
  or upload idempotency ledger was added; an explicitly retried ambiguous upload can
  create an extra asset, although it cannot publish a duplicate social post.
- Library usage reads narrow owner-scoped draft records in batches. Very large histories
  need further load evidence; 1,000-draft local measurements are not a scale guarantee.
- Filenames, not image contents, are searchable. No asset deletion UI was introduced;
  existing account-deletion/retention processes still apply.
- Live provider formats, OAuth, receipt links, revocation and physical iPhone background
  behaviour require separately labelled acceptance. There were no real social posts.
- The original 79-section register remains: 58 partial, 12 gaps, 9 unverified. Historical
  P0 domains include tenancy, authorisation and publishing assurance. The paused broad
  RLS/service migration was not activated. Independent security, operational recovery,
  storage-policy and comprehensive privacy evidence are not closed by this feature work.

## Release recommendation and rollback

Hold production and distribution for owner review. Native final results and the exact
candidate check links are recorded in the validation addendum. A passing feature gate
supports a limited beta candidate; it does not certify commercial readiness.

No schema migration is required. If later authorised and deployed, web rollback is to
the preceding approved application revision while retaining all newly saved owned
assets and draft references. Native rollback means stopping further distribution and
shipping a corrected higher-numbered build; installed binaries cannot be remotely
downgraded. Preserve the existing approval, unknown-outcome and consent protections
throughout any rollback. Never resend an uncertain publication as part of recovery.
If an old server revision is restored after a future native rollout, the new library
endpoint would be unavailable to installed clients; their existing device-upload flow
remains. Prefer a scoped roll-forward retaining that read-only endpoint, and explicitly
verify client/server compatibility before a rollback. No such rollout occurred here.


## Performance measurements

Local medians in milliseconds. Both revisions use identical isolated workloads;
providers and AI are deterministic delayed fixtures. Baseline and candidate were
measured sequentially without the earlier concurrent local test load. These small
samples show no material regression and do not establish a speedup or live SLA.

| Operation | Before | Candidate |
|---|---:|---:|
| Login | 1,034 | 1,049 |
| Studio response | 33.7 | 32.6 |
| Draft listing (1,000 drafts) | 44.2 | 43.9 |
| Schedule | 56.9 | 54.8 |
| Performance | 97.9 | 99.5 |
| Next Move, synthetic model | 485.1 | 476.9 |
| Caption generation, synthetic model | 422.7 | 395.6 |
| Upload 793 KB synthetic JPEG | 42.4 | 41.7 |
| Save draft with media | 30.3 | 19.6 |
| Reopen saved draft | 8.8 | 7.3 |
| Campaign page response | 7.1 | 7.3 |

The new library's 500-asset/1,000-draft workload returns 30 assets in a 29.7 ms
median across eight samples (10 SQL statements, about 9.9 KB). Local browser opening
measured 102 ms at 390px and 116 ms at desktop. These are separate fixtures, not
production or physical-device measurements. The final CI fixture measured library
opening at 75 ms (phone) and 58 ms (desktop); see `browser-ci.json`. Large video/network transfer times are
not inferred from the small image test.

Reproducible source: `scripts/benchmark_performance.py`,
`scripts/benchmark_media_library.py` and the saved upload-measurement script.
Raw samples and route inventory are in [the evidence directory](evidence/confidence-media-learning-20261110/).

## Screenshot review

Screenshots show synthetic accounts and content. Baseline native images come from
the preceding compact-toolbar validation; candidate images come from this branch's
simulator checks. They are not screenshots of a new distributed build.

| Surface | Before | Candidate |
|---|---|---|
| Phone campaign/attachment entry | [Campaign before](evidence/confidence-media-learning-20261110/campaign-before-390.png) | [Saved media](evidence/confidence-media-learning-20261110/library-390.png) |
| Desktop | [Campaign before](evidence/confidence-media-learning-20261110/campaign-before-1366.png) | [Saved media](evidence/confidence-media-learning-20261110/library-1366.png) |
| Studio recovery | Existing upload experience; failure captured in test | [Reopened attachments, phone](evidence/confidence-media-learning-20261110/studio-390.png), [desktop](evidence/confidence-media-learning-20261110/studio-1366.png) |
| Short-screen Next Move | [Before](evidence/confidence-media-learning-20261110/next-move-before-650.png) | [Compact secondary controls](evidence/confidence-media-learning-20261110/next-move-focused-650.png) |
| Native campaign | [Normal](evidence/confidence-media-learning-20261110/native-campaign-before.png), [largest text](evidence/confidence-media-learning-20261110/native-campaign-before-largest.png) | [Normal](evidence/confidence-media-learning-20261110/native-campaign.png), [largest text](evidence/confidence-media-learning-20261110/native-campaign-largest.png) |


Native saved-media selection: [normal](evidence/confidence-media-learning-20261110/native-library.png) and [largest accessibility text](evidence/confidence-media-learning-20261110/native-library-largest.png). Selection, filenames, Cancel and Use selected remain reachable. The automated accessibility-value assertions verify selected/unselected state after filtering and reopening; spoken VoiceOver output is not claimed as manually verified.

Native AI presentation: [Next Move before](evidence/confidence-media-learning-20261110/native-next-move-before.png) → [candidate](evidence/confidence-media-learning-20261110/native-next-move.png); [campaign refinement before](evidence/confidence-media-learning-20261110/native-refinement-before.png) → [inspectable evidence](evidence/confidence-media-learning-20261110/native-campaign-evidence.png) and [original retained until Apply](evidence/confidence-media-learning-20261110/native-refinement.png). These fixture campaigns omit a display name and therefore show the existing “Campaign 6” fallback; real saved campaign naming was not changed.

## Final critical review

| Lens | Challenge | Decision |
|---|---|---|
| Customer | Can I find yesterday's photo without understanding storage? | Saved media is beside existing attachments; cancel, reuse and reopen are exercised. Filename search remains a limit for large collections. |
| Product designer | Will more evidence make the first useful action harder to find? | Details stay collapsed; the short-screen layout preserves the proposal, action and strategy link. No compulsory onboarding was added. |
| Social-media specialist | Does a stronger-sounding recommendation actually have better evidence? | Examples come from available data, retain platform/date/format, and disclose sample limitations. No promised engagement or sales lift. |
| QA/security | Can partial failure, a switched account or a retry corrupt the result? | Preserve owned canonical IDs, compare authority/revisions, retry failed files and test order permutations. Real device/provider acceptance remains open. |

Synthetic tasks included the gym's trial post, florist's collection offer, barber's
cancellation, bakery's changed date, pottery class, retailer's reusable product media,
creator's performance question and cautious owner's consent decline. These are mapped
to the existing/new test families in the journey matrix. The reactions are analyst
hypotheses applied to those paths, not ten independent people completing usability tests.

## Follow-ups requiring separate evidence or scope

| Work | Value | Dependency / cost / complexity |
|---|---|---|
| Resumable background video upload and upload idempotency | Recover large transfers after termination without extra assets | Native background transfer design, storage multipart support and durable ownership/retry ledger; medium-high engineering and storage/request cost |
| Optional media folders/tags | Find assets in large collections | Real library search failures and user demand first; medium UI/data migration effort, small storage overhead |
| Matched performance cohorts | Better comparison by platform, format and post age | Sufficient permitted provider history and sound sample sizes; medium analytics work, provider-fetch cost |
| Live caption/voice evaluations | Establish authentic quality and willingness to pay | Consenting real owners, approved examples, blind evaluations and measured model cost; no automatic stronger-model upgrade |
| Physical-device and independent security acceptance | Evidence beyond mocks and simulator | Review build after release authorisation, device/iCloud/network tests and scoped independent assessor; external time/cost not committed |

## Validation addendum

Review PR: [#49](https://github.com/davidwilson92-cpu/DataMaxxing/pull/49), based on
`codex/campaign-qa-fixes`, the established Render release branch. `main` is historical
and is not this candidate's release target. No merge or release was performed.

Final runtime candidate `723a26a`:
[full required application run](https://github.com/davidwilson92-cpu/DataMaxxing/actions/runs/42872780694)
**passed**: 826 SQLite tests, 827 PostgreSQL tests, the JS/client/browser suites,
synthetic backup/restore, hosting-image smoke test, dependency audits and production
guardrails. SQLite skips the two real-PostgreSQL-only tests; PostgreSQL skips the
SQLite backup test because its dump/restore runs separately. These are complementary
coverage, not unexplained skips. Both dependency audits found no known vulnerabilities
at the time of this run; that is not proof of absence of security defects.

The same final runtime `723a26a` **passed 46 native unit tests, 28 UI tests and iPhone Release compilation** in [native run 42872781079](https://github.com/davidwilson92-cpu/DataMaxxing/actions/runs/42872781079). This includes exhaustive 256-case four-file retry ordering, normal/largest-text media selection, selection across filters, accessibility values, campaign status/evidence and preservation of original captions until Apply. The simulator screenshots above were visually inspected.

CI reported non-blocking notices about older pinned actions being run on Node 24 and macOS runner capacity. Updating the action pins can be handled in a separate maintenance change; neither notice represents a failed application or native test.

The final evidence commit changes documentation/artifacts only. The passing runs above identify the exact validated runtime; any fresh PR checks triggered by documentation alone are separate from these recorded results.

No production settings were modified. The unchanged billing guards were exercised in
regression; customer charges remain disabled. The existing released build is unchanged.

Additional keyboard check: at 320px with enlarged library controls, Enter opens,
Space selects, Tab cannot reach the obscured page, Escape cancels and focus returns
to Add/Saved media. Browser chrome remains reachable as expected for a native HTML
dialog. Selected attachments remain unchanged after cancellation. This is a targeted
keyboard/layout check, not a full screen-reader or WCAG certification.
[Enlarged-controls screenshot](evidence/confidence-media-learning-20261110/library-320-large-text.png).


## Physical-device acceptance before wider distribution

After the owner authorises a review build, check a real iPhone with Photos/iCloud:

1. Select several campaign photos/videos, interrupt one transfer, retry and verify
   original ordering and a saved/reopened brief. Completed files must remain reusable.
2. Background and terminate during separate transfers. Confirm completed assets remain
   in Saved media; unfinished files require deliberate reselection, not an unseen resend.
3. Use saved-media search/type filters with VoiceOver and largest text; verify selected
   state, Cancel, Use selected, dismissal and focus are understandable.
4. Switch brand/account after a failed operation and verify no old asset or pending
   retry can be applied to the new context.
5. Check connected/expired social profiles and final-review cancellation. Any real
   publication requires its own explicit approval; an uncertain result must not resend.

These are focused remaining acceptance paths, not instructions already performed or
an authorisation to distribute. No external dependency has been marked passed merely
because the deterministic tests passed.


## Comparable-task capability matrix

**D** means documented by the supplier, not hands-on verified. **U** means not
established by the reviewed sources. Every competitor's task timing, failure rate,
AI authenticity and accessibility quality remains U. A documented feature does not
prove an equivalent implementation or user outcome. Sources were checked 10 Nov 2026.

| Product | First caption | Campaign/refinement | Reusable media | Publishing clarity/recovery |
|---|---|---|---|---|
| Buffer | D AI drafting | D drafts/queue; campaign-level refinement U | U for owned-asset library parity | D draft/approval/queue states; ambiguous-outcome recovery U |
| Later | D caption generation and rephrasing | D calendar planning; whole-campaign AI refinement U | D synced library, labels/notes/filtering | D scheduling; duplicate-safe failure recovery U |
| Metricool | D AI text | D planning/editing/duplication | D Post Library; not assumed identical to an asset library | D edit/reschedule and reminder publishing; uncertainty handling U |
| SocialBee | D AI captions | D Copilot strategy/categories/posts | Asset-library parity U | D overdue/upcoming/published, with some manual-completion states |
| Planable | D generated captions | D planning, review, approval and scheduling | D workspace library and reuse | D draft/scheduled/published statuses and permissions; uncertainty handling U |
| Predis.ai | D creative/caption generation | D calendar/publishing; reviewed remaining-post optimisation U | D asset library; owned reuse semantics U | D publishing/approval features; timeout recovery U |
| Hootsuite | D AI content assistance | D planning/approvals | D managed content libraries | D publishing tasks/approval; uncertainty handling U |

| Product | Recommendation relevance/evidence | Mobile/web consistency | Performance/accessibility | Trust/control |
|---|---|---|---|---|
| Buffer | D AI and insights; per-recommendation evidence U | D mobile drafts synced with web | U | D draft approvals; independent security U |
| Later | D prompt/tone; performance-to-recommendation linkage U | D iOS captions and synced media; selected features desktop-only | U | D editable output; independently verified privacy/security U |
| Metricool | D analytics and posting times; explanatory evidence U | D mobile feature matrix; Post Library documentation conflicts | U | D approvals; independent security U |
| SocialBee | D editable brand context and strategy; causal evidence U | D companion/reminder flow, not assumed full web parity | U | D review before publishing; independent security U |
| Planable | D caption generation; performance linkage U | D mobile uploads; full parity U | U | D workspace permissions and review approvals; independent security U |
| Predis.ai | D visual brand consistency; evidence-based recommendations U | U for native parity | U | D approval features; independent security U |
| Hootsuite | D brand context/performance questions; social listening is separately supplied | D mobile approvals/planner; content library unavailable in mobile | U | D content availability/permissions; independent security U |

Additional supporting sources:

- [Buffer mobile drafts](https://support.buffer.com/articles/creating-managing-and-approving-draft-posts-on-the-buffer-mobile-app-XSRim1JeUl) documents drafting before channel selection and synced web/mobile drafts. Preserve Zova's equivalent low-friction start; do not require connection before drafting.
- [Later Caption Writer](https://help.later.com/hc/en-us/articles/12252569781015-Later-s-Caption-Writer), dated 2 Jul 2026, and [media organisation](https://help.later.com/hc/en-us/articles/360042771474-Access-Organize-Your-Media-Library), updated 24 Aug 2026, support caption and reuse comparisons. Zova matches the basic reuse task; Later's richer media organisation remains a gap, not silently declared unnecessary.
- [Metricool mobile features](https://help.metricool.com/features-available-in-the-mobile-app-213ni) lists mobile Post Library access, while [its Post Library guide](https://help.metricool.com/posts-library-u05cj) says it is unavailable in the mobile version described. This inconsistency is marked unverified; no parity claim is made from it.
- [SocialBee mobile](https://help.socialbee.com/hc/en-us/articles/29979248854935-Using-the-SocialBee-Mobile-App) documents reminders and manual completion. This reinforces keeping finish-in-platform visibly different from confirmed automatic delivery.
- [Planable product](https://planable.io/product/), [media library](https://planable.io/guides/media-library/) dated 30 Mar 2026, and [scheduling](https://help.planable.io/hc/en-us/articles/21715441152028-How-to-schedule-a-post) updated 29 Oct 2026 support the comparison. Zova now covers reuse and explicit state labels; team collaboration and archival media management remain separate scope.
- [Hootsuite content libraries](https://help.hootsuite.com/s/article/manage-library) and [mobile updates](https://www.hootsuite.com/whats-new/accelerate-your-strategy-with-hootsuites-latest-mobile-updates) distinguish web library management from mobile publishing tasks. Zova's library is implemented on both surfaces, but that alone does not establish superior usability.

An additional [Buffer incident report](https://status.buffer.com/incidents/01M6R5MCP3V06DKZ27CHZ1M7GY)
records a resolved 6 Nov 2026 issue affecting saving posts/drafts behind an upload-wait
message. This is supplier-confirmed historical evidence, not a claim of a current fault.
It reinforces testing save/reopen and stuck-upload recovery separately from happy-path
publishing. No competitor defect rate or comparative reliability score is inferred.


Native test-harness correction: run 42855699951 passed 46 unit tests and 27 of 28 UI
tests, including media reuse, cross-filter selection and largest-text controls. The
remaining assertion exposed an outdated offline Next Move fixture with no `learning`
field. The fixture now matches the backend evidence contract and the same disclosure
assertions remain enabled. That failed run is not counted as full native acceptance;
the corrected candidate passed the final run linked above. Campaign fixtures were
also extended to exercise their status summary and evidence disclosure. The final
review corrected singular “1 draft” wording and added explicit native selection
accessibility values; earlier passing runs do not substitute for final validation.
