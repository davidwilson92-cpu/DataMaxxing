# Beta tester remediation — 30 October 2026

Status: candidate under validation, not a commercial-readiness certification. All 51 nonempty findings from the supplied workbook are mapped below. No source workbook was edited. The retained 79-section security/operations register remains in force.

## Workbook traceability

Implemented means code changed in this candidate; final automated evidence and real-device limits are recorded separately. Adapted means the underlying problem is addressed without contradicting the owner’s simplicity/security/free-beta requirements.

| ID | Source | Finding | Disposition and response |
|---|---|---|---|
| QA-01 | Onboarding and Auth Screens!2 | Suggestion: Display the 'Zova AI' text instead of OpenAI for branding purposes | **retained-security** — Zova branding retained; OpenAI remains accurately named in AI-sharing/privacy disclosures. Hiding the processor is not a valid branding fix. |
| QA-02 | Onboarding and Auth Screens!5 | Improve Visibility of the Legal Policies Section on the One View Screen | **implemented** — Native welcome legal links moved beside the main sign-in action. Large accessibility text may still require scrolling. |
| QA-03 | Onboarding and Auth Screens!6 | Suggestion: Improve Password Field and Button Layout on the Login Screen | **implemented** — Independent eye controls inside password fields; forgot-password below/right; prominent Create an account action. |
| QA-04 | Onboarding and Auth Screens!7 | Field Accepts Invalid Email Addresses Without a Valid Domain Extension | **implemented** — Complete domain validation in browser and existing server normalization. No restriction to .com. |
| QA-05 | Onboarding and Auth Screens!8 | Login Confirmation Prompt Appears on Every Login Attempt | **retained-security** — Keep iOS system authentication consent and account-bound confirmation; these protect account switching and secure return. No unsafe auto-accept. |
| QA-06 | Onboarding and Auth Screens!11 | Implement Strong Password Validation with a Visible Requirements Checklist | **adapted** — Visible live length/match checklist; retain the server 10–256-character policy rather than weakening to eight or forcing arbitrary character classes. |
| QA-07 | Onboarding and Auth Screens!12 | Suggestion: Instead of the 'Show' password button, use the eye toggle button within the Password field | **implemented** — Separate eye controls for password and confirmation. |
| QA-08 | Onboarding and Auth Screens!13 | Suggestion: Align the Country Field Color with the App Theme | **implemented** — Country select matches the dark authentication theme. |
| QA-09 | Onboarding and Auth Screens!14 | Email Verification Flow Is Missing | **adapted** — Registration queues a hashed, time-limited verification link; Account offers resend. Verification remains optional for existing beta access; a mail outage never invalidates registration. |
| QA-10 | Onboarding and Auth Screens!15 | Incomplete Onboarding Steps Are Skipped After Logging Back In | **adapted** — Unfinished first-run native guide resumes its step; Skip completes it. Optional social/voice setup stays in Account. No subscription gate or required plan-selection during free beta. |
| QA-11 | Onboarding and Auth Screens!17 | The Forgot password screen theme should match with the app theme | **implemented** — Recovery pages now use the dark branded form treatment. |
| QA-12 | Onboarding and Auth Screens!18 | Implement Strong Password Validation with a Visible Requirements Checklist on Forgot Password screen as well | **adapted** — Recovery checklist matches the real 10–256-character server policy and confirmation requirement. |
| QA-13 | Onboarding and Auth Screens!19 | The password view and hide toggle button is missing on the new password setup screen | **implemented** — New-password and confirmation visibility controls on recovery. |
| QA-14 | Studio Screen!2 | Add a button to reset the AI-chat | **existing-verified** — Existing + New post saves previous work before starting a blank chat; no duplicate Reset action. |
| QA-15 | Studio Screen!3 | The chat with the AI get disappear by closing and re-opening the app | **implemented** — Restore the last server draft separately for each user/brand; protected unsaved recovery takes precedence. New post deliberately clears the resume pointer. |
| QA-16 | Studio Screen!4 | Suggestion: Remove the extra padding and move the input field for the post into center for the first view | **implemented** — Centre the empty composer until focus/content; retain the owner-requested blank Studio and accessible scrolling layout. |
| QA-17 | Studio Screen!5 | Add the box around the first AI-response | **implemented** — Assistant messages have a pale rounded bubble distinct from the caption editor. |
| QA-18 | Studio Screen!8 | The keyboard should open automatically when the user tap on the 'New post button' | **implemented** — New post focuses the composer after saving. |
| QA-19 | Studio Screen!9 | Suggestion: Move the placeholder text to the center align | **implemented** — Save status and centred publishing-approval reassurance are separate lines. |
| QA-20 | Studio Screen!10 | Social Media Account Selection Is Missing from the “Review Post” Popup | **implemented** — Review stays open with available caption-platform choices and inline guidance when no destination is ready. |
| QA-21 | Studio Screen!11 | Open Social Account” Button Redirects to Settings Instead of the Connection Screen | **implemented** — Native review directly opens the relevant provider connection and refreshes its context; web review links directly to that provider. |
| QA-22 | Studio Screen!12 | Generated Threads Are Not Displayed in the Review Post Popup | **implemented** — Initial and final review show every thread item, numbered when more than one. |
| QA-23 | Studio Screen!13 | Update Revoked Social Account Status Immediately on the Studio Screen | **adapted** — Read-only provider checks on foreground/visible app, bounded to once per minute. Proven revoked access displays reconnect; timeouts/429 remain unavailable, never falsely revoked. Not instantaneous push notification. |
| QA-24 | Studio Screen!14 | iPhone Photo Library Does Not Open and Missing Permission Requests | **device-retest** — Photos picker is presented outside the attachment menu. Uses the privacy-preserving iOS picker, which does not need whole-library permission. Real-device restricted/iCloud/photo/video checks remain required. |
| QA-25 | Studio Screen!15 | Unable to Edit or Update the Link in Post Options | **implemented** — Source URL stays local while typing; validate on Done, inline error, sheet remains open. No partial-URL autosave. |
| QA-26 | Studio Screen!16 | Review Post Popup Closes When Selecting an Unconnected Social Media Account | **implemented** — Disconnected account stays in review with direct Connect and Remove actions; no global dismissal on context error. |
| QA-27 | Schedule Post Screen!2 | Schedule Popup Automatically Closes on First Attempt | **implemented** — Review/schedule initialization is a structured task; context errors stay inline and preserve the sheet. |
| QA-28 | Schedule Post Screen!3 | Improvement:  Fix Date and Time Formatting in the Suggested Starting Time on the Schedule Post Screen | **implemented** — Suggested times rendered through the local date formatter, not raw ISO strings. |
| QA-29 | Schedule Post Screen!4 | Use the Device's Local Time Zone on the Schedule Post Screen | **implemented** — New schedule uses device timezone; an existing planned occurrence retains its explicit timezone. Suggestion label and conversion use the displayed zone. |
| QA-30 | Performance Screen!2 | Display Account Performance Check-In Time Based on the Device’s Local Time | **implemented** — Checked-at display uses the device timezone. |
| QA-31 | Performance Screen!3 | Dismiss the Keyboard When Tapping Outside Input Fields | **implemented** — Window tap recognizer dismisses keyboard without consuming text input, buttons or scroll gestures; scroll-to-dismiss retained. |
| QA-32 | Performance Screen!4 | Selected Brand Automatically Resets to Default After App Restart | **implemented** — Persist selected brand by user/base URL; restore only a brand still present in the authenticated owner list. |
| QA-33 | Profile Screen!3 | Improve the Visibility of Social Media Account Connect Buttons | **implemented** — Primary purple account-connect buttons with white text and accessible targets. |
| QA-34 | Profile Screen!4 | Facebook Account Connection Fails with “Facebook Is Unavailable for This App” Error | **external-blocker** — Meta dashboard on 30 Oct: pages_show_list, pages_read_engagement and pages_manage_posts remain Not submitted. Existing Instagram approvals are intact. Public Facebook connection is not certified until review and a non-role account test. |
| QA-35 | Profile Screen!5 | Instagram Connection Requires Multiple Attempts | **device-retest** — Keep the existing secure web authentication route and return-state validation. Tester first-attempt Instagram issue needs clean-session physical-device reproduction; prior owner success does not close this report. |
| QA-36 | Profile Screen!6 | TikTok Connection Fails | **configuration-blocker** — Tester capture says non_sandbox_target. Read-only comparison confirmed the live Render service uses the sandbox client key, not the approved production key. Production credential correction/Direct Post activation requires the pending specific approval; no credentials copied into this report. |
| QA-37 | Profile Screen!7 | Why does the Instagram connection need a professional account? | **provider-limit** — Instagram publishing API requires Creator/Business. Explain this before connecting; personal-account automatic publishing cannot be implemented honestly. |
| QA-38 | Profile Screen!8 | Improve the Unlink Account Flow with a Confirmation Popup | **existing-verified** — Native unlink already requires confirmation; cancel does not unlink. |
| QA-39 | Profile Screen!11 | Improvement: Fix the placeholder text alignment to the start on the input field | **implemented** — Multiline strategy fields explicitly lead-align text and placeholder. |
| QA-40 | Profile Screen!12 | Settings Screen Gets Stuck on the “Updating” Loader | **implemented** — Strategy work is cancelled on close; cancellation releases busy state and is not surfaced as a connection error. Replacement work awaits previous cleanup. |
| QA-41 | Profile Screen!15 | Add the dropdown of the timezone selection | **implemented** — Searchable timezone list plus Use this iPhone timezone; no manual identifier entry. |
| QA-42 | Profile Screen!16 | The connection lost error appears multiple times during updating the voice content | **device-retest** — Native voice saves now receive direct JSON instead of redirects; repeated saves and persistence covered by authenticated API tests. Original device/network failure still needs recheck after upgrade. |
| QA-43 | Profile Screen!17 | Improvement: Center the “Status Updated” Popup on the Screen | **adapted** — Centred, accessible nonmodal saved feedback; avoids adding another blocking popup. |
| QA-44 | Profile Screen!20 | Improve the Visibility and Usability of the “Add Brand” and “Rename Current” Buttons | **implemented** — Add and Rename primary buttons have consistent contrast, spacing and targets. |
| QA-45 | Profile Screen!21 | Automatically Populate the Current Account Name in the “Rename Current” Input Field | **implemented** — Current brand name is prefilled and restored after Account load. |
| QA-46 | Profile Screen!24 | Change Password Button Does Not Work or Display Validation Messages | **implemented** — Visible password length/match feedback, disabled invalid submit, server validation messages, session revocation preserved on successful change. |
| QA-47 | Profile Screen!25 | Improve the “Change Password” Button Text for Better Usability | **implemented** — Update password label across native and web. |
| QA-48 | Profile Screen!26 | Improve the Security and Privacy Section Design for Better Usability | **existing-verified** — Security & privacy remains an icon-labelled expandable group; improved password controls/checklist. No return to excessive pills/cards. |
| QA-49 | Profile Screen!29 | Improve the “Send Verification Email” Button Color for Better Visibility | **implemented** — Verification action is a clear primary button when email is unverified. |
| QA-50 | Profile Screen!30 | Improve the Visibility and Design of the “Sign Out” Button | **existing-verified** — Sign out remains alongside account identity at the top with a 44pt target; no duplicate destructive navigation. |
| QA-51 | Profile Screen!33 | Display a Reconnection Popup When Social Account Access Is Revoked | **adapted** — Foreground status banner with reconnect action; saved work preserved, no forced modal loop, no false revocation on temporary provider failure. |

## Virtual tester findings

| Observed problem | Candidate change / limit |
|---|---|
| Negative constraints cancelled drafting | Restrict stop detection to publishing verbs; drafting and no-publish instructions coexist. |
| Rewrite both only changed one platform / invalid count | Explicit all/both/two scope, strict per-platform JSON schema and exact thread counts; both outputs must pass before applying. |
| Invented free trial, recurring date, personal claims | Facts/offer/frequency rules and style-only examples added to caption and Next Move prompts. Real model comparison supports stronger creative model; prompts alone do not guarantee factuality. |
| Voice disappeared on rewrite | Approved and supplied writing examples are now sent on rewrite as well as generation. |
| Private tracking plans and claim caveats in captions | Separate creator instructions from public copy, preserve disclosure and requested CTA. GPT-5 mini still failed the evaluation; see model decision. |
| Supplied performance figures ignored without connection | Allow labelled user-supplied/hypothetical analysis without a provider connection; Performance now offers the question box before connection. Unknown metrics remain unknown, not zero. |
| Analysis chats cluttered Schedule | New performance-only chats stay in Studio history and are omitted from saved posts; adding a caption/media puts them back. Existing records are not deleted. |
| Review dead end when unconnected | Direct platform connection action, preserved review and inline errors. |
| Music implies capabilities it does not have | Music options label; clearly distinguishes eligible Reel music from finishing photos/Stories inside Instagram. |
| Repeated setup and weak next ideas | Reuse saved strategy, voice and available performance; respect explicit resources/frequency; keep two-field strategy, one proposal, optional refinement and endless batches. No extra questionnaire. |
| Carousel and sales claims | No claim that a text/shot plan is a completed carousel. No invented sales attribution or connected sales data; user-supplied sales are labelled. |
| Too much friction/weekly return value | No new Studio Your week card, no duplicate Reset, no enforced payment/onboarding steps. Schedule stays the calendar; voice learning remains consent-controlled. |

## AI decision

Production was confirmed to use gpt-5-mini. Four synthetic tasks were compared against gpt-6.1-terra twice. The first run had a local text-encoding issue and is provisional; the clean UTF-8 repeat is the reported comparison. No customer content or provider credentials were sent as test prompts.

| Task | GPT-5 mini | GPT-6.1 Terra |
|---|---|---|
| One-off Brixton class | Preserved time/one-off, 8.07s | Preserved time/one-off, 2.34s |
| Affiliate caption | Failed disclosure placement: copied “Start Ad …” into body, 8.19s | Correct opening disclosure and commission, 4.66s |
| Both-caption rewrite, scoped to one platform | Correct count, generic extra CTA, 5.78s | Correct count, concise supplied facts, 1.68s |
| Supplied A/B performance | Correct arithmetic, verbose; invented “limited stock” in proposed CTA, 19.49s | Correct rates, clear source caveat, one-variable experiment, 9.49s |

Recommend GPT-6.1 Terra for generation, rewrite, Next Move/strategy and performance interpretation; retain the cheaper model for intent routing. OPENAI_CONTENT_MODEL now supports that separation with per-request isolation. It is opt-in and has not changed production. Updated analysis prompt also prohibits invented scarcity and targets 120 words. This small evaluation is not a general quality benchmark or a guarantee of factual captions.

Official model pages: https://developers.openai.com/api/docs/models/gpt-6.1-terra and https://developers.openai.com/api/docs/models/gpt-5-mini. Terra standard text prices are $1 input/$5 output per million tokens. Mini is $0.25/$2. An illustrative 2,000-input/500-billable-output-token call is $0.0045 vs $0.0015, before retries, extra reasoning, images, tools and taxes. Actual task usage must be measured.

## Validation and release limits

- Focused backend pass: 46 tests (before the final small UI/voice adjustments). Full SQLite, PostgreSQL, browser, native simulator and Release compile results pending.
- New regression coverage includes drafting negations, both-caption scope, schema length, voice examples, source-labelled numbers, concurrent model isolation, saved analysis separation, signup verification failure, connection revocation/cache/reconnect races and repeated native voice saves.
- Native regressions exercise stored chat/brand pointers, five-item review with unconnected destination, invalid URL kept in Post options, and keyboard dismissal. Simulator results pending.
- Confirmed live: Stripe mode test; REQUIRE_SUBSCRIPTION=false. Render remains in use. No paid monitor activated.
- Facebook public Page permissions remain unsubmitted; TikTok production key correction is pending approval; first-attempt Instagram and real-device picker/voice checks remain explicit acceptance tasks.
- No production deploy, App Store submission or TestFlight notification has been made in this task.
