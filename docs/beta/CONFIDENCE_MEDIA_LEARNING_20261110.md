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
picking and retains failed selections while the screen/session is alive. Saved media
provides recovery for a completed upload whose response or brief save was interrupted.
Uploads are not silently restarted after app termination.

## Finding → change → verification

| Finding | Change | Evidence |
|---|---|---|
| Previously uploaded content required another upload | Owner/workspace-scoped media library in both attachment flows | `test_confidence_media_learning.py`; `confidence_browser.cjs`; native library UI tests |
| Aggregate draft status could mislabel replacement media | Frozen publication and schedule references determine usage | Published-original/replacement/upcoming-use integration test |
| Several uses of one file looked like several copies of a post | References grouped by canonical draft/campaign IDs | Same-title, multi-state, remove-without-delete test |
| A failed brief save could duplicate a selected attachment on retry | Deduplicate existing IDs before applying the selection | Browser abort-first-save test, one attachment after retry/reload |
| Picker controls could re-enable already attached files after failure | Restore each control's previous ownership/selection constraint | Browser disabled-existing-selection check |
| Old workspace replies could affect a new selection | Server ownership checks plus client authority/version guards | Cross-account/brand tests; native authority checks; stale Studio reply suite |
| Mobile toolbar moved between pointer-down and click | Preserve composer focus until the toolbar action executes | Actual 390px browser first-click failure reproduced, fixed and retested |
| Web batch failure obscured completed uploads | Per-file requests, progress, retained successes and failed-only retry | Two-file fault injection; three requests total; original order after retry/reload |
| Native Studio stopped at the first failed file | Continue remaining files, retain retry selections; save failures do not re-upload an already attached file | Source review and native compile/regression; physical picker fault exercise remains unverified |
| Campaign progress disappeared after a later failure | Per-file uploaded/waiting/unconfirmed states and retained IDs | Campaign recovery browser tests and existing media validation suites |
| Status summaries omitted queued/review states | Shared state labels and explicit preparing/awaiting-approval counts | State projection tests; no publication-side mutation |
| Uncertain outcomes looked retryable | Preserve destination/results checks and no-auto-resend guidance | Reviewed publication, timeout, race and unknown-outcome regression suites |
| Recommendation rationale could not be inspected | Deterministic evidence from the actual performance context, not model-generated metrics | Zero/null/stale/platform tests; Next Move input-capture tests |
| Extra evidence pushed Your strategy off a short screen | Combine secondary evidence/refinement controls and remove repeated basis text | `next_move_focus_browser.cjs`, 390×650 and 390×760 |
| Native evidence could repeat the same basis text | Match concise web labels; disclose detail on expansion | Native Next Move fixture and UI assertion |

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

The generated `route-inventory.csv` inventories 161 OpenAPI method/path operations;
it is an inventory, not a claim that every route was manually exercised. Static files,
framework documentation and signed media transport are covered separately where tested.

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
| Navigation/accessibility | 390px and desktop browser, short composer viewports, keyboard/Escape/focus, native normal/largest text | Full VoiceOver audit and all hardware sizes unverified |

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
| Mobile/web consistency | Same work and controls, usable small-screen layout | 2 → pending native final validation | Web complete; native evidence recorded separately |
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
