# Native build 12 review against the original tester workbook

Follow-up work is recorded in [NATIVE_QA_FIXES_20261027.md](NATIVE_QA_FIXES_20261027.md).
The audit below preserves the build-12 findings before those subsequent fixes.

Reviewed 27 October 2026. This audits native iOS **0.1.0 (12)** against the original tracker. It does not claim every original scenario was rerun on a phone.

## Decision

**Do not mark the entire tracker closed.** Six reported defect fixes have implementation and relevant passing automated evidence in build 12. Facebook's original connection failure still needs a real native connection retest. In-app deletion initiation works, but completed operational erasure is not established. Voice scanning reloads saved fields, but a real connected account must still demonstrate populated results on the phone.

One original UX request remains incomplete: the X selector does not explain a thread. Some new native controls specify dimensions below the original approximately 44-point target. Larger text and complete product-screen orientation coverage cannot inherit the tester's old passes.

No runtime, production data, social connections, billing or release settings changed during this audit. Build 12 remains externally approved but held at the owner's request. Existing external testers still have build 11: their results must not be treated as native-build-12 results.

## Original source and scope

Original workbook, read without alteration:

`C:/Users/david/.codex/codex-remote-attachments/01a09c9f-6976-7670-9008-0476ec90615d/8B597B37-548C-42B9-AA48-3674C51D8B40/1-Zova-2520Social-2520QA-2520Tracker.xlsx`

SHA-256: `6b30a970d8f6a1879976e5e9de3616784d5e39beb1956d690d702db3ff794d42`.

All seven sheets were read: Read Me, Test Cases, Bugs, UX Observations, First Impressions, Scorecard and Summary. **57 actual cases, seven populated bugs and five populated UX observations**; example and empty placeholder rows excluded. Tester: iPhone 16; iOS version and TestFlight build were blank. Historical recordings were not replayed in this audit; the workbook and previous remediation record supply their written findings.

Original results remain **46 Pass, 7 Fail, 3 Blocked, 1 Untested**. Original 82.14% is 46/56, including blocked cases in the denominator. It is not a new pass rate. Original average **5.9/10** is preserved; no replacement customer score is inferred from tests.

Runtime reviewed: `2de31e19401367d909cb320986122b28093fdeb6`. No current differences from that candidate in `ios/`, `nova/` or `tests/`. Later documentation commits do not alter build 12.

## Evidence and limits

| Key | Evidence | Boundary |
| --- | --- | --- |
| A | Fresh focused run: **164 passed**, two dependency deprecation warnings, 204.88 seconds. | Disposable data and synthetic external responses. Covers account/voice/deletion, schedules, strategy/Next Move, native presentation, provider returns, native handoff, recovery presentation, Help/export, message/media and reviewed publication. Not real provider publication. |
| B | Exact-source [native CI40565819691](https://github.com/davidwilson92-cpu/DataMaxxing/actions/runs/40565819691): **39 unit tests, 10 UI tests, iPhone Release compilation passed**. | Existing evidence for source inside build 12, not a new simulator run. UI journeys use fixtures. |
| C | Exact-source [application CI40565819642](https://github.com/davidwilson92-cpu/DataMaxxing/actions/runs/40565819642): **727 SQLite / 728 PostgreSQL tests** plus required browser/recovery/audit/beta checks passed. | Broader pre-release evidence. Backend passing does not establish a native UI journey. |
| D | Simulator captures from B; this audit re-inspected Studio, Next Move and Schedule. | Normal-size presentation, not fresh iPhone 16/larger-text/all-screen landscape coverage. Other prior captures are recorded in NATIVE_IOS_PARITY_20261027.md. |
| E | Owner answered Yes to build-12 upgrade, Studio opening, retained attachments, photo/video idea saving/reopening and social cancellation. | Exact owner-reported smoke checks only; not every provider's successful connection or live publication. |
| F | Fresh unsigned production GET /help: HTTP 200, HTML, not raw error JSON. | Signed-out Help route currently works. No account/data mutation. |

Fresh test command:

```powershell
.\.venv\Scripts\python.exe -m pytest -q `
  tests/test_account_qa_20261025.py tests/test_schedule_editing.py `
  tests/test_strategy_revision.py tests/test_next_move_intelligence.py `
  tests/test_native_presentation.py tests/test_social_native_return.py `
  tests/test_ios_beta_handoff.py tests/test_signup_recovery_ux.py `
  tests/test_media_export.py tests/test_studio_message_media.py `
  tests/test_reviewed_publication.py `
  --junitxml=.validation-tmp-native/qa-review/qa-regressions.xml
```

Warnings concern Starlette's deprecated httpx TestClient integration and AnyIO BlockingPortal alias; no failures. Local XML and read-only workbook extraction are under `.validation-tmp-native/qa-review/`.

## All seven reported defects

| ID | Implementation and verification | Closure assessment |
| --- | --- | --- |
| BUG-01 — no account deletion | NativeAccountView exposes Delete account. NativeDeletionView obtains a session-bound proof, requires current password plus DELETE, and calls the existing authenticated handler. A covers proof/ownership/revocation, cancelling unsent work and preserving uncertain deliveries. | **Missing-control defect corrected; operational closure open.** This initiates deletion and signs out. David's manual seven-day process and verified completion/receipt still need an actual exercise; initiation is not completed erasure. |
| BUG-02 — cannot reschedule/edit/cancel | NativeScheduleListing exposes Manage schedule. NativeScheduleView has date picker/reschedule, explicit cancel, and edit-to-Studio. Edit stops eligible unsent deliveries and requires fresh review. A changes the actual time and checks stale/foreign/claimed/unknown cases; B opens/saves/cancels a synthetic schedule. | **Fix retained and tested.** The UI Save-new-time test itself does not move the picker; the backend test establishes an actual time change. Phone edit/reschedule/cancel acceptance and the original specific leftover job (TC-45) remain distinct. |
| BUG-03 — Facebook login fails | NativeProductRoot uses the bound handoff/system authentication sheet, reloads account state and handles cancellation/no-Page/failure. NativeSignIn and A/B preserve state/callback/owner/brand/return controls. | **Not independently closed.** Previous connected-Page evidence and generic cancellation do not reproduce this tester's failed login on build 12. Need eligible login, Page selection, final confirmation and return. Preserve the working Instagram grant. |
| BUG-04 — gym survives restaurant strategy | NativeNextMoveView proposes from current description/direction, saves with a revision and replaces visible ideas. A excludes old business from the new model input, persists the new strategy and rejects stale handoff. B edits/reopens strategy and opens an idea. | **Fix retained and tested.** Correct context/state plumbing, not guaranteed relevance of every live AI response. |
| BUG-05 — cannot return to Drafts | Native Schedule has independent navigation. Opening a saved post selects Studio; Schedule returns to its own list/calendar without a web redirect. B covers tab changes/management; D shows the list/calendar. | **Fix retained.** No forced restart in the navigation path. Exact two-draft phone sequence remains a customer acceptance check. |
| BUG-06 — scan says updated but empty field | NativeAccountView awaits scan, reloads account and calls fillVoice on actual saved fields. A covers persistence/reload, explicit overrides, empty/failure, consent, brand and revoked account cases. | **Handler/backend fix retained; live scan acceptance open.** Native UI fixtures do not run this scan. Check real readable captions populate fields and survive reopening; no usable captions must give an honest empty result. |
| BUG-07 — signed-out Help error | Native welcome Help opens public /help. A tests the public page; F confirms live HTML without login. | **Fix retained and live public route checked.** Native route is present; authenticated session not required. |

## All five UX observations

| ID | Assessment |
| --- | --- |
| UX-01 — cramped recovery | **Fix retained.** Shared auth/recovery CSS has explicit spacing and 48px input/button minimums. System authentication intentionally still uses those pages. A/C cover forms; no fresh Safari larger-text capture. |
| UX-02 — cramped signup/recovery links | **Fix retained.** Shared auth alternatives separated vertically by 12px with 44px minimum targets. Separate from new native touch-target findings under TC-54. |
| UX-03 — repeated X taps / external window | **Mechanism corrected.** First tap enters serialized busy operation and ASWebAuthenticationSession. A/B and E cover return/cancellation. Real X success on build 12 remains a provider check. Minor copy issue: Account says “Saving…” during connection. |
| UX-04 — busy Next Move / unclear saving | **Simplification retained.** One proposal, purple AI recommendation, primary action and separate Your strategy with two inputs. Explicit save persists strategy; one-off ideas do not silently replace it. A/B/D; no new customer score. |
| UX-05 — drafting / thread unclear | **Partial.** Composer explains caption drafting. X says “One post”, “Thread · 3 posts”, “Thread · 5 posts”; neither selector nor Guide explains connected posts. Requested short format explanation is still missing. |

## All 57 original test cases

“Retained” means implementation and cited evidence remain present, not a fresh physical-device Pass. Original statuses remain unchanged.

| Case | Scenario | Original | Native assessment / boundary |
| --- | --- | --- | --- |
| TC-01 | Sign up | Pass | Shared signup through system authentication retained (A/B/C). Fresh native-sheet account creation not repeated. |
| TC-02 | Signup validation | Pass | Server validation and preservation of non-secret inputs retained (A/C). Not a new device test. |
| TC-03 | Email verification | Pass | Shared verification/native handoff retained (A/C). Fresh email-link-to-app journey remains a device check. |
| TC-04 | Onboarding | Pass | Native short, skippable introduction; seen/skip state tested (B). Welcome explains the AI social media manager. |
| TC-05 | Logout | Pass | Credentials, presentation and owned local recovery/media cleared; late responses cannot restore another account (B). |
| TC-06 | Login | Pass | Bound authentication/Keychain flow retained (A/B). Owner opened Studio on build 12 (E), not an exhaustive fresh-login test. |
| TC-07 | Wrong password | Pass | Shared credential validation retained (C). No live wrong-password attempt made. |
| TC-08 | Recovery | Pass | Shared reset/revocation and spaced recovery form retained (A/C). Prior owner reset evidence is historical, not a fresh exercise. |
| TC-09 | Session persistence | Pass | Keychain/refresh isolation retained (B); owner upgrade/reopen supports continuity (E). All expiry/cold-start cases not rechecked. |
| TC-10 | Generate caption | Pass | Native Send-to-caption journey passes (B); shared ownership/consent/revision checks (A). Live AI quality/latency not remeasured. |
| TC-11 | Conversational refinement | Pass | Native refinement/history uses existing conversation API; media stays with the post without repeating per message (A/B). Live model adherence unscored. |
| TC-12 | Manual edit | Pass | Caption editor, autosave serialization and final-review journey covered (B); native/web persistence covered (A). |
| TC-13 | Refine after manual edit | Pass | Current draft saved before subsequent actions; revision/serialization and shared payload coverage (A/B/C). No new live AI comparison. |
| TC-14 | Long text / emoji | Pass | Native text model and server limits retained (B/C). All long-text native layouts still need device coverage. |
| TC-15 | Generation failure | Pass | Recoverable input retained; failed/late save cannot silently lose a send (A/B). Physical slow/offline journey remains to check. |
| TC-16 | Photos image | Pass | Photos selection, HEIC conversion and protected upload path (B); owner confirms photo save/reopen (E). All orientations not rechecked. |
| TC-17 | Video | Pass | File-backed upload/preview and owner video save/reopen (B/E). Busy indicator is visible; no byte/percentage progress in current native UI. |
| TC-18 | Remove media | Pass | Removal updates draft/media settings; attachment state covered (A/B). No real media removed. |
| TC-19 | Multiple media | Pass | Ordered media and one-video-or-images limits retained; mixed media/limits covered (B/C). Device multi-selection acceptance remains. |
| TC-20 | AI reflects media | Pass | Media reaches shared multimodal request (A/C). Live caption accuracy still requires qualitative checking; fixtures cannot establish it. |
| TC-21 | Large / unsupported file | Pass | Native size/type guards, HEIC conversion and server inspection retained (B/C); oversize photo rejection covered. |
| TC-22 | Permissions | Pass | PhotosPicker uses selected-item access; camera denial offers Settings recovery. Deny/regrant/capture not established by owner smoke check. |
| TC-23 | Save draft | Pass | Autosave/revision/status handling retained (A/B); owner confirms media idea saves (E). |
| TC-24 | Close/reopen persistence | Pass | Owner confirms existing drafts/attachments and new media idea reopening (E); save/recovery protections covered (A/B). |
| TC-25 | Cross-device persistence | Pass | Native edits are read as the same saved web data (A). No simultaneous two-device live check performed. |
| TC-26 | Edit/resave | Pass | Expected revisions, save/send serialization and recovery guard stale overwrites (A/B). |
| TC-27 | Delete draft | Pass | Native destructive confirmation and owned endpoint retained (C). No real draft deleted during audit. |
| TC-28 | Save strategy | Pass | Native propose/save/reopen flow and shared owner/brand persistence tested (A/B). |
| TC-29 | Recommendations | Pass | Saved strategy, voice, available performance and upcoming work underpin request (A). Live relevance still needs qualitative review. |
| TC-30 | Idea to draft | Pass | Native handoff opens saved draft in Studio (B); stale strategy handoff rejected (A). |
| TC-31 | Replace goal | Fail | BUG-04 fix retained (A/B): old gym context excluded from new restaurant strategy/model input; stale ideas invalidated. |
| TC-32 | Professional Instagram | Blocked | Eligibility/return/presentation retained (A/B). Historical owner success and generic build-12 cancellation are not a fresh successful connection. |
| TC-33 | Facebook Page | Fail | BUG-03 remains a live provider check: eligible login, Page selection, final Zova confirmation and native return. |
| TC-34 | TikTok | Blocked | Consent/review/return covered (A/B); tester's regional restriction remains a coverage gap. Old inbox-only expectation is obsolete after approved Direct Post. |
| TC-35 | Cancel connection | Pass | Cancellation/state recovery covered (A/B) and owner (E). Owner did not identify each of the four providers separately. |
| TC-36 | Personal Instagram | Pass | Business/Creator guidance and shared eligibility checks retained (A/C); provider requirements not bypassed. |
| TC-37 | Disconnect | Pass | Native confirmation and owned unlink reload account state; shared lifecycle tests (C). No real connection unlinked. |
| TC-38 | Final publish review | Untested | Now has synthetic native UI evidence (B): destination/caption/media review, cancellation and TikTok fresh consent. Immutable approval/duplicate guards (A). No live post. |
| TC-39 | Missing requirements | Pass | Shared preflight and native review blockers/consent requirements retained (A/B/C). |
| TC-40 | Unconfirmed outcome | Pass | Native result presentation and duplicate/unknown-outcome protections retained (A/B/C). Existing unknown record not altered or declared resolved. |
| TC-41 | Future schedule | Pass | Native reviewed date/timezone conversion and shared immutable scheduling retained (A/B/C). No real scheduled provider delivery performed. |
| TC-42 | Past date | Pass | Server scheduling-window validation remains authoritative (C); native requests do not bypass it. |
| TC-43 | Reschedule | Fail | BUG-02 fix retained: backend test changes actual timestamp/stale checks (A); native management opens/saves (B). Phone picker-change acceptance remains. |
| TC-44 | Cancel schedule | Fail | BUG-02 fix retained: explicit native confirmation/synthetic cancellation (B), exact attempt/worker/unknown guards (A). |
| TC-45 | Original job cleanup | Blocked | Not conclusively closed. Prior aggregate showed no active deliveries but did not identify the original tester's job. Do not resend or cancel unrelated work. |
| TC-46 | Return to list | Fail | BUG-05 corrected with independent Schedule navigation (B/D). Exact Schedule → post → Schedule → another-post phone retest remains. |
| TC-47 | Performance | Pass | Empty states, provider messages, date filters and missing-vs-zero retained (B/C). No new real-metric accuracy measurement. |
| TC-48 | Voice/settings | Fail | BUG-06 saved-field/reload fix retained (A); native handler fills fields. Real caption scan and reopening on phone still needed. |
| TC-49 | Account details | Pass | Uses owned current account/brand data with no ID placeholder; ownership/cross-brand tests (A). Personal details not changed. |
| TC-50 | Account deletion | Fail | In-app proof/password/confirmation initiation exists and is tested (A). Completed manual erasure remains an operational check (BUG-01). |
| TC-51 | Keyboard | Pass | Typing/caption-save/review journeys and screenshots (B); earlier autosave keyboard interruption corrected. Other forms/device sizes need coverage. |
| TC-52 | Scrolling | Pass | Normal-size journeys/screenshots (B/D); no frame-rate or complete long-list/keyboard stress test. No new physical Pass assigned. |
| TC-53 | Larger text | Pass | Needs correction/validation before inheriting Pass: several labels use fixed point sizes, including small calendar text; no Dynamic Type screen test. |
| TC-54 | Touch targets | Pass | New native gap: brand selector minimum 30pt high; Your posts 44×34pt; calendar arrows/refresh 38×44pt. Guaranteed ~44pt hit areas need review. |
| TC-55 | Dark mode | Pass | Dark Account/entry and owner's light Studio/Schedule/Performance retained. Complete system appearance switching needs device coverage. |
| TC-56 | Orientation / safe areas | Pass | Portrait product and landscape launch covered (B/D), not full product landscape/larger text/keyboard. Blanket Pass cannot be inherited. |
| TC-57 | Interruptions | Pass | Background save, protected recovery, media pausing and owner reopen supported (B/E). Calls/process termination during upload/prolonged offline need physical checks. |

## Specific native follow-ups

- **UX-05:** add a short explanation of one post versus connected posts; no extra flow.
- **TC-54:** NativeStudioView brand selector has 30pt minimum height and Your posts has a 44×34pt frame. NativeScheduleListing month arrows and refresh use 38×44pt. These explicit dimensions undershoot the tester's ~44pt target. Framework hit regions were not measured; guarantee sufficient touch areas and retest.
- **TC-53/56:** NativeNextMoveView uses fixed 25/14/9pt text; calendar uses 11/10/9pt labels; Studio footer uses 10pt. Fixed sizes do not establish correct Dynamic Type behaviour. No full product large-text/landscape UI test exists. Validate before inheriting original passes.
- Account progress text “Saving…” during social sign-in could be clearer. This is copy polish, not evidence that the connection itself fails.
- No claim of closed real Facebook failure, live populated voice scan, exact original job cleanup or completed operational erasure.

## First impressions and scorecard follow-through

| Original finding | Current response and limit |
| --- | --- |
| Purpose took about seven minutes to understand | Welcome names the AI social media manager and caption/content-plan purpose. Short first-use steps are skippable; Guide is separate. No new person's comprehension time measured. |
| First useful caption took about 6.5 minutes | Blank Studio, direct composer and optional onboarding reduce compulsory steps. No new timed result or claimed percentage improvement. |
| Clean appearance / relevant captions were positives | Uncluttered Studio and brand treatment retained. Live creative quality still needs creator assessment. |
| Would return for captions, not trust scheduling or pay yet | Schedule controls now exist with passing regressions. Facebook verification, deletion operations and commercial assurance remain separate. Customer charges stay off. |
| Top five improvements | Scheduling → BUG-02; deletion → BUG-01; connections → BUG-03/UX-03; navigation/context/voice → BUG-05/04/06; simpler wording → UX-04/05. All traced above, including incomplete items. |

Original scores stay: customer experience 6; functionality 5; simplicity 6;
usability/accessibility 7; intuitiveness 5; design/branding 7; commercial quality
5. Workbook average 5.9. This audit does not replace customer judgement with a
new numerical score.

## Closure plan

1. Complete the thread explanation and guaranteed native hit areas; validate larger text and product landscape. Those require a new validated binary, not a change to already signed build 12.
2. Verify Facebook's exact failed sequence and a populated real voice scan/reopen. Complete professional Instagram/TikTok native checks where original tester was blocked. Provider sign-in through the system browser is intentional.
3. Repeat exact Schedule edit/reschedule/cancel and two-draft navigation on a phone. Identify the original tester job before declaring its cleanup warning closed; never resend ambiguous work.
4. Exercise approved manual erasure with a suitable disposable account and verify receipt/completion/exceptions. Do not delete a customer's account just to fill this evidence gap.
5. Retest the released native build with device/iOS/build recorded. Preserve original results and add a new retest record.

This does not change the owner's external-release hold. All **79 historical
commercial findings** remain in the separate deferred register; this 57-case
tracker is not a substitute for the security and operational register.
