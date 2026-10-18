# Studio sent-message and TikTok drafting correction — 18 October 2026 (not deployed)

Branch codex/studio-send-recovery-20261018 addresses two owner-reported defects: sent ideas remaining in the composer and TikTok-only sponsor/paid-partnership drafting incorrectly demanding an X version. Planner targets now follow the actual selected/active caption and create a first version when no caption exists; sponsor URLs are content, not destination changes. Sent text moves into the conversation before planning; failed requests have a separate Retry message control, retain attachments and unsent new input, survive reload, and do not duplicate the user turn. Initial save failure keeps input in place. Late replies remain workspace-bound. Pending-message metadata is additive; no schema migration.

Synthetic browser checks: exact screenshot request produced a TikTok caption, empty composer persisted after reload; 390px mobile failed generation/reload/keyboard retry succeeded with one user turn, no horizontal overflow. Evidence locally under social-proof/studio-sent-tiktok-20261018.png and studio-retry-mobile-20261018.png. Model/providers mocked; no real post, grant, charge or production data changed. Local full suite: 359 passed / 1 skipped. Client lifecycle and planning/scheduling suites passed. Successful generation now clears pending metadata atomically; new-draft forks preserve source state and copy transcript/media/link/composer into the new row, guarded by ownership, status and revision. Synthetic browser verified reopening the old draft does not offer a stale retry. Runtime candidate 2fa13f72009fa4629129070c14b8e15fa9f73631 is pushed; hosted CI39146945668 passed all required jobs: synthetic tests, PostgreSQL tests, synthetic restore, container build/smoke, dependency audit and exact beta guardrails. Not deployed; sandbox and production remain unchanged.

Commercial-disclosure tests verify existing own-brand/paid selection, label/declaration changes, consent reset, private-paid rejection and immutable options. Sandbox remains unaudited/Only me; an actual paid-partnership post cannot use Only me. Demonstrate controls without publishing; public-access audit approval remains required. Production stays inbox-only, Instagram unchanged, native branch not deployed. All 79 broader beta findings retained.

Rollback: revert this bounded candidate or redeploy sandbox runtime 89e7cf716d82f358d52515b58313862f0258c7eb. Preserve data, uploads, sessions, connections and publication receipts; never resend prior tests. Old code ignores pending_message JSON. Free sandbox storage remains ephemeral; no deployment was requested in this update.

---

# Sandbox release verified — 16 October 2026

Owner requested publish. Deployed exact89e7cf716d82f358d52515b58313862f0258c7eb to existing Free TikTok sandbox only. Render dep-db9819ff3r2c73afr1p0 reports Deploy succeeded|Live. CI38957921987 passed all gates:319passed/1skipped each on SQLite/PostgreSQL, synthetic backup restore, image build/smoke, dependency audit and exact beta scope. Public health/login200; deployed studio-publish.js, studio-state.js, readiness.js, studio-design.css and studio.js match local candidate byte-for-byte after newline normalization. Evidence social-proof/sandbox-release-89e7cf7.png.

Production zova-social.com unchanged and inbox-only. No real social post, new grant, billing change, or native deployment. Owner may need fresh sandbox login/TikTok connection because SQLite/uploads are ephemeral. Never resend previously published draft1. Sandbox rollback is7fdec1573a004bd28d79ee0e54c0628461969247, without restoring production data or replaying posts. Next: owner can record the cleaner caption/review flow, verify the actual private TikTok post, then prepare truthful approval evidence. Public Direct Post approval still pending;79 wider beta gaps remain.

---

# Studio clarity and TikTok result refresh — 16 October 2026

Current local changes address the owner's recording feedback: caption-first creation/rewrite without media-observation narration, explicit Edit caption (Story retains Edit planning notes), compact composer and collapsed composer during review, readable TikTok privacy labels, automatic read-only publication checks every15seconds for up to10minutes, and public TikTok links when the provider returns a real public post ID. Private sandbox posts accurately show Published without manufacturing a public link. Polls are draft/workspace-bound, terminal results stop polling, and background checks do not move focus. Backend GET and worker share throttled receipt reconciliation; unknown outcomes are never resent. Existing Instagram logic is unchanged.

Validation: full local SQLite suite319passed/1skipped; Node lifecycle/polling/media-summary checks passed; exact beta scope verified. PostgreSQL/remote release gates not run for this candidate. Validated synthetic desktop1280x720 and phone390x844: no horizontal overflow; caption edit/save/final snapshot verified; review composer56px and phone review feed627px. Normal composer252px desktop/291px phone with a video attachment; no-attachment composer is smaller. Local screenshot social-proof/studio-caption-20261016.png. No real post, grant, or production change. NOT DEPLOYED. Before deployment rerun required remote PostgreSQL/restore/container/dependency gates on exact candidate; sandbox is ephemeral and redeploy may require reconnecting. Broad79 gaps remain open; no commercial certification.

Rollback: revert this bounded change set; no schema migration. Reconciliation adds optional status_checked_at/url fields only to existing result JSON; old code tolerates these. Preserve publication receipts and never resend earlier tests. Production TikTok remains inbox-only pending approval. Prior sandbox publication must not be repeated.

---

# Saved stopping point - 16 October 2026

Owner will return tonight; no scheduled reminder or background posting requested. TikTok Direct Post works in the isolated sandbox: draft1 returned Published after refreshing provider status, for @davidwilson493 with Only me visibility. Do not resend this draft. Independent viewing of the private video in TikTok remains unconfirmed.

Next session: read this handoff, check sandbox availability/session first, and have owner verify the private video on TikTok. Prepare a NEW draft for the recorded demonstration: connect account, upload original media, edit caption, show privacy/interactions/disclosures and consent, final review, owner-authorised private publication, refresh status, then show the actual TikTok post. Review recording before submitting TikTok production video.publish revision and separate public-access audit. Neither is submitted/approved yet. Production stays inbox-only; approval enables eligible customers to publish publicly from the main site. No further implementation or production activation is implied by the successful private test.

Sandbox https://zova-tiktok-sandbox.onrender.com is FREE with ephemeral SQLite/uploads; restart/spindown/redeploy can lose test state and require a fresh test login/reconnection. Auto-deploy is Off. Do not reconnect its database to production. Code/configuration evidence and recording plan are saved in docs/TIKTOK_DIRECT_POST_20261016.md; screenshots and synthetic video remain locally under social-proof/. Do not expose credentials or upload the whole proof folder. Preserve all79 known beta gaps and existing connections.

---

# TikTok private Direct Post confirmed by refreshed provider status - 16 October 2026

On return to sandbox draft1, UI was already Waiting for platform processing (dispatch occurred outside this agent turn). Agent only clicked Refresh results, never Confirm publish. Refreshed publication result and sidebar both show Published. Reviewed destination @davidwilson493, Only me, exact test caption and6second video described below. Evidence social-proof/tiktok-private-published.png. This establishes Zova provider-status confirmation of private Direct Post; independent viewing in TikTok still needed for recording. Do not resend. Public approval/audit remains pending. Production unchanged.

---

# TikTok final private review verified - 16 October 2026

Owner explicitly approved accepting TikTok Music Usage Confirmation and opening final review only. Accepted agreement and generated server-owned final snapshot successfully for sandbox draft1, David Wilson @davidwilson493, six-second zova-beta-test.mp4, exact caption: Zova Direct Post integration test — checking our reviewed publishing flow. Final review displays SELF_ONLY; comments/Duet/Stitch off; own brand/partnership/AI-generated media no; video preview and processing notice. Confirm publish was NOT clicked. No provider publication outcome claimed. Evidence social-proof/tiktok-final-review-ready.png. Await exact separate private-test publication approval or owner recording; do not resend previous tests. Production unchanged. Cosmetic follow-ups: raw SELF_ONLY and opaque provider ID appear in review; mixed create + do-not-publish intent quirk remains.

---

# Live TikTok sandbox account and media verified - 16 October 2026

Owner signed into sandbox in side browser. Account shows David Wilson connected; live publish context identifies @davidwilson493. Uploaded existing synthetic6-second ZOVA BETA TEST video into new draft1. Browser preview readyState4/duration6; unauthenticated media GET200 video/mp4 20834bytes under verified sandbox prefix. AI inspected8frames. Initial mixed create + Do not publish message stopped generation; simpler drafting request succeeded. Record that intent-handling defect; do not silently call resolved.

Edited exact caption: Zova Direct Post integration test — checking our reviewed publishing flow. Live privacy options Followers/Friends/Only me, no default; comments unchecked; Duet/Stitch disabled by provider. Selected Only me. Agreement checkbox remains UNTICKED and Review final post disabled. Asked owner at-action permission to accept TikTok Music Usage Confirmation and open final review ONLY. No TikTok post sent, no final snapshot/provider outcome yet. Screenshot social-proof/tiktok-live-private-review.png. Next: await agreement answer, open final review, obtain exact separate private publication approval before sending. Sandbox ephemeral; avoid restarts. Production unchanged.

---

# TikTok recording sandbox ready for account connection - 16 October 2026

Reused existing FREE Render service zova-tiktok-sandbox (srv-d9u4joad0e5s73afpu10). Discovered it previously shared the production PostgreSQL database; changed this test service ONLY to sqlite:////tmp/zova-tiktok-recording.db, verified saved. Production users/data/keys/service unchanged. This temporary database and local uploads may be lost on restart/spindown/redeploy. Do not promise durable staging; record in one session and keep external evidence. Auto-deploy is Off to avoid branch updates resetting recording state.

Owner explicitly approved copying existing TikTok Sandbox client key/secret into this existing Render service. Configured those credentials, PUBLIC_BASE_URL and callback to https://zova-tiktok-sandbox.onrender.com, TIKTOK_SEND_TO_INBOX=false, SELF_ONLY default config (user must still explicitly select privacy), REQUIRE_SUBSCRIPTION=false, ZOVA_ENV=sandbox, and TIKTOK_VERIFIED_MEDIA_PREFIX=https://zova-tiktok-sandbox.onrender.com/media/raw/. Verified saved nonsecret values after deployment. No public post or new user grant sent.

Sandbox7672854716816082965 under TikTok app7672846663509215253 already has Direct Post and video.publish. Existing target user davidwilson493. Updated sandbox website to recording host. TikTok verified https://zova-tiktok-sandbox.onrender.com/ URL prefix using downloaded signature file; screenshot social-proof/tiktok-sandbox-prefix-verified.png. Production TikTok draft/live settings were not changed in this increment.

Dedicated branch codex/tiktok-recording-sandbox-20261016 pinned on test service, Live7fdec1573a004bd28d79ee0e54c0628461969247, deploy dep-db91mlcvk9tc73ea9df0. Only runtime change versus PR33 is static sandbox verification route. Initial CI caught CRLF digest mismatch; corrected normalised digest, CI38901929057 passes all required jobs:315 tests/1 skipped on SQLite AND PostgreSQL, restore/container/dependencies/guardrails. Local Direct Post tests16passed. Verification endpoint200 with exact signature; signup rendered and no subscription charge. Production remains cc093687 inbox-only; no broad native branch deployment.

User has been asked to create a SEPARATE Zova login at https://zova-tiktok-sandbox.onrender.com/signup then connect registered TikTok tester davidwilson493, or identify another account to add as sandbox target. Do not share passwords. Real OAuth, creator restrictions, uploaded media fetch, final review and private Direct Post outcome remain pending their connection; no ready-to-record end-to-end claim yet. Before sending anything obtain exact post/account/privacy approval. Complete provider verification, then recording; do not submit old inbox recording as Direct Post evidence. No iOS device validation performed. All79 broader beta gaps retained.

Rollback: keep test DB isolated; do not point sandbox back to production. Set only sandbox TIKTOK_SEND_TO_INBOX=true to disable Direct Post or suspend test service if requested. Keep production unchanged. Preserve any publish receipts before restarting disposable sandbox.

---

# Direct Post deployment evidence - 16 October 2026

PR33 is merged as cc093687bc92f5600283918d330ef70691e4216e and verified Live on Render dep-db91bkvavr4c739qd50g. Public /health and versioned Studio publishing script return200; the script contains the new Direct Post controls and policy declaration. Required hosted checks passed:315 tests /1 skipped on SQLite and PostgreSQL plus restore, container, dependency and release checks.

Production remains inbox-only. Direct Post is NOT enabled or provider-validated. TikTok production draft contains video.publish and Direct Post. Updated notes were entered and Save clicked; subsequent reload and Manage apps navigation returned Request aborted, so persistence of the latest notes could not be reverified. Earlier draft save was verified. Separate audit at Supporting documents is unsubmitted. Verified URL prefix is https://zova-social.com/; TIKTOK_VERIFIED_MEDIA_PREFIX still needs configuring and validating against hosted storage before direct testing. Do not change delivery mode or resend previous test posts.

Native PR28 includes the same server implementation. Its contract was regenerated for the additive connection_ids field (05e2c93);40 focused tests pass /1 skipped. All required hosted native checks passed in38900036915 and38900044596. Native remains disabled and undeployed. Desktop synthetic UI inspected; attempted mobile viewport override did not take effect, so mobile visual validation is still outstanding.

Remaining: isolated real Direct Post authorisation and exact-approved private test, new provider recording, reviewer access check, app revision plus public-access audit submission and approval, then reconnect for video.publish and controlled feed rollout. Existing inbox recording is insufficient. All79 broader beta gaps retained. Rollback and recording script: docs/TIKTOK_DIRECT_POST_20261016.md.

---

# TikTok Direct Post preparation - 16 October 2026

See docs/TIKTOK_DIRECT_POST_20261016.md. Production remains inbox-only. TikTok draft revision saved with video.publish and Direct Post; not submitted. Existing URL prefix https://zova-social.com/ verified. Separate audit form at Supporting documents, not submitted, browser answers may be ephemeral. New real Direct Post recording and provider validation required. Local implementation includes consent/disclosure/fresh creator/duration/verified-media controls and tests; no live Direct Post or native rollout claimed. All79 gaps retained.

---

# Facebook live publication verified - 16 October 2026

Owner explicitly approved the exact single public text-only Facebook test. Published once through draft28 immutable final review to Zova Social Page1232370066628887. Zova returned Published and receipt122119807485439972. Independently opened Facebook and verified the exact text, Zova Social author and Public audience at https://www.facebook.com/61593199172836/posts/122119807485439972/ . Leave the post in place; do not resend or remove without owner request. Screenshot social-proof/facebook-provider-verified.png is local evidence.

Facebook app-role connection and text publication now verified. General customer access remains blocked on the separate unsubmitted Meta Page-permission review; do not equate this test with approval. X text test verified; TikTok inbox received per owner, not publicly published. Instagram unchanged. Image/thread/scheduling and native device validation are not established by these live text/inbox tests. All79 broader gaps retained.

---

# Provider validation update - 16 October 2026

Owner explicitly approved the narrowed Facebook grant and six-second TikTok inbox test. Saved Meta grant for Zova Social Page1232370066628887 only, then confirmed the exact Page in david1@gmail.com / My brand. Zova Account shows Connected. No Facebook post sent yet; draft28 is being prepared for separate exact publication approval.

Submitted synthetic video from reviewed TikTok draft27 once. Zova returned pending/complete in TikTok, without error. Owner independently confirmed "Video received in TikTok" on16 October2026. This verifies inbox delivery, not public publication. Do not resend. UI still says Waiting for platform processing even after confirmed inbox receipt; improve delivered-to-inbox labelling as a follow-up without marking it publicly published. Instagram unchanged. Facebook public-customer permissions review remains unsubmitted/unapproved. Shared native integration head93af22c passed all required CI38888696671/38888702089, remains disabled/undeployed.

---

# Live social review fix - 16 October 2026

PR32 is Live (8ef1230, Render dep-db8vtgjrjlhs73betts0); all required checks passed; health200 and real TikTok draft27 final inbox review verified. X approved test already published once: https://x.com/DataMaxxingUK/status/2111033940157055189 . Do not resend. Pending owner answers: final narrowed Facebook grant for Zova Social only; exact six-second synthetic TikTok inbox send. Do not treat elapsed time as approval. No Facebook/TT delivery receipt yet. Shared native branch93af22c integrates all fixes, remains disabled/undeployed. See docs/SOCIAL_BETA_COMPLETION_20261016.md and feature matrix.

---

# Social beta integration work - 16 October 2026

Read docs/SOCIAL_BETA_COMPLETION_20261016.md for evidence and rollback. Instagram preserved. PR30 live; X authorised test published once and verified: https://x.com/DataMaxxingUK/status/2111033940157055189 . Do not resend. TikTok connected; draft27 holds an unsent synthetic video. Facebook three-permission review draft saved, not submitted. PR31 least-privilege Facebook change merged with required checks; hosting verification pending. Current cache-version follow-up has20 focused tests passing but is not yet deployed. Verify inbox review after rollout before requesting exact video-send approval. Restart stale Facebook consent without business_management before asking for Page grant. Native PR28 remains draft/disabled; shared fixes integrated through PR31, final checks pending. All79 gaps retained.

---

# Next Move always-visible sections — 12 October 2026 (not deployed)

Branch codex/next-move-open-sections-20261012 replaces the Details and Change this idea dropdowns with always-visible, labelled sections and bold16px headings. No collapse controls on either section. Source evidence retains its separate disclosure. See steps now focuses the visible Details heading. Existing draft/feedback behavior preserved. Node journey/onboarding suites and4 beta scope tests passed. Synthetic desktop1280x720 and mobile390x844 reviewed; feedback input directly accessible, no horizontal panel overflow. No provider, schema, account or billing changes; all79 gaps retained. Rollback live db9a4ff6daff2735b48ff989771c9ae8c91e866c. Hosting checks required before publication.

---

# Creator Studio refinement is live — 12 October 2026

PR26 merged as db9a4ff6daff2735b48ff989771c9ae8c91e866c. Render dep-db6cikc9v7es739ubsbg is Live (56.6s rollout). Final candidate83fb222 passed all required checks in PR38244952639 and push38244944763. Brief startup HTTP errors recovered; health200 and exact deployed studio-design.css, studio-state.js and studio-experience.js matches verified. Signed-in live Studio starts with a blank composer/welcome and no recommendation card; saved history and personal workspace label render; recommendations load inside Next Move with existing Open draft, Details and Change this idea controls. No real post, grant or charge performed. Owner screenshot is local only: docs/validation/creator-studio-live.jpg. No schema change. Rollback798796b86168b68aa1e9993ca3a028991b3eee49 preserves data, uploads, sessions and connections. All79 broader beta findings remain open.

---

# Creator Studio refinement — 12 October 2026 (not deployed)

Branch codex/creator-studio-20261012 implements the creator critique with the owner's overriding preference: Studio starts with a blank chat; recommendations stay ONLY in Next Move. No home recommendation card or background generation. Refined purple identity/controls, saved brand/profile label, owned attachment thumbnails with safe fallbacks, readable two-line history, natural creator-hook guidance and consistent New chat welcome. Four visual review passes, including compact mobile navigation; desktop390px/320px mobile, keyboard-to-draft, media reopening and clean reset verified on synthetic localhost. Local274passed/1skipped; Node suites passed; ownership/brand/URL preview regressions added. See docs/CREATOR_STUDIO_REVIEW_20261012.md for the executed prompt, heuristic scores and evidence limits. All79 broader gaps retained; no migration, real posts, grants or charges. PR26 implementation2ec749a passed all required checks in38244715161 and38244710412. Await explicit publication; not merged. Rollback live798796b86168b68aa1e9993ca3a028991b3eee49.

---

# Studio design coherence is live — 12 October 2026

PR25 merged as 798796b86168b68aa1e9993ca3a028991b3eee49. Required synthetic, PostgreSQL and production guardrail checks passed on final candidate 282ee8e in CI38241265879 and push38241259549. Live health returned200; studio-design.css, studio.js, studio-experience.js and strategy.js matched the tested files. Signed-in live draft24 and the loaded Next Move panel visually verified: compact composer, conditional Post/Story, primary Review & publish, consistent navigation icons, restrained branding and Details/Change this idea. No real social posts, grants or billing changes. Render dashboard connection closed during verification, so deployment ID was not recorded; live application and asset verification succeeded. No schema migration. Rollback to1998cec03762931a362c17705b8a04081c5cdb94 preserves data. All79 broader beta gaps remain open. Owner screenshots are local only. See docs/STUDIO_DESIGN_REVIEW_20261012.md.

---
# Studio design coherence candidate — 12 October 2026 (not deployed)

Branch codex/studio-design-coherence-20261012 completes three visual review passes against the six cosmetic criteria. See docs/STUDIO_DESIGN_REVIEW_20261012.md for recommendations, benchmark sources, measured layouts, scores and limits. Primary draft action, composer grouping, restrained branding, shared navigation icons, readable controls, compact Next Move and plain-language recommendation guidance implemented. Local SQLite272passed/1skipped; Node suites and synthetic desktop/mobile/keyboard/edit/reload review passed. PR25 implementation checks passed in CI38240968536 and38240961652, including PostgreSQL and beta safeguards. Not merged or deployed; use normal protected release flow when publishing. All79 broader beta findings retained; design8/10 scores are heuristic, not commercial readiness. No real provider actions or schema migration. Rollback1998cec.

---

# Details-only Next move is live — 12 October 2026

PR24 merged as1998cec03762931a362c17705b8a04081c5cdb94. Render dep-db6bf3k9v7es739t2iag is Live. All required checks passed in PR CI38236867250 and push38236860942. Brief startup502 recovered; health200 and exact strategy.css/strategy.js matches verified. Signed-in live Next move shows only Details and Change this idea beneath the card/carousel; planning controls remain accessible via Post options. Purple gradient launcher shipped. No real posts or account/billing mutations performed. Rollback to1c978a1401427246bfe57ad230faa2f475ae54f9 preserves data. Broader beta gaps remain open.

---

# Next move details-only refinement — 12 October 2026 (not deployed)

Branch codex/next-move-details-only-20261012: recommendation view exposes only Details and Change this idea beneath the card/carousel. Removed More options wrapper and reminder UI. Plan/settings/recurring controls are hidden from Next move and remain accessible in the separate Your plan view through Post options or Plan my socials. New accounts see Set your goal; confirming the plan returns to recommendations. Launcher retains white text/shimmer with a near-black plum-to-violet gradient. No backend/data/auth/publication changes. All79 broader beta findings retained.

Validated synthetic browser setup-to-plan-confirm-to-recommendation flow, clean panel and separate Post options planning access; Node onboarding, journey, schedule and Studio checks pass. Regression asserts planning/recommendation visibility separation. Hosted release checks/deployment remain pending. Rollback to1c978a1 preserves data.

---

# Next move focus release is live — 12 October 2026

PR23 merged as1c978a1401427246bfe57ad230faa2f475ae54f9. Render dep-db6b7poae00c73afn09g is Live. Required synthetic, PostgreSQL and production guardrails checks passed in CI38235232320 (also push38235226889). Health200 and exact deployed strategy CSS/JS, shared icon helper and X/Facebook/TikTok SVG matches verified. Signed-in Studio displays the larger black/white launcher and all four platform icons. No real social posts, grants or billing changes. Broader beta gaps remain open. Rollback to b82b04715c7c48efaa22d0a21d41d90021121cb4, preserving data.

---

# Next move focus and platform icons — 12 October 2026 (local, not deployed)

Branch codex/next-move-focus-icons-20261012 simplifies the card to one More options disclosure, retaining feedback, reminders, context and keyboard navigation. Studio launcher is larger black/white with two gentle shimmer cycles; reduced-motion disables animation. Shared locally hosted X/Facebook/TikTok SVG marks replace text approximations across composer, strategy, draft/review/results, analytics, account and landing controls. Names remain in accessible labels and prose. No backend, auth, billing or publication changes. All broader beta gaps remain open.

Validation: desktop and390px browser review, icon accessible names, secondary disclosure; existing Node journey/onboarding/schedule/Studio suites pass. Full local SQLite suite:271 pass/one skip with only stale scope manifest failure; refreshed exact scope after review and all4 beta gate tests passed. PostgreSQL hosted checks and deployment have not been run for this candidate. Rollback to b82b047 preserves all data. Screenshot docs/validation/next-move-focus-studio.jpg is synthetic and local.

---

# Next move carousel is live — 12 October 2026

One recommendation at a time with previous/next, Details, optional Change this idea, and Remind me (tomorrow/next week/custom browser-local date converted to UTC). This is idea deferral, not post scheduling. Removed Made for your plan/Quick check/Behind the idea/You’ll need labels; review instructions now use readable dark text. Official Instagram artwork sourced from Meta’s brand page is shared across composer, draft/platform controls, account connections and analytics. Prose/legal names remain readable. No schema migration; feedback fits existing80-character column. PR22 merged as b82b04715c7c48efaa22d0a21d41d90021121cb4. Render deployment dep-db68tbjrjlhs73bfl820 is Live. CI38218780881 passed all required checks: 272 passed/one skipped on both SQLite and PostgreSQL; client interaction checks passed. Live home returned200 and four deployed assets exactly matched. Live signed-in carousel navigation, Instagram glyph, readable review steps and reminder choices verified without changing owner recommendations or publishing posts. Local synthetic feedback, reminder, draft/reload and keyboard/mobile journeys passed. See docs/NEXT_MOVE_CAROUSEL_20261012.md. Broader beta gaps remain open.

---

# Next move brand update is live — 12 October 2026

PR21 merged as562d7a9404dead17ce5fac77279f155544037365. Render deployment dep-db68joek1f9s73f2g5dg succeeded, live at07:20:05UTC. GitHub Actions had been disabled (enabled:false); re-enabled existing workflow and ran normal PR checks. No branch protection bypass. CI38216870312 passed all required checks,271 passed/one skipped for each SQLite and PostgreSQL.

Live health200 and exact strategy.js/strategy.css content match verified. Existing signed-in draft22 opened and the new dark Next move card, Skip and compact disclosures rendered. Existing stale-source warning remained accurate. No ideas were dismissed, real social posts sent, grants changed or charges made for this release verification. Screenshot is local only and contains owner context. Broader beta/security gaps remain open in docs/beta/KNOWN_GAPS.md and deferred-register.json. Rollback to4d86fe7 while preserving data, drafts and sessions.

---

# Next move visual refinement ready for release checks — 11 October 2026

Candidate15bd98e in PR21. Local browser design/interaction checks passed at desktop,390px and320px widths; see docs/NEXT_MOVE_BRAND_20261011.md. Hosted workflow38174288031 remains queued without started jobs. This design has NOT been merged or deployed. Finish required checks before publishing; do not bypass them. Broader beta gaps remain open.

---

# Next move brand refinement — 11 October 2026

Reworked the recommendation panel with a dark Zova card, original translucent Z asset, stronger type, Draft/Skip actions, compact evidence and icon refresh. Removed reason questionnaire and duplicated approval text. Skip advances to the next saved idea and requests more when exhausted, preserving visible cards on save failure. Local desktop/mobile and keyboard journey reviewed; candidate awaits release checks. No backend/model/schema changes. Broader beta defects remain open.

---

# Next move published and verified — 10 October 2026

Live commit 4d86fe76eb5c2fc2bfe7388b7b3a6f8491cf5789, Render dep-db588kn40ujc73c8cp90, service live at 18:31:51 UTC. PR19 delivers the compact recommendation-to-draft journey; PR20 corrects invalid model response handling found during live verification. CI38075939402: 271 passed / one skipped on SQLite and PostgreSQL, required beta scope/restore/image/dependency checks passed.

Live authenticated verification: empty saved plan automatically generated three recommendations; Draft post created an actual AI-written draft, navigated to Studio, retained Instagram-only selection and content on reload; reopening Next move offers Open draft. Draft23 is the retained unapproved validation draft in workspace0. No real social publication, scheduling, charge or grant change occurred. Health/login/signup returned200; PR19 client asset matched the reviewed source. Desktop/mobile390x844 and keyboard/failure/late-response testing used isolated synthetic data. Saved screenshots include owner data and must not be committed publicly.

Read docs/NEXT_MOVE_SIMPLE_20261010.md and docs/validation/next-move-live-20261010.json. Remaining limitations: live generation was verified for one saved strategy/account, not every provider/model outcome. Invalid output gets one repair; provider outages still require retry. Broader commercial/security backlog remains open in docs/beta/KNOWN_GAPS.md and deferred-register.json and must be prioritised on future updates. No schema migration; rollback to ebb6f48 for the repair or4c0b041 for the full Next move update, preserving drafts/data.

---

# Next move live-model follow-up — 10 October 2026

PR19 is live as ebb6f48. The compact UI and synthetic journey passed, but live recommendations failed strict validation. Current follow-up supplies the exact schema/platform constraints and one bounded repair; awaiting full CI and live verification. Read docs/NEXT_MOVE_SIMPLE_20261010.md. Broader beta gaps remain open.

---

# Next move simplification candidate — 10 October 2026

Read docs/NEXT_MOVE_SIMPLE_20261010.md. Current update responds to the owner-reported empty/cluttered Next move journey. Implements automatic missing/stale recommendations, one featured post, compact disclosures, explicit draft platform/title, save failure and late-navigation protection. Local synthetic browser end-to-end setup/draft/reload and two design review passes completed. Broader security gaps remain required follow-up in docs/beta/KNOWN_GAPS.md. Await CI and live verification before calling this update published.

---

# Beta is live — 10 October 2026

Verified Render deployment dep-db52dg3rjlhs73abnrr0, commit 4c0b0419beb6944bd8e0db3189432d259e9efded, live at 11:52:45 UTC. PR 17 merged after all three required checks passed. CI 38049756412: SQLite 265 passed / one skip; PostgreSQL 265 passed / one skip; restore/image/dependency and exact-scope beta gate passed. Health/login/signup returned 200; live Studio asset matched candidate and browser retained existing session/draft21. Transient 502 during startup recovered. No real post/charge/provider grant or secret change was used for validation.

Known gaps and next-update requirements: docs/beta/KNOWN_GAPS.md and docs/beta/deferred-register.json. Commercial readiness remains unapproved. Broader PR18 security migration is deferred and must not be deployed wholesale. When the owner next requests updates, address/reconcile the saved defects and security gaps first. Local screenshot contains the owner's draft: do not commit or share it publicly. Sanitised release evidence: docs/validation/beta-live-20261010.json.

---

# Limited beta authorisation — 10 October 2026

Owner requested publication as a beta for personal testing and deferral of the remaining commercial work. This supersedes the all-sections-complete requirement for this focused beta only. Read docs/beta/KNOWN_GAPS.md and docs/beta/deferred-register.json on every future update and address the recorded issues before unrelated expansion.

Use focused UX PR 17; do not publish the broad unfinished security/service migration in PR 18. The beta excludes later optional MFA and account/usage hardening, which remain next-update priorities. Required application/PostgreSQL/migration/restore/image and scoped beta checks must pass. Deployment has not yet been confirmed; append actual revision and evidence after verification. Existing billing test settings, data, sessions and publishing approvals must remain intact.

---

# Publication blocked by enforced production gate — 8 October 2026

User authorised publication. A focused release was prepared in the sibling `zova-ux-release` worktree, branch `codex/ux-release-20261008`, PR #17 (https://github.com/davidwilson92-cpu/DataMaxxing/pull/17), candidate `1398c7ececae2de5ab9370e7c43fa9021ba4c11d`. It is NOT merged or deployed. Production remains `38f1c265`.

Both push and PR CI passed synthetic-tests and postgres-release. Final suites: 261 passed / one expected skip on SQLite; 261 passed / one expected skip on PostgreSQL (SQLite-only backup test). PostgreSQL old-schema title migration DID pass, as did dump/restore, Docker smoke and all three frontend harnesses. Dependency audit is clean after oauthlib 4.0.0 and direct OAuth1 signing for the legacy X text path. No real post was sent. Render export was created 8 October 2026 20:35 UTC; three-day point-in-time recovery is available. Backup stayed in Render.

GitHub refused merge because active ruleset `Zova production guardrails` (24140009) requires `Production guardrails`, synthetic-tests and postgres-release. No bypass actors. The missing gate exists in separate unmerged PR #16 and intentionally blocks until its open requirements/evidence are resolved. Do not remove the rule, fabricate a green check, force-merge or manually deploy around it. The prior broader candidate is still local and must not be deployed wholesale. No infrastructure or billing changes were made.

Release manifest: `../zova-ux-release/docs/UX_RELEASE_20261008.md`; remote evidence: Actions run 37841005196; local downloaded artifacts: `../zova-ux-release/docs/validation/ux-release-ci-final/`. Next step is reconcile the focused UX release with the enforced guardrail release process and resolve its required evidence. The owner MFA and paid-staging deferrals in PR #16 remain relevant; they are not release waivers.

---

# Focused UX release candidate — 8 October 2026

Publication authorised. Read `docs/UX_RELEASE_20261008.md` for exact scope and rollback. This separate release excludes the broader September authentication, recovery, storage and newsletter candidate. Remote release checks and live verification are required before marking it live.

---

# Next move top-right and current-topic search — LOCAL CANDIDATE, 27 September 2026

Current increment is NOT deployed. Branch `codex/next-move-sources` in the existing `zova-strategy` workspace, based on production-equivalent 653528a / 021aad7. Read `docs/NEXT_MOVE_SOURCES_20260927.md` for details, evidence, limitations and rollback. Sources under the mirrored project remain read-only.

Implemented: top-right branded Next move; compact expandable source cards; bounded web/public-social search using public content themes; cited URLs and 14-day reported-date checks; strategy-ranked recommendations; 24-hour source expiry; explicit evergreen fallback and existing draft/approval continuity. No schema changes. Full suite 224 passed; final focused suite 43 passed including 2 additional tests. Desktop and 390/320px mobile, keyboard and generated-draft reload reviewed locally. Provider/model acceptance remains unvalidated: no local OpenAI key. No live posts, grants, charges, settings or production changes. Fresh CI/PostgreSQL and a synthetic provider search are release gates.

Rollback this increment to production-equivalent 653528a / 021aad7, retaining all data. Prior live strategy release details below remain valid; this increment does not supersede production until separately published.

---

# Strategy and Next move LIVE — 27 September 2026

User explicitly approved repository upload and deployment. PR #13 merged as 021aad77292abc95c499191789bc50c5cda69436, identical tree to validated 653528a02a53b1575509bcc05c3f8adafaaac7a3. Both candidate CI runs 36347400542 and 36347397624 passed (SQLite/PostgreSQL, synthetic restore, dependency audit and hosting image checks). PostgreSQL validation found a pre-existing concurrent-first-request limiter race; corrected without changing limits, with 22 focused local tests passing.

Render deployment dep-dasnmcc9v7es73f7jvrg confirmed Deploy succeeded / Live; service-live log at 21:24:02 BST. Fresh managed PostgreSQL export available at 21:18 BST; three-day point-in-time recovery available. Production backup was not downloaded/restored. Public health and homepage return 200; all four changed Studio JS/CSS assets match tested files. Existing signed-in browser session and saved draft 9 remained visible; Next move opens without error and purple sparkle renders in both heading and composer. Opening panel initialized an empty strategy row for the existing session; no preferences confirmed, AI calls, posts, grants or charges. No credentials/settings changed.

Release evidence: docs/validation/strategy-release-20260927.json and strategy-live-20260927.png in the local zova-strategy checkout. Provider/real-model quality and verified live trends remain unproven; rollout does not close these gaps. Rollback: retain additive tables; cancel pending series jobs before code rollback to b746bad, preserve unknown/completed outcomes and all user/media/auth/social records. Earlier candidate-only statements below are historical.

---

# Zova continuation — local strategy candidate, 27 September 2026

This candidate is NOT deployed. Current production base: b746bada82965baa8f3bf55bf04a921683134b35. Branch: codex/strategy-next-move. Workspace: C:/Users/david/.codex/.chatgpt-projects/g-p-6a8a0aa881c88191a2835a8d53316369/zova-strategy.

Read docs/STRATEGY_NEXT_MOVE_20260927.md first for the iteration log, scores, limitations and rollback, and docs/ZOVA_FEATURE_MATRIX.md for current feature status. Earlier live history remains in the original root handoff under Documents/Codex/2026-08-29/referenced-chatgpt-conversation-this-is-an.

Implemented: confirmed brand strategy separate from proposals; up to three compact Next moves; generated idempotent linked drafts; feedback; finite recurring plans; exact repeat batch approvals; fresh drafts separately reviewed; pause/cancel/time edits; privacy lifecycle and usage integration. Existing users/data/auth/media/social connections and explicit publishing approval preserved. Testing billing flags unchanged.

Validation: 203 automated tests passed (17 existing warnings), JavaScript syntax/whitespace checks passed. Local synthetic browser journey and 390x844 responsive check, no horizontal overflow; Escape returns focus to Next move. Mocked AI/providers, no live posts. Final targeted subscription-guard regression: 21 passed (2 existing warnings).

Before release: run staging PostgreSQL concurrency and worker recovery; real-model usefulness evaluations; approved provider scheduling/Story validation. Live trends are unavailable with explicit evergreen fallback. Batch TikTok settings use individual Studio review. Future content changes require an edited new series; one/future time changes are supported. Do not claim whole-product 8/10 or deploy without authorization.

Rollback: cancel pending series deliveries before returning code to b746bad; do not automatically cancel sending/unknown outcomes. Keep additive tables and completed history. Restore-test a database backup before any release.

Local git origin points to the original local checkout, not GitHub. Do not push to it. No PR or deployment created in this task.
