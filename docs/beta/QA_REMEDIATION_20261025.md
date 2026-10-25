# Zova beta QA remediation — 25 October 2026

## Scope and evidence boundaries

This is the traceability record for the tester's **Zova Social QA Tracker** workbook and the owner's seven additional requests. It records implementation and regression coverage, not a release approval or a replacement customer assessment.

The source workbook contains **57 actual test cases, 7 populated bugs and 5 populated UX observations**. Example rows and empty BUG/UX placeholders are excluded. The extracted source is `zova-qa-20261025.json`; the original workbook remains unchanged. The tester specified iPhone 16 but left iOS version, TestFlight build and comparison browser blank. These omissions limit exact reproduction and must be filled in during retesting.

Original totals: **46 Pass, 7 Fail, 3 Blocked, 1 Untested, 0 N/A**. The workbook reports **82.14%**, calculated as 46/56; that denominator excludes Untested but includes Blocked. It must not be represented as a new verified pass rate. No original result below has been changed because code was edited.

Work remains on the current Render architecture with customer charges disabled. No live customer deletion, provider permission expansion, public test post or production schedule cancellation is implied by this document. Final suite results, CI, deployment and TestFlight details are to be appended by the release owner after verification.

### Status language

- **Implemented, retest pending:** code and targeted regression coverage exist; the replacement build and real device journey still require confirmation.
- **Partial:** useful remediation exists, but a material requirement remains unmet.
- **External check:** requires a real provider/account/device, operational decision or human confirmation; synthetic tests do not close it.
- **Original pass retained:** preserves the tester's result; does not claim that this revision has been retested on their phone.

## Original customer assessment — preserved

| Dimension | Original score /10 | Principal evidence and remediation target |
| --- | ---: | --- |
| Customer experience | 6.0 | Clean initial impression, smooth signup and relevant output; remove Help, navigation and scheduled-post dead ends. |
| Functionality and reliability | 5.0 | Caption/refinement/media/persistence worked; scheduling, Facebook, changed strategy and scanned voice did not. |
| Simplicity and unnecessary steps | 6.0 | Reduce repeated connection taps, plan clutter and forced app restarts. |
| Usability and accessibility | 7.0 | Keyboard, scrolling, larger text, dark mode, safe areas and touch targets passed; auth spacing needs correction. |
| Intuitiveness | 5.0 | Purpose took about seven minutes to become clear; simplify Studio wording and the next action after creating a strategy. |
| Visual design and branding | 7.0 | Clean, modern initial appearance; cramped authentication and busy planning screens reduced polish. |
| Commercial quality and likelihood of returning/paying | 5.0 | Useful captions, but weak scheduling control, Facebook failure and missing account deletion prevented confidence in paying. |
| **Workbook average** | **5.9** | **Original customer assessment, not a post-fix score.** |

No new customer scores are assigned. Code review and automated regression evidence cannot establish an 8/10 customer experience, payment intent or commercial readiness. Actual manual erasure operation/retention evidence, real Facebook verification and replacement-build device testing remain material constraints.

### First impressions to preserve and improve

- The product's purpose became clear **about seven minutes** after launch, after the first generated post. The first useful caption took **about 6.5 minutes**, including signup and connecting accounts. These are baseline observations, not new performance measurements.
- Positive findings: a clean, uncluttered first impression; smooth account creation; successful X connection; a relevant, well-written awareness caption. Preserve these rather than adding more onboarding screens.
- Hesitation points: signed-out Help, Instagram's professional-account requirement, repeated X taps, planning clutter and unclear drafting/thread terminology.
- The tester would return for captions, but would not yet trust scheduling or pay until scheduling control and Facebook connection work reliably.
- Remediation keeps a blank Studio workspace, explains the task in the composer, separates an immediate idea from an editable strategy, and gives scheduled work visible management actions. There is no duplicate welcome/recommendation block competing with Next Move.

## Evidence index

These paths identify relevant implementation and regression coverage. They are not claims that all tests have passed in the final release run.

| Key | Implementation and regression evidence |
| --- | --- |
| E1 — account and voice | `nova/account_deletion.py`, `nova/voice_memory.py`, owned account/voice handlers in `nova/app.py`, account/deletion templates, `account-sections.js`; `tests/test_account_qa_20261025.py`, `tests/account_voice_client.test.cjs`, `tests/test_ios_beta_handoff.py`. |
| E2 — Schedule | `nova/schedule_routes.py`, `nova/static/drafts.js`, `nova/static/schedule.css`, `nova/templates/drafts.html`; `tests/test_schedule_editing.py`, `tests/test_schedule_windows.py`, `tests/schedule_agenda.test.cjs`, `tests/test_reviewed_publication.py`. |
| E3 — strategy and Next Move | `nova/strategy.py`, strategy panel/JS/CSS, Account's canonical Strategy link; `tests/test_strategy_revision.py`, `tests/next_move_revision.test.cjs`, `tests/strategy_onboarding.test.cjs`, `tests/next_move_journey.test.cjs`. |
| E4 — native navigation and provider return | `ios/Zova/Core/NativeProtocol.swift`, `ios/Zova/StudioSurface.swift`, `ios/Zova/ZovaApp.swift`, `nova/mobile_shell.py`; native `NativeProtocolTests.swift` and `WebKitHandoffTests.swift`, `tests/test_social_native_return.py`, `tests/test_ios_beta_handoff.py`, `tests/mobile_connect_client.test.cjs`. |
| E5 — Help, auth and Studio clarity | Public Help and auth/recovery templates, `account-access.css`, mobile auth spacing, Studio placeholder/format wording and scheduled-state actions; `tests/test_media_export.py`, `tests/test_signup_recovery_ux.py`, `tests/test_studio_clarity_client.py`, `tests/studio_clarity_client.cjs`. |
| E6 — music and private export | `nova/instagram_audio.py`, separate encrypted audio grant in social connection lifecycle, reviewed audio payload, `nova/media_export.py`, music dialog/JS/CSS and workspace persistence; `tests/test_instagram_audio.py`, `tests/test_media_export.py`, `tests/instagram_music_client.test.cjs`. |
| E7 — preserved foundations | Existing account integrity, security, AI privacy, connection lifecycle, media inspection/availability, workspace persistence, Studio message-media, reviewed publication, Instagram formats, TikTok outcomes and operational recovery suites. The release owner must record the actual final selection/results. |

## All seven reported bugs

| ID / original severity | Original defect and evidence | Remediation and regression evidence | Current closure boundary |
| --- | --- | --- | --- |
| BUG-01 — Critical | No in-app account deletion; TC-50. No recording supplied. | Visible Account deletion action. Current password, session-bound short-lived confirmation proof and same-origin protections. Revokes web/mobile access, cancels unsent work across brands, invalidates unused approvals and returns an opaque status receipt. Publication confirmation rechecks active ownership before claiming a new send. E1 covers incorrect credentials/proof, foreign users, session revocation, unsent cancellation and preservation of uncertain outcomes. Public deletion instructions now match the actual flow. | **Manual beta workflow implemented; operational execution remains unverified.** The owner approved David with a seven-day target. Authenticated initiation is self-service; the receipt correctly remains pending until a verified operator executes the maintenance/drain, reconciliation and cleanup procedure. The private queue exposes target/overdue cases. The operator command reads committed cleanup and missing files before recording completion. See ACCOUNT_DELETION_RUNBOOK.md and deletion regression tests. No real account has been erased, automatic erasure/notification is not claimed, and retention/backup handling still needs case-specific operational evidence. |
| BUG-02 — Major | Scheduled post cannot be rescheduled, edited or cancelled; TC-43/44/45. [Recording](https://cap.so/s/7079r64t3nhx1sn), approximately 00:10–00:24: Open draft leads to a read-only Studio/result screen with no clear management action. | Schedule replaces the Drafts label; compact calendar/list and explicit Reschedule, Edit post and Cancel. Editing first atomically stops unsent destinations and requires fresh approval. Version checks prevent stale changes; a claimed/unknown attempt is not rewritten or resent. Exact publication references, owner/brand scope, corrupt records, rollback and worker-race cases covered in E2. Locked Studio provides a Schedule route and honest loading status. | **Implemented, retest pending.** Real device must change time, edit/review again and cancel. The tester warned that their original post may still be scheduled: its actual provider/job state and cleanup remain an **external check**, not implied by synthetic cancellation tests. |
| BUG-03 — Major | Facebook login does not complete; TC-33. [Recording](https://cap.so/s/kr36y1n40196gfw). | Native browser bridge and return handling hardened; connection remains bound to the initiating device, owner, brand and provider through final confirmation. E4 tests valid/cancelled returns and no premature connection. | **External check remains.** The recording includes a provider-controlled identity/Google step; it does not establish that every failure is a Zova callback defect. Complete Facebook authentication and Page selection with a real eligible account, then verify final confirmation and return. Do not bypass identity checks, claim a successful Facebook connection, or expand permissions based only on this code change. |
| BUG-04 — Major | Changing business goal from gym to restaurant leaves gym recommendations; TC-31. [Recording](https://cap.so/s/agrasjjnprae0rd), 00:28–00:52. | A replacement strategy is proposed from the latest description, not stale business context. Saving persists the description/structured strategy for the owner and brand, increments revision and replaces superseded open/snoozed recommendations while preserving existing drafts. Late model batches and client responses cannot attach to a newer strategy. E3 covers replacement context, brand isolation, revisions and stale responses. | **Implemented, retest pending.** Retest gym → restaurant, reload/reopen and recommendation → draft. Live AI usefulness/trend freshness still requires external assessment. |
| BUG-05 — Major | Cannot return to Drafts list after opening a draft; TC-46. [Recording](https://cap.so/s/29c8rd9fxab2z94). | Native internal navigation selects the corresponding tab instead of leaving Studio inside a stale Schedule tab; tab roots and unsaved navigation handling are explicit. Schedule naming is consistent across native/web navigation. E4 covers routing and WebKit handoff behavior. | **Implemented, retest pending.** On a replacement iPhone build, open an item, tap Schedule and open another without force-quitting. Check unsaved work survives navigation and prompts are not duplicated. |
| BUG-06 — Major | Scan says voice updated but fields remain empty; TC-48. [Recording](https://cap.so/s/kvrpqmggsep40za), approximately 00:05–00:19: fields remain empty while the saved timestamp changes. | API returns the actual saved preferences; client fills editable fields immediately, preserves edits typed during the scan, and reload reads the same stored values. Empty provider captions/failure do not announce success or erase guidance. Manual overrides, including intentional blanks, survive learning. Approved captions update bounded, consent-gated brand voice examples. E1 covers reload, cross-brand access, unusable model output and an AI response arriving after revocation. | **Implemented, retest pending.** Requires readable captions from a real provider to verify a live scan. A successful connection alone does not guarantee that provider returns historical caption content. |
| BUG-07 — Minor | Signed-out Help shows technical error. [Walkthrough](https://cap.so/s/ys5krhgynavb6aa), 00:08. | Help is readable while signed out; account-specific actions point to sign-in. Native response handling and public page tests cover the route. E5. | **Implemented, retest pending.** Verify Help from the signed-out replacement app; no raw JSON or forced sign-in is required to read basic help. |

## All five UX observations

| ID / original impact | Reported observation | Delivered change / evidence | Retest expectation |
| --- | --- | --- | --- |
| UX-01 — Low | Reset-password email field and action cramped. [Recording](https://cap.so/s/bae0c2h0s2wj77y). | Dedicated auth/recovery spacing and readable full-width controls, E5. | Reset from iPhone, keyboard open/closed and larger text; no touching controls or clipped error. |
| UX-02 — Low | Create-account and forgot-password links easy to mistap. Walkthrough 00:33. | Separated actions with adequate touch targets and consistent mobile auth styling, E5. | Each action responds independently; landscape/larger text remain usable. |
| UX-03 — Medium | X takes several taps and opens a separate window. Walkthrough 03:27. | Immediate native connection progress, duplicate-start protection and controlled browser/auth session return, E4. | A single tap shows progress; cancel and success return correctly. Provider authentication may still require its own screens; no promise of zero identity steps. |
| UX-04 — Medium | Planning screen cluttered; next action and Save plan unclear. Walkthrough 04:48. | Next Move gives one immediate action; Strategy is a separate description → concise proposal → explicit Save strategy journey. Editable saved strategy is linked from Account. E3. | New user can distinguish a one-off post suggestion from changing their ongoing strategy without survey-like questions. |
| UX-05 — Medium | Drafting wording and Single post / thread choices unclear. Walkthrough 05:27. | Composer explains that a description becomes a caption; X options use One post and Thread · 3/5 connected posts. Blank Studio avoids duplicate explanatory hero content. E5. | User understands how to start and what a thread creates without reading a help page. |

## All seven additional owner requests

| Owner request | Implementation | Evidence / remaining limit |
| --- | --- | --- |
| O1 — Turn Drafts into Schedule, with a succinct calendar/business view; edit work without duplication | Schedule is the primary label; drafts and upcoming destinations live in the same area. Calendar/list filtering, clear platform/status/time context and inline reschedule/edit/cancel actions. Locked Studio routes back to management. | E2/E4/E5. Timezone and DST validation retained. Calendar results are bounded and disclose truncation rather than pretending to show unlimited history. Existing delivery receipts remain immutable. Real-device calendar/edit/cancel retest required. |
| O2 — Save Next Move strategy with user profile | Strategy is stored server-side for the correct owner/brand, including source description and editable structured plan. Account links to the canonical editor; no second profile strategy form. | E3 isolation/reload/save tests. A one-off idea does not silently replace or create a strategy. |
| O3 — Make Next Move immediate, useful and reliable; separate next action from strategy | One recommendation at a time, direct draft action, separate Strategy editor; request/revision handling prevents late overwrite. Errors retain useful detail; unavailable live discovery can produce clearly labelled strategy-based evergreen suggestions. | E3. No assertion that a failed search is a live trend. Live relevance and latency need a fresh customer retest. |
| O4 — Replace strategy survey with description and examples; let AI build a saved, editable strategy | Brief free-text input with examples, concise editable proposal, explicit save and later reopen from Account/Next Move. Old business context is excluded when replacing the strategy. | E3, BUG-04. The short review is deliberate user control over persistent direction, not an automatic silent strategy change. |
| O5 — Save and refresh Your voice | Persist learned fields and explicit overrides; use recent approved captions as bounded examples with current AI consent. Editable preferences and visible remembered captions remain available; clear-memory action included. | E1. Learning does not overwrite explicit creator choices or claim unapproved/pending content was published. It is saved application context, not a promise of model training. |
| O6 — Choose Instagram music for posts and Stories where Instagram permits | Eligible **single-video Reels** can search/select licensed audio through Meta's Facebook-login Audio API, with a separate encrypted eligible User grant. Track/account/volumes are verified in the immutable review and rechecked before dispatch. Stories/photos offer private media export and caption copy to finish in Instagram. | E6. Existing direct Instagram primary credentials stay intact. Direct Instagram Login does not provide this audio API; an eligible Facebook grant may be required. No automatic music/sticker insertion for Stories/photos is claimed. No live licensed-audio publication was performed for this remediation. |
| O7 — Minimise steps, words and duplication | Blank Studio, clear composer task, consistent Schedule label, one Next Move recommendation, distinct Strategy journey, simple account rows and separate auth touch targets. | E1–E5. Preserve review/confirmation only where needed for publication, persistent strategy changes and deletion. Customer simplicity/intuitiveness scores require retesting; do not self-certify them. |

## Complete test-case traceability

Every original TC ID appears below. “Retest” means replacement build/device or provider evidence is still required, even when automated regression coverage exists. Original passing cases remain regression targets, not newly executed tester results.

### Onboarding — TC-01 to TC-09

| ID | Scenario | Original result | Remediation / regression evidence and closure |
| --- | --- | --- | --- |
| TC-01 | New email signup | Pass | Original pass retained. E5 auth layout; existing onboarding/account integrity tests. Retest replacement iPhone signup. |
| TC-02 | Signup validation | Pass | Original pass retained. Signup/recovery UX and security suites; preserve specific inline errors. |
| TC-03 | Email verification | Pass | Original pass retained. Existing recovery/verification and native return coverage; real delivered link/app return retest. |
| TC-04 | Onboarding flow | Pass | Original pass retained. E3/E5 simplify strategy start without forcing an added survey. |
| TC-05 | Logout | Pass | Original pass retained. E4 session/cookie revocation coverage; verify no account data after logout. |
| TC-06 | Login | Pass | Original pass retained. E5 spacing and existing native/account tests; old data must remain. |
| TC-07 | Wrong password | Pass | Original pass retained. Existing security/account tests and separated auth actions. |
| TC-08 | Password recovery | Pass | Functionality passed; UX-01 addressed in E5. Real mailbox/device retest remains distinct from mocked delivery. |
| TC-09 | Session survives force-quit | Pass | Original pass retained. E4; verify replacement binary and token restoration on device. |

### Studio and media — TC-10 to TC-22

| ID | Scenario | Original result | Remediation / regression evidence and closure |
| --- | --- | --- | --- |
| TC-10 | Generate caption | Pass | Original pass retained. E5 clear composer; existing AI response/conversation tests. Live output quality/latency retest. |
| TC-11 | Conversational refinement | Pass | Original pass retained. Existing conversation intent and Studio recovery suites. |
| TC-12 | Manual caption edit | Pass | Original pass retained. Existing workspace persistence and immutable review coverage; explicit voice overrides protected separately in E1. |
| TC-13 | Refine manual edit | Pass | Original pass retained. Existing conversation/workspace tests; verify AI uses latest text. |
| TC-14 | Long input, emoji, line breaks, other languages | Pass | Original pass retained. Existing bounded input/workspace checks; device text layout remains a retest. |
| TC-15 | Interrupted generation | Pass | Original pass retained. E3 stale response/error handling and existing AI recovery tests; airplane-mode retest. |
| TC-16 | Image upload | Pass | Original pass retained. Existing media inspection/availability/message-media suites; E6 private export adds a new regression target. |
| TC-17 | Video upload | Pass | Original pass retained. Existing upload/inspection suites; eligible Reel music and native export require additional E6/device checks. |
| TC-18 | Remove media | Pass | Original pass retained. Existing workspace/message-media tests; changing media must invalidate an incompatible music choice/review. |
| TC-19 | Multiple media | Pass | Original pass retained. Existing limits/order checks. E6 must reject licensed audio on anything other than one eligible Reel video. |
| TC-20 | AI recognises distinctive media | Pass | Original pass retained. Existing media-inspection tests. Video frames are inspected; audio understanding is not claimed. |
| TC-21 | Large or unsupported media | Pass | Original pass retained. Existing media validation/availability; no new support for unsupported formats is asserted. |
| TC-22 | Photos permission denied/allowed | Pass | Original pass retained. Native real-device retest required; server tests cannot prove Photos permission recovery. |

### Persistence and Next Move — TC-23 to TC-31

| ID | Scenario | Original result | Remediation / regression evidence and closure |
| --- | --- | --- | --- |
| TC-23 | Save caption/media/platforms | Pass | Original pass retained. Existing workspace tests plus E6 saved music selection validation. |
| TC-24 | Reopen saved draft after force-quit | Pass | Original pass retained. E4 navigation and E7 persistence; device retest includes media and music state. |
| TC-25 | Same draft on web and iPhone | Pass | Original pass retained. Shared server-owned workspace; verify newest edits on both clients. |
| TC-26 | Edit and resave without duplicates | Pass | Original pass retained. Revision checks, E2 scheduled edit and E7 persistence. |
| TC-27 | Delete draft | Pass | Original pass retained. Existing unsubmitted-draft deletion/confirmation checks; delivery history is not erased as a plain draft. |
| TC-28 | Add goal/strategy | Pass | E3 replaces survey-like input with a description/proposal/save journey; owner/brand persistence regression. Retest new path. |
| TC-29 | Relevant recommendations | Pass | E3 one immediate recommendation, source honesty and evergreen fallback. Relevance needs customer/live assessment. |
| TC-30 | Recommendation becomes draft | Pass | E3 idempotent idea-to-draft journey and saved context. Retest complete new flow in Studio. |
| TC-31 | Edit/remove goal | Fail — BUG-04 | E3 replacement context, strategy revisions and stale batch/response tests. Gym → restaurant and removal behavior require replacement-build retest. |

### Connections and publishing — TC-32 to TC-40

| ID | Scenario | Original result | Remediation / regression evidence and closure |
| --- | --- | --- | --- |
| TC-32 | Connect professional Instagram | Blocked | Tester lacked an eligible account. E4 protects return flow; cannot convert to pass. Retest with an authorised Business/Creator account, preserving working direct Instagram. |
| TC-33 | Connect Facebook Page | Fail — BUG-03 | E4 bridge/return regression coverage. Real provider identity step, Page selection, final connection and native return remain external. |
| TC-34 | Connect TikTok | Blocked | Tester location prevented TikTok use. Retest in a supported location with an authorised account. Workbook inbox-only note is historical, not definitive current capability evidence. |
| TC-35 | Cancel connection | Pass | Original pass retained. E4 provider/device-bound cancelled return tests; repeat for every supported platform on device. |
| TC-36 | Personal Instagram requirement | Pass | Original pass retained. [Walkthrough](https://cap.so/s/ys5krhgynavb6aa) 03:08 shows professional requirement. Preserve honest requirement; no promise of personal-account API publishing. |
| TC-37 | Disconnect account | Pass | Original pass retained. E1/E6 clear primary and additional audio credentials; existing connection lifecycle tests preserve drafts. |
| TC-38 | Final publishing review | Untested | E6/E7 check destination, immutable caption/media/settings/audio. Needs real reviewer/device walkthrough; not automatically a pass because endpoints are tested. No public posting required to inspect review. |
| TC-39 | Missing account or required media | Pass | Original pass retained. Existing reviewed publication/format checks plus E6 ineligible audio rejection. |
| TC-40 | Unconfirmed outcome | Pass | Original pass retained. E2/E7 preserve receipts and prevent automatic resend/edit of uncertain attempts. Confirm clear destination-check guidance. |

### Schedule, Account and Performance — TC-41 to TC-50

| ID | Scenario | Original result | Remediation / regression evidence and closure |
| --- | --- | --- | --- |
| TC-41 | Future schedule | Pass | Original pass retained. E2 calendar/local timezone, exact UTC review and immutable delivery handling. |
| TC-42 | Reject past time | Pass | Original pass retained. E2 time-window/DST validation; cannot schedule an invalid past instant. |
| TC-43 | Reschedule | Fail — BUG-02 | E2 time-only update, stale revision rejection, missing ledger protection and worker-race coverage. Device retest required. |
| TC-44 | Cancel schedule | Fail — BUG-02 | E2 exact unsent job/attempt cancellation, no cancellation of later/unknown attempt, rollback on competing claim. Device retest required. |
| TC-45 | No leftover scheduled tests | Blocked — BUG-02 | E2 makes cancellation available. **Actual original tester job cleanup is still unverified**; inspect its current state before any authorised cancellation, never resend. |
| TC-46 | Draft list navigation/clarity | Fail — BUG-05 | E2 calendar/list and E4 correct native tab navigation. Test Schedule → post → Schedule → another post without app restart. |
| TC-47 | Performance with/without accounts | Pass | Original pass retained. Existing analytics/performance suites; no new measured analytics capability claimed. |
| TC-48 | Account settings persist | Fail — BUG-06 | E1 persisted voice fields, DOM update, manual override protection, reload/brand/error tests. Live caption scan and device reopen retest. |
| TC-49 | Accurate account details | Pass | Original pass retained. E1 strategy link/voice display and existing account integrity tests. |
| TC-50 | In-app account deletion | Fail — BUG-01 | E1 authenticated self-service initiation/receipt now exists. **Partial** until operational erasure, deadline and verified completion process are established and tested. |

### Mobile behavior — TC-51 to TC-57

| ID | Scenario | Original result | Remediation / regression evidence and closure |
| --- | --- | --- | --- |
| TC-51 | Keyboard behavior | Pass | Original pass retained. E4/E5 plus new strategy/music forms require device keyboard-open testing. |
| TC-52 | Scrolling | Pass | Original pass retained. Calendar, account examples and music results introduce new bounded scroll areas; inspect on device. |
| TC-53 | Readability / Dynamic Type | Pass | Original pass retained. E5 spacing/contrast and compact Schedule/strategy views; actual larger-text retest required. |
| TC-54 | Touch targets | Pass | Original pass retained. E5 auth actions and E2 inline controls; verify new calendar/music buttons on device. |
| TC-55 | Dark mode | Pass | Original pass retained. Account/bridging pages retain dark treatment; Studio/Schedule/Performance retain the owner's clear light surfaces. Verify system appearance changes. |
| TC-56 | Orientation / safe areas | Pass | Original pass retained. E4/native layout tests support regression; notch, keyboard and home indicator need actual-device checks. |
| TC-57 | Interruptions / background | Pass | Original pass retained. E4 navigation/save handling and E7 persistence. Background/phone-call tests remain device-only evidence. |

## Capability matrix after implementation

| Capability | Web / shared backend | iOS consideration | Honest limit |
| --- | --- | --- | --- |
| Caption generation/refinement | Shared AI and draft APIs retained; clearer composer. | Same saved content and edit/review flow. | Live quality/latency not re-scored. |
| Schedule calendar and management | One Schedule area with drafts, time changes, edit and cancellation. | Native Schedule label and internal routing. | Active/unknown sends cannot be silently rewritten; retained history is intentional. |
| One-off Next Move | Immediate idea without silently changing a strategy. | Compact shared panel. | Search/model failures remain possible and must be honest. |
| Saved Strategy | Owner/brand persistence; description-based proposal and explicit save. | Reopen from Account; no duplicate editor. | Customer strategy quality requires retesting. |
| Voice | Stored profile, explicit overrides, consent-gated approved examples. | Same editable fields after scan/reload. | Provider may return no readable historical captions. |
| Account deletion | Self-service authenticated initiation, revoke/cancel, receipt. | Reachable inside app. | Final erasure and time-bounded operations still incomplete. |
| Instagram direct connection/publishing | Existing working primary flow preserved. | Bound provider return and final account confirmation. | Business/Creator eligibility; real replacement-build test still required. |
| Instagram licensed Reel audio | Conditional Facebook User grant, search, track/account verification, reviewed volumes. | Shared picker; native download fallback. | One video Reel only; no combined-audio preview; live provider test required. |
| Story/photo music | Private export/copy and finish in Instagram. | Native share/save support is part of the replacement build. | Manual destination-app step; not automatic Zova music publishing. |
| Facebook | Existing Page OAuth/publish path retained with return fixes. | Provider session returns to originating app attempt. | BUG-03 real connection retest remains outstanding. |
| X | Existing connection/publishing maintained; immediate progress and routing improvements. | Protected in-app authentication/session return. | Provider may require identity steps; no credentials or login bypass. |
| TikTok | Existing approved capability/configuration preserved. | Native connection/cancel journey retained. | Tester location blocked this case; verify actual grant/mode instead of relying on old workbook inbox-only wording. |
| Billing/hosting | Render retained; customer charges disabled. | No new purchase flow. | No cloud migration or paid commercial release claim. |

## Remaining release blockers and external evidence

1. **Account deletion operations:** define an owner-approved completion deadline, drain in-flight writers/sends safely, complete erasure/media/provider handling and verify the receipt transitions only after successful cleanup. Document retention and completion communication. Do not label initiation alone “account deleted.”
2. **Facebook:** repeat the recorded failure with a real eligible Page account, including provider-controlled identity steps, selection, final confirmation and native return. Preserve the working Instagram grant.
3. **Replacement iPhone build:** install the actual new TestFlight build and retest Schedule routing/edit/cancel, strategy replacement, voice fields/reload, signed-out Help, first-tap connection progress, unsaved navigation, media export/share, keyboard and safe areas. Record device, iOS and build.
4. **Provider cases blocked or untested by tester:** professional Instagram, TikTok in a supported location and full final review. Licensed Instagram audio needs a real eligible Facebook grant and separate review/publication evidence before claiming end-to-end live support.
5. **Original scheduled test cleanup:** determine whether the tester's job is still pending, completed or uncertain; reconcile before authorised cancellation. No automatic resend or unverified cleanup assertion.
6. **Credential exposure in public recording:** the supplied public tester material includes credential exposure. Do not reproduce values in docs, screenshots or logs. Owner/tester should rotate exposed credentials, revoke affected sessions where appropriate and remove/redact the public material; removal/rotation is not confirmed by this remediation.
7. **Customer reassessment:** ask the tester to rerun failed/blocked/untested cases and the changed journeys. Obtain fresh scores, time to first useful caption, understanding of Next Move versus Strategy, and confidence in Schedule. Original positives and original 5.9 average remain the baseline.

## Review iterations and visual evidence

1. Reproduced the reported failure patterns against code and all linked tester recordings; preserved original results and distinguished provider-controlled failures from application defects.
2. Implemented compatible changes and ran focused ownership, persistence, scheduling, native return, publishing and UI regressions.
3. Exercised a disposable browser account through reschedule, cancellation, pause-all-before-edit, caption edit/reload, strategy save/reload, pottery-to-restaurant replacement, voice edit/reload and private media download. External provider calls were blocked and the worker disabled. This found and fixed a transient old-idea flash between requests.
4. Rechecked mobile/desktop proportions. A final keyboard-height check found the Send control below the visible area with all platforms selected; the conflicting height limits were replaced with one visual-viewport budget. Browser checks now pass at 390×844, 390×500, 390×350 and a 350px visual viewport inside an 844px layout viewport. Text and Send stay fully reachable, including long input, attachments and all platforms. Format controls remain accessible, and ordinary-height controls are not clipped. This regression runs in CI.
5. First exact-candidate CI passed 652 SQLite tests (2 skipped) and 653 PostgreSQL tests (1 skipped), synthetic PostgreSQL recovery, image smoke and actual-image dependency audit (no known findings). A client assertion assumed UK date order; CI's US locale exposed it. The assertion now checks the actual focused day/month without imposing the operating system's presentation order. A fresh full candidate run remains required.

Synthetic browser screenshots, not production/customer or iPhone acceptance:

- [Schedule on desktop](evidence/20261025/schedule-desktop.png) and [rescheduled post on mobile](evidence/20261025/schedule-rescheduled-mobile.png).
- [Editing a previously scheduled post](evidence/20261025/edited-scheduled-post-mobile.png).
- [Concise strategy proposal](evidence/20261025/strategy-proposal-mobile.png) and [replacement restaurant recommendation](evidence/20261025/restaurant-next-move-mobile.png).
- [Account rows](evidence/20261025/account-mobile.png) and [public Help](evidence/20261025/help-mobile.png).

Music capability was checked against Meta's [Audio API documentation](https://developers.facebook.com/docs/instagram-platform/content-publishing/audio-api/). Its eligible Facebook-login Reel path is separate from the manual photo/Story finish flow. A documented API and synthetic payload tests are not proof that the production account has an eligible grant or that a licensed track was delivered.

Deletion receipts now appear in a paginated operations-only queue, with pending counts in health status. The monitor credential cannot read case receipts. This gives an operator visibility; it does not send a notification or complete erasure automatically.

## Final release verification

Final application/native CI results and candidate identity are recorded here after the last layout iteration. No production deployment or new TestFlight build has been performed in this remediation. The existing approved build remains 0.1.0 (10); it does not contain these native changes. Customer charges and the paid monitor remain disabled, and hosting remains on Render.

Native validation at `bf6cc07`: [macOS/iPhone CI](https://github.com/davidwilson92-cpu/DataMaxxing/actions/runs/40177228592) passed **20 unit/WebKit tests and one UI test**, plus iPhone release compilation. The subsequent viewport and locale fixes do not change `ios/`; this is simulator/build evidence, not a signed TestFlight release or actual social login acceptance.

Additional visual evidence: [short viewport Studio](evidence/20261025/studio-short-viewport.png), [full-height composer](evidence/20261025/layout-844-plain.png), [short viewport with attachment](evidence/20261025/layout-350-attachments.png), and [Instagram manual music finish](evidence/20261025/instagram-finish-mobile.png).

### Exact candidate application result

Code candidate **`1a77f43bbd07cb44de41364a3b3b2b127f6c4af6`** passed the [push validation](https://github.com/davidwilson92-cpu/DataMaxxing/actions/runs/40177854317) and [PR validation](https://github.com/davidwilson92-cpu/DataMaxxing/actions/runs/40177859348):

- SQLite: **652 passed, 2 platform-specific skips**. PostgreSQL: **653 passed, 1 platform-specific skip**. The SQLite run skips PostgreSQL advisory-lock and migration tests; the PostgreSQL run skips the SQLite backup test and instead runs its own dump/restore.
- Client checks: **29 passing tests/groups**, plus the separate Studio clarity script and real-browser mobile viewport regression.
- Synthetic PostgreSQL recovery verifies passwords, encrypted credentials, sessions/revocation, unknown publication preservation, AI choice and media.
- Built hosting image smoke checks and exact beta-scope gate passed.
- Fresh test-environment and actual-hosting-image dependency audits: **zero known findings**. This is a package audit, not an assertion that the application has no security risks.

No real post, provider permission, customer deletion, subscription charge, paid monitor or hosting migration was performed. No deployed server or signed TestFlight build contains this candidate yet. A new native build must be signed/uploaded before the tester can verify the tab and export changes.

### Next acceptance run

Use the replacement TestFlight build and record its number, iPhone model and iOS version. Prioritise:

1. Schedule → post → Schedule → another post, reschedule, edit with fresh approval, then cancel. Inspect the original tester job before any authorised cleanup; never replay an unknown result.
2. Replace the saved business strategy, fully reopen, then generate a relevant post from Next Move. Separately request a one-off idea without changing the saved strategy.
3. Scan real readable captions, verify voice fields immediately and after reopening, then edit/clear them and check those choices remain.
4. One-tap Facebook connection through eligible Page selection and final Zova confirmation, then automatic app return. Repeat cancellation for all providers.
5. Keyboard-open Studio with multiple selected platforms and an attachment; text, Send and format choices must remain reachable. Verify media export/share and logout during an export.
6. Eligible Reel audio search/selection and final review; separately follow the clearly manual Story/photo path. Do not perform a live publication without explicit approval.
7. Public Help and recovery targets while signed out. Validate deletion completion only after an operator/deadline and reconciled erasure process are established.

Request fresh usability scores and time-to-first-useful-caption. Retain the original assessment until real retesting supplies new evidence.

Final native PR run on the same code candidate **1a77f43** also passed: [iOS validation 40177859386](https://github.com/davidwilson92-cpu/DataMaxxing/actions/runs/40177859386), **20 unit/WebKit tests, one UI test and iPhone release compilation**. All mandatory application and native checks for this runtime candidate are green. Any following documentation-only commit does not change the validated runtime, native source or exact-scope manifest.

Rollback remains separate for server and native: retain current data/uploads/keys, the new additive voice/audio columns, encrypted credentials and immutable publication history. Revert application behavior without restoring stale database snapshots; do not replay or reset an uncertain provider outcome. The previous verified live server `bcd260e` and approved TestFlight build 10 remain the recorded live baseline, not deployments of this candidate.


## Owner-authorised publication preparation — 25 October

The owner explicitly requested publication and approved David as the deletion operator with a seven-day target. This authorises shipping the workflow, not deleting a real customer account. The restricted manual runbook and durable receipt make that process actionable; daily queue checks remain David's responsibility because the paid monitor stays inactive.

A fresh pre-release read at 14:34 UTC confirms live server bcd260e, PostgreSQL/schema ready, embedded worker idle, no overdue or stuck publications/mail, and billing/checkout/enforcement off. The historical unknown Instagram outcome remains. The 108 unpriced AI calls are missing cost evidence, not zero cost. An apparent 18 AI failures was reproduced as a counting defect: aggregate rows are 18 `success` and 41 `returned`; the status query wrongly treated `success` as failure. A regression is being added without rewriting those historical records.

Render completed a fresh managed database export dated 25 October 14:36 UTC; it remains in Render. Its three-day point-in-time recovery window was observed. No restore or credential change was performed. Screenshot: evidence/20261025/render-pre-release-backup.png.

The existing Codemagic signing workflow started at 14:36 UTC on fully validated source 43f4f47, build ID 6ade13d14a72334e32e50660, workflow counter10. Native files are unchanged by the subsequent server-only deletion operations work. Upload/Apple distribution and final server deployment must be verified separately below before claiming delivery.


## Published release and verification — 25 October, 14:54 UTC

This section supersedes the earlier candidate/preparation status above. It does
not replace the tester's original case outcomes or scores.

- **Web deployed:** exact `d15f619d30e430d1405164a8a58c08ea89d0ab17`, Render
  `dep-dbf1ef67bikc73bra6b0`, 14:50:36 UTC start, 57.9s, Live. Auto-deploy remains
  off; no main merge or AWS migration. [Render proof](evidence/20261025/render-live-d15f619.png).
- **CI:** [push](https://github.com/davidwilson92-cpu/DataMaxxing/actions/runs/40203790190)
  and [PR](https://github.com/davidwilson92-cpu/DataMaxxing/actions/runs/40203795510)
  passed 675 SQLite / 676 PostgreSQL tests (2 / 1 database-specific skips), 29 client
  tests/groups, Studio and real-browser viewport checks, synthetic backup recovery,
  actual-image package audit and smoke, exact beta scope. No known package findings;
  not a claim that the app has no security risk.
- **Review iteration:** earlier ccf0f69 full CI failed because new deletion tests
  inherited a publishing heartbeat and leaked synthetic jobs into later tests.
  d15f619 isolates/restores test state; production drain and reconciliation checks
  remain intact. Local functional rerun passed 671 with two skips, followed by the
  complete manifest-inclusive CI above. Prior failures are not hidden or waived.
- **Native:** [final native CI](https://github.com/davidwilson92-cpu/DataMaxxing/actions/runs/40203795378)
  passed. Signed build 11 uses previously fully validated 43f4f47; its native source
  and signing workflow are identical to d15f619. Codemagic 6ade13d14a72334e32e50660
  uploaded 0.1.0 (11), Apple receipt 45dbc386-8d7c-4163-be3a-02e6b4f9d91e.
  Both existing tester groups assigned; external status **Testing** after review
  submission, automatic notification enabled. Build 10 preserved. Public link
  https://testflight.apple.com/join/BxawFPCu remains capped at ten testers.
  [Apple proof](evidence/20261025/testflight-11-external-testing.png).
- **Live readback:** exact server SHA, database/schema ready, worker embedded/idle,
  billing off, checkout/enforcement false, account-erasure maintenance false.
  Public health/login/Help returned 200. Existing signed-in session still works;
  Studio, calendar, Account rows, separate Strategy description and immediate
  Next Move entry loaded without changing customer content.
  [Live calendar](evidence/20261025/schedule-live-20261025.png).
- **Preservation:** pre/post counts identical: 19 users, 46 drafts, 21 connections,
  29 media references, ten publications, one schedule. All 25 previously available
  files remain; four historical missing references unchanged. Seventeen encrypted
  access/refresh values remain decryptable, aggregate ciphertext digest unchanged
  (`826033052d31b01c190f985806bc6ce8d728472218a0b20d41d6719092d094fe`).
- **Operations:** no pending/overdue deletions; zero stuck/overdue jobs or mail
  failures. AI failure count now correctly zero. One historical unknown publication
  and 108 unpriced AI calls remain, so the overall operations status still says
  attention. No reset/resend or invented zero-cost claim. Fresh database export
  completed 14:36 UTC with three-day PITR available.
- **Deletion decision:** David is the manual operator, seven-day target, daily
  queue review. Runbook and guarded operator enforce actual maintenance/drain,
  provider/billing/retention reconciliation and post-cleanup verification before
  receipt completion. No real customer account was erased during this release.

Still requiring real acceptance: install build 11 and rerun changed phone journeys;
Facebook Page connection/confirmation/app return; eligible Instagram audio grant
and delivery; original tester schedule reconciliation; exposed test-credential
rotation/redaction; customer reassessment. Original 57 cases and 5.9 score remain
baseline. All 79 wider findings remain tracked. Customer charges and paid monitor
remain disabled. This is a released limited beta, not commercial certification.
