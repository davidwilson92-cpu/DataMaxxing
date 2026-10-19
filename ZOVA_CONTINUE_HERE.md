# Latest owner correction and iPhone account mismatch — 19 October 2026

**Theme source of truth:** Studio, Drafts and Performance must be plain light/white. Account and connection/sign-in intermediary pages stay near-black/violet. This overrides earlier global dark entries below. Live server72ad0573da850fb472c6b47bea6966f9e06d7223, Render dep-dbb1a7ff3r2c73fth8j0,14:03:25 BST. Live core3 white and connection page dark inspected. Application39256612072 passed485/1 skipped on both databases plus release checks. Native light/dark conditional source is committed; validation39256385114 pending at this entry.

**New owner evidence:** native handoff offers an email the owner says is not theirs. The prompt obtains it from the bearer device session's User record, never the browser cookie. Do not presume this establishes cross-account leakage or a typo. Asked for the correct Zova email; answer pending. Do not change emails, merge accounts, transfer drafts/connections or approve this identity. Instagram screenshot shows native Instagram loading skeleton before callback; phone still runs7 with the old embedded browser route. Normal-browser Instagram fix remains undelivered because existing Codemagic cannot load branches/workflows. No successful new binary upload. Do not tell owner to install8.

**Bounded account recovery candidate:** browser handoff explicitly distinguishes Zova from Instagram identity; wrong-account action consumes only this one-use ticket without accepting it, issuing a cookie, changing browser/native identity or revoking grants. Instructions return to app Account/sign out. Account email and existing Sign out moved outside collapsed categories. Future native login requests an ephemeral auth browser so Safari's remembered Zova identity is not inherited. Existing browser proof, owner/purpose/session/replay protections retained. Focused synthetic tests42 passed, including two-account cancellation/no-cookie/replay and wrong-purpose cases. Native validation and full application checks must finish before release claims. User's real account identity and actual phone/provider flow remain unverified.

**Rollback:** latest currently live72ad057 retains light-core preference. Account recovery candidate has no migrations; revert its bounded code changes to72ad057 if necessary. Never restore stale customer data or resend unknown publications. All79 wider beta gaps remain. TestFlight7 is still the only delivered beta. Preserve separate Zova Market, all users/data/uploads/grants, both Instagram routes, explicit posting approvals and disabled charges.

---

# Dark product UI live; iPhone Instagram update validated but signing blocked — 19 October 2026

**Website/shared screens:** a4070430496338c70b44d8132fb4a2023ef6049d is deployed. Render dep-dbb0ipijnfac739e8dug,19 October13:13:26 BST,51.9s. Earlier9b13289 deployment dep-dbb0gjff3r2c73fqkv10 also succeeded. Public health/login/native-config200; deployed night CSSv20261019-3 and Account JS match the reviewed files. Live signed-in Studio, Account, Drafts and Performance inspected; no messages, posts, grants or customer settings submitted. Auto-Deploy remains off; main is older.

**Delivered UI:** black/violet product palette replaces pale/pink gradients; Account is five expandable categories (details, voice, socials, security/privacy, plan/help). Hash links and save errors open the correct category; voice saves return to open preferences; native socials-only refresh still preserves unsaved settings. Studio has + New post beside Zova, smaller Next move, compact workspace/header, clearer composer prompt. Welcome hides on focus; mobile weekly summary hides while typing. Existing conversation, drafts, uploads, approvals and billing testing settings preserved.

**Phone acceptance:** owner screenshots show Studio loaded in build7, so the earlier bootstrap blocker is accepted as repaired on the phone. Do not ask again whether7 opens Studio. Instagram remains unverified: direct connection starts302 at11:14,11:31,11:42 BST, with no direct callback in the inspected four-hour logs. Asked owner for the stopping screen/error. No token exchange failure was observed. New native implementation opens the same bounded, purpose/session-bound Instagram handoff in the normal browser, where the owner previously reported success, and refreshes connection presentation when the app becomes active. Other platforms keep their existing sheet. No grant reset, reauthentication removal or approval bypass.

**Native candidate:**8d602a5674592c0625e9ca8e62a6d04fcc0a0146 adds the normal-browser route and dark native canvas/status appearance with readable violet links. CI39250881721 **success**:16 unit tests,1 welcome UI test, release compilation. New Instagram routing test passed; real WebKit cookie bootstrap/error/export tests retained. Simulator welcome screenshot reviewed; its build1 label is a simulator build, NOT a new TestFlight release. Application39250888058 success485 passed/1 skipped each SQLite/PostgreSQL, plus backup restore/container/dependencies/exact scope. Deployed a407043 also passed39250027919 with the same counts; native-only palette tweak does not require another web deployment. Superseded/duplicate native jobs were cancelled, not counted as passes.

**Remaining delivery blocker:** Codemagic's existing app6ad5cbbeadaac76a4f1f8525 cannot load branches/workflows and shows “Oh no! Looks like something broke down.” Reproduced via settings, last build and Applications/start-build after refresh. No new signed build was started/uploaded. **0.1.0(7) remains the latest delivered TestFlight build**; do not tell the owner to install8. Resume in existing Codemagic app when service recovers; select codex/ios-beta-20261019/current reviewed source, reuse zova-social-testflight profile, existing distribution certificate and zova-testflight Apple integration. No secrets exported, new auth grants or paid resources created to bypass this. Upload/internal group assignment and real iPhone Instagram/keyboard retest remain. Interim owner option: connect through the regular browser on zova-social.com and reopen the app; do not claim this has just been retested.

Evidence under ignored social-proof/: instagram-precallback-attempts.txt, codemagic-branch-loading-block.png, dark-release-preflight.json, account-dark-live.png, studio-dark-live-focused.png, drafts-dark-live.png, performance-dark-live.png, ios-dark-validation/ios-test-attachments/. Updated feature matrix and docs/IOS_BETA_READINESS_20261019.md distinguish implementation, tests and delivery. PR34 remains draft; not commercial certification. All79 wider beta gaps retained.

**Rollback:** redeploy pre-update2bce283476563ef399f1afe413aee40abe2e65c2 / dep-dbaulsrrjlhs73aorpsg and keep build7. No migrations in this update; do not drop tables, restore stale writes or replay pending/unknown publications. Existing users, PostgreSQL, uploads, encrypted connections, both Instagram routes, explicit approvals and disabled charges remain.

---

# iPhone feedback: dark product theme and grouped Account — 19 October 2026

Owner screenshots now show Studio loaded on the phone: build7 bootstrap acceptance is observed. This does not verify social connections or every native feature. New bounded candidate: shared near-black/violet product theme, grouped Account settings with deep-link/save-error reveal, + New post beside the brand, compact Next move/header, hero hidden on composer focus and mobile weekly summary hidden while typing. Native shell/background/status appearance also changes to dark; needs a replacement TestFlight binary. Existing forms, workspace links, native socials-only refresh, drafts and immutable approvals preserved.

Instagram remains an open provider journey defect, not falsely resolved. Production logs show /connect/instagram200 then /oauth/instagram/start302 at11:14,11:31 and11:42 BST, **no callback** in the four-hour inspected window. This narrows the observed failure to before return to Zova; no token-exchange failure is evidenced. Asked owner where it stops and the displayed message. Do not disconnect accounts, change grants, remove reauthentication or weaken state/session protections to guess at a fix. Real phone/provider retest still needed.

Validation in progress:45 focused Python tests passed;5 Node native/account/focus cases passed, syntax and diff checks clean. Synthetic loopback phone previews used disposable SQLite/users and no provider keys. Preview helper under ignored social-proof is local only, not product source. Exact application/PostgreSQL and native CI, deployment and new TestFlight status must be recorded before release claims. All79 broader gaps remain tracked. Rollback runtime to2bce283 / dep-dbaulsrrjlhs73aorpsg; build7 remains previous native binary. No migrations or customer data changes.

---

# Replacement iPhone beta7 released; phone acceptance pending — 19 October 2026

Owner confirmed build5 installed and failing. Do not repeat the version5 question or claim its origin-header patch fixed the phone. Production logs confirmed /mobile/web-session403 after build5. Exact device header mismatch was not captured; the new implementation removes the failing WebKit POST rather than claiming the simulator reproduced every phone condition.

**Zova Social0.1.0(7) is now Testing** in the existing private group with1 invitation. Apple UUIDdf822ba2-979a-4de9-aa56-481774dbab71, uploaded11:06 BST. Signed source2bce283476563ef399f1afe413aee40abe2e65c2; Codemagic6ad5ea777550aed81090148a uploaded successfully. Build6 failed compilation before upload;7 is the intended replacement. Owner asked to Update, fully close/reopen and confirm Studio. Actual phone acceptance is still pending; no unsupported working-device or commercial-ready claim.

Production2bce283 is Live on Render dep-dbaulsrrjlhs73aorpsg (11:03 BST,1m09s). Native URLSession redeems an owned, active, one-use ticket with bearer at /api/v1/native-web-session; receives one Secure/HttpOnly session cookie and a bounded destination. Swift validates and installs the cookie in WKHTTPCookieStore before a plain GET /studio. No access/refresh token enters WebKit or a URL. Existing session/purpose/owner/version/expiry/replay/revocation checks and browser origin protections remain. Legacy clients/browser handoffs preserved. Actual Coordinator rejects generic/HTTP JSON error documents without hiding JSON file exports; welcome shows build number.

Validation: application39234304434 and test-only39235234636 green,483 passed/1 skipped each SQLite/PostgreSQL plus restore/container/dependencies/scope. Native39235234656 **success**,15 unit tests including real cookie-first GET and production error/export policy,1 welcome UI test and release compilation. Test-onlyb10bd55e701dd03b4acdab13b86ce579fef37fe6 corrected the URLProtocol harness to read streamed bodies; production Swift and project settings exactly match build7 source2bce283. Earlier harness crash was not waived. Public health/login/signup/config200; native-web-session without bearer401/no cookie. Proof: social-proof/ios-native-cookie-live-preflight.json, native-cookie-ci-tests.txt, native-cookie-bootstrap-live.png, testflight-build7-testing.png.

No customer/profile/draft/upload/social grant changes or real posts/charges. Existing79 beta gaps retained; separate Zova Market app untouched. Draft PR34 remains pending physical acceptance. Read docs/IOS_BETA_READINESS_20261019.md. Rollback server to a9398b2 / dep-dbau7ce1egvs73c5jfsg if needed (preserves data but new app bootstrap route then unavailable); no schema rollback. Auto-Deploy remains off while main is older. Do not deploy broad PR28.

---

# Confirmed build5 device blocker; native cookie bootstrap in validation — 19 October 2026

Owner explicitly confirms0.1.0(5) installed and still sees raw origin-protection JSON. Do not ask for the build number again. Production logs show POST /mobile/web-session403 at10:46:07,10:46:31 and10:49:22 BST after the first repair. Exact device header mismatch is not captured, so do not pretend the simulator reproduced every phone condition. Existing build5 is not accepted as working.

New candidate2bce283476563ef399f1afe413aee40abe2e65c2 replaces the app's WebKit POST bootstrap: native URLSession uses bearer+one-use owned ticket to redeem /api/v1/native-web-session, parses the one Secure/HttpOnly cookie, installs it in WKHTTPCookieStore, then loads ordinary GET /studio. Access/refresh tokens never enter WebKit. Cookie remains bound to the originating revocable session; endpoint rejects web-cookie-only authority, wrong session/purpose, expired/reused tickets and cross-origin requests. Legacy WebKit/browser handoffs remain compatible; no origin protections removed. Actual Coordinator now rejects JSON even if response is not HTTPURLResponse, and cannot mark /mobile/web-session ready. Visible welcome build label added.

Local38 handoff/lifecycle tests passed before final single-cookie header adjustment. Application39234304434 passed483/1 skipped on both databases plus release checks. Native39234291707 exposed a forced unwrap in the new test harness reading URLProtocol.httpBody (iOS supplies httpBodyStream), not product code; corrected test-onlyb10bd55. New native39235234656 is running; application39235234636 is green. Production iOS source is unchanged between2bce283 andb10bd55. Earlier native compile caught a SwiftUI version-label type-check error, fixed4b03567; export attachment compatibility protected2bce283. Replacement signed iPhone build started in existing Codemagic account; capture actual new build URL/status before claims. Production2bce283 is now Live, Render11:03 BST/1m09s, public health/login/signup/config healthy; native-web-session without bearer returns401 with no cookie. See social-proof/ios-native-cookie-live-preflight.json. The first signed replacement attempt6 failed on the version-label compile error before upload. Corrected signed build7 uploaded successfully (Codemagic6ad5ea777550aed81090148a), Apple UUIDdf822ba2-979a-4de9-aa56-481774dbab71, Ready to Test but not assigned while the final native run is pending. Build7 code is2bce283; test-onlyb10bd55 does not require another binary. Need full native cookie-first GET and production Coordinator tests, exact application/PostgreSQL/restore/container/dependency checks, then deploy and assign processed replacement to private group. Owner phone retest required; no unsupported success claim.

---

# iPhone Studio handoff repair released — 19 October 2026

Owner's build4 screenshot exposed a real initial-navigation403, not an installation failure. **Replacement Zova Social0.1.0(5) is now Testing**, manually assigned to Zova Social Internal Beta with1 invitation. Apple build UUID77e6529f-aefc-4d7c-bb30-441e60f069ff; signed source671bbdd8df5e1324158391db63053d6be84b9149. Production native sources are identical in latest test-onlyb9dcd32. Ask owner to Update in TestFlight, fully close/reopen and confirm Studio. Physical-device confirmation is still pending; do not claim it already works on the phone.

Backend a9398b2f8a7718f372c7bdfdffc4534aa9d60f6e is Live on existing Render service (10:32 BST,53.4s). Scoped fix: non-simple native header on initial one-use ticket POST; opaque origin allowed only for this exact marked exchange. Hostile concrete origins, unmarked opaque requests and unrelated mutations remain blocked. No CORS grant. Ticket expiry/purpose/ownership/revocation/replay checks preserved. iPhone intercepts HTTP errors instead of rendering raw JSON.

Required checks completed: native39231451448 **success**,12 unit tests including actual WebKit network POST/header/body/303/session-cookie (4.401s),1 welcome UI test and release iPhone compilation. Application39231451464 **success**,480 passed/1 skipped each SQLite/PostgreSQL; restore/container/dependency/scope gates passed. Earlier loopback compile/timeout attempts failed and were corrected, not waived. Live probes in social-proof/ios-webkit-origin-live-fix.json; actual WebKit evidence ios-webkit-ci-network.txt; Apple release screenshot testflight-build5-testing.png. No user/social/upload data changes, no posts/grants/charges. All79 broader gaps retained. Draft PR34 remains pending device acceptance.

Read docs/IOS_BETA_READINESS_20261019.md for full matrix/history. Rollback server to f47e1be preserves data but restores the known old-client origin blocker; no schema rollback. Do not deploy broad PR28 or enable Auto-Deploy while main remains old. Do not overwrite separate Zova Market app.

---

# iPhone beta first-device blocker — 19 October 2026, 10:24 BST

Owner installed build4 and reported all tabs showing JSON403: Open Zova directly and try again. This is a confirmed release blocker; build4 availability was not proof of working Studio. Reproduced public POST /mobile/web-session with opaque Origin:null; SecurityMiddleware blocks the initial WebKit navigation before consuming the one-use ticket. Fix541ca62 adds a non-simple X-Zova-Native-Handoff:1 header to the native request and allows opaque origin only on the exact POST ticket exchange with this marker. Explicit hostile origins and all other routes stay protected; CORS not enabled; actual one-use,60s, purpose/session/owner checks remain required. Native now intercepts HTTP errors instead of rendering raw JSON.

Candidate671bbdd8df5e1324158391db63053d6be84b9149 adds a real WebKit loopback POST/redirect-cookie integration test. Local35 native handoff/lifecycle tests pass, including reproduced failure, fixed exchange, replay and hostile-origin boundaries. Required hosted validation39230191672/application and39230191657/native is running. New signing/upload job https://codemagic.io/app/6ad5cbbeadaac76a4f1f8525/build/6ad5e2be7550aed81090123e started. Do not distribute a new build until actual WebKit test and release checks pass; do not call the device issue fixed until owner retests the updated build. Production is now a9398b2 / Render Live,53.4s; public synthetic probes verify marked opaque-origin exchange reaches401 ticket validation, unmarked/hostile remain403 and no CORS grant. Apple processed build5 UUID77e6529f-aefc-4d7c-bb30-441e60f069ff (native source671bbdd; later commits change tests only). It is Ready to Test but not assigned to the group yet. Actual WebKit loopback test compiled but timed out during cold startup; timeout/diagnostics corrected in test-only252a1c3/b9dcd32. Await latest native run before distribution. Do not treat incomplete loopback checks as passing.

---

# iPhone internal beta available — 19 October 2026

Zova Social 0.1.0 (4) is uploaded, processed and **Testing** in App Store Connect. Private group Zova Social Internal Beta has one tester, David Wilson, invited at 10:08 BST. Apple app ID6824416979 / bundle com.zovasocial.app / team7B4W8RN6GX. This is separate from Zova Market: never overwrite that app. Native binary source16fbb9a8e168d774a130f5cecfcc266928960141; build UUIDe5b9c889-61cb-463a-b0b0-fb3cdfe744ef. Build3 is not distributed. Owner authorised registration, signing and internal upload; no public App Store submission.

Current worktree: C:/Users/david/.codex/.chatgpt-projects/g-p-6a8a0aa881c88191a2835a8d53316369/zova-ios-beta, branch codex/ios-beta-20261019, draft PR34. Read docs/IOS_BETA_READINESS_20261019.md first for evidence, feature matrix and rollback. Backend candidate f47e1be540f167f6bf6594318dde56f3a107d822 includes the final native Account refresh preserving unsaved edits; Render deployment dep-dbats96q1p3s73d3c2ig reports Deploy succeeded | Live, duration46.9s, verified at10:11 BST. Its native tree matches build4. Main remains older; specific-commit deployment disabled Auto-Deploy deliberately. Do not enable it blindly or deploy broad PR28.

Exact f47 checks green: application CI39225907537 and39225914327, native CI39225914321. Application476 passed/1 skipped on SQLite and PostgreSQL; synthetic backup/restore, container, dependencies and release guardrails passed. Native11 unit tests,1 welcome UI test and release compilation passed; JS native refresh3 tests passed. Initial Apple upload exposed an iPad orientation mismatch; fixed explicit target family and added actual IPA metadata regression gate. Later build4 is Apple's accepted final build.

Production native flag, exact callback and Associated Domains are configured. Verified existing web account and Facebook/TikTok/X connections remained intact; Instagram is not connected in that checked account. No social grant or post changed. Render database recovery shows3-day PITR and a completed logical export created09:03 BST; no production restore or data download. Physical iPhone sign-in, Studio/media/keyboard/VoiceOver/provider-return checks remain pending user installation. All79 wider beta gaps retained; no commercial certification, charges or subscription enforcement.

---

# TikTok public-access audit submitted — 18 October 2026

Owner approved the final Direct Post audit declarations. Accepted the three displayed declarations and submitted the prepared audit for app7672846663509215253 with the reviewed3m51s/4.65MB merged video. TikTok explicitly confirmed: “Your Application to request access to Content Posting API has been submitted!” It states an expected response in2-4weeks and directs checking Manage apps for status. Evidence: social-proof/tiktok-final-1810/audit-submitted.png and audit-submitted.txt. This is submission confirmation, not approval.

Both outstanding requests are now submitted: app revision/video.publish is In review; separate Content Posting API public-access audit is submitted. Await TikTok decisions. Production remains inbox-only; do not activate Direct Post or infer scope upgrade from submission. After both required approvals, verify live permissions, reconnect for video.publish with the account owner's consent, and run a specifically authorised public publishing test before controlled rollout. No real post, production deployment, grant change, billing or iOS rollout occurred in this submission step. All79 broader gaps retained.

---

# TikTok review package and app submission — 18 October 2026

Owner authorised merging/trimming/compressing the main v2 recording and the commercial-content addendum, final review, and submission. Final video: C:/Users/david/Videos/Zova TikTok Direct Post - review package 1810.mp4; 231.37 seconds, 4,648,050 bytes, 1920x960 at15fps, AAC audio retained. SHA256 eb082a3f43bcf0338a8ed96f379acd979af713e822f2aacd798c9c5ca2097a72. Full video/audio decoding passed; key scenes and boundaries visually reviewed. Kept main0-112s,123-190s,202-221.166633s;4s labelled supplement transition; addendum49-78.207979s. Cuts remove waiting/repeated drafting; no fabricated provider outcome. New recording supplement starts3:22. Local evidence/manifest under social-proof/tiktok-final-1810/.

App7672846663509215253 production revision successfully SUBMITTED and portal shows In review. New combined video attached; old approved inbox recording retained to evidence existing video.upload. Notes explain video.publish, Login Kit/user.info.basic, separate test host, private test outcome, commercial controls, production inbox-only until approval and no native iOS submission. Callback, existing scopes and production service were not changed. Website/legal pages and sandbox signup/login each returned200. No new real post. Actual reviewer-account login and reviewer TikTok sandbox allowlisting have not been tested; notes truthfully state that Direct Post testing requires a registered sandbox tester and do not invent credentials or claim unrestricted reviewer access.

Separate Content Posting API public-access AUDIT is fully populated with the new video and code-checked database field description, but NOT SUBMITTED. Browser tab13 is at Review with all three legal declarations unchecked. Owner has been asked for action-time approval to accept Developer Terms/Production-use compliance, exemption of TikTok reviewer access from Zova terms/policies, and truthful facts declaration. Await reply; do not claim audit submitted or TikTok approved. Draft form persistence across closing/reloading is not guaranteed; local audit-review.txt and audit-declarations.png preserve answers. Existing app review tab12 shows In review. Maintain those tabs for continuation.

After owner approves declarations: tick the three checkboxes on the audit Review page, continue submission, verify an explicit receipt/success state, capture screenshot and update this handoff. If another legal declaration or CAPTCHA appears, use the required action-time confirmation. No charges, public posting, production-mode switch or iOS rollout authorised by submission. All79 beta gaps remain tracked.

---

# Sandbox publication verified — 18 October 2026, 21:17 BST

Owner requested “Publish updates”. Deployed exact tested runtime 1bd3b9486ea79c82413978c07e7d82a4c26ef52c to zova-tiktok-sandbox only (srv-d9u4joad0e5s73afpu10). Render deployment dep-dbaiictg1s2s73c85sf0 reports Deploy succeeded | Live, duration37.6s. Independent release preflight confirmed exact-commit CI39161889443 green, documentation-only HEAD and all79 known gaps retained. No production deployment, real social post, grant, billing change or native rollout.

Before restart, saved read-only draft1/publication-1 UI text and screenshot under social-proof/sandbox-publication-1-before-1bd3b94.{txt,png}. It still showed Outcome unconfirmed; no authoritative receipt was recoverable from this UI. This preserves visible evidence, not a database/uploads backup. Do not resend or reinterpret that submission. Sandbox SQLite/uploads remain ephemeral.

Post-deploy checks: /health and /login return200; all four versioned Studio assets (studio.js, studio-state.js, studio-publish.js, studio-design.css?v=20261018-media) match the exact tested candidate after newline normalization. Browser refresh of sandbox Studio returns the sign-in screen, so no new signed-in/model/provider result is claimed. Prior tests:440 passed/1 skipped each SQLite/PostgreSQL plus restore/container/dependency/frontend and scope gates; synthetic desktop/mobile attachment evidence retained. Local release evidence: social-proof/sandbox-release-1bd3b94.png and sandbox-release-1bd3b94-checks.json.

Next: owner signs in again and tests a fresh caption/video draft; sent video should appear on the user conversation turn with an empty composer. Sandbox permits private Only me testing; third-party paid partnerships remain unavailable pending TikTok approval. Do not resend old unknown publication1. Keep production inbox-only unchanged. Operational callback-query log redaction and all79 wider gaps remain tracked.

Rollback: manually deploy exact2fa13f72009fa4629129070c14b8e15fa9f73631 to this sandbox only. No schema rollback; older code ignores additive message/retry metadata. Preserve durable receipts and unknown outcomes; never replay submissions. A sandbox restart can reset temporary users/uploads/connections again.

---

# Sent media, first-caption creation and TikTok outcome repair — 18 October 2026 (pre-release evidence)

Branch codex/studio-media-tiktok-results-20261018 builds on deployed sandbox 2fa13f7. Owner reported publication-1 unconfirmed after commercial disclosure and video remaining in composer. Live sandbox draft1 remains needs_review/unconfirmed; the old adapter discarded the underlying exception and receipt details, so its exact cause cannot be recovered from the existing result. Never reclassify it as failed or resend without authoritative evidence. No provider post was sent during this work. Owner subsequently signed in: live draft2 showed “Post this shlop” followed by “Create a draft first…”, reproduced and now handled by proposing a first caption (never implicit publication or agreement).

Sent attachments now live on the user turn with playable previews, while workspace active media remains the authority for AI/review/publishing. Server rebuilds previews from owned same-brand records; client URLs are ignored. Removal from the active post retains historical preview; deleted uploads show unavailable. Additive conversation/retry metadata only; no migration. Changed media/source link blocks retrying an old request silently against new content. Synthetic desktop1280x720 and mobile390x844 showed no composer video after send/reload, retained playback, no horizontal overflow; mobile composer196px. Screenshots: social-proof/studio-sent-attachment-desktop-20261018.png and studio-sent-attachment-mobile-20261018.png.

TikTok adapter now records pre-send, requested, rejected and accepted receipt stages. Documented explicit init rejection becomes Failed with an allowlisted explanation; timeouts/ambiguous responses stay unknown. Receipt-bearing interrupted work is reconciled without resend. Conditional updates bind checkpoints, recovery and poll completion to the exact reviewed attempt; late workers/status responses cannot overwrite or send a replacement attempt. Worker recovery preserves receipts and does not let old receiptless unknowns starve pending work. Known processing failure reasons are safe mapped messages; raw provider errors/tokens are not retained.

ZOVA_ENV=sandbox now makes its private-only restriction explicit in settings and server validation, even when creator_info lists wider choices. Own-brand promotion differs from third-party paid partnership: the latter requires Everyone/Friends and cannot be sent from this unaudited test app. Provider options remain displayed without a default; unavailable test choices are disabled. Approval remains external; no grant/audit/production changes. Production stays inbox-only; native branch remains undeployed. All79 wider beta gaps retained. Live access logs still include OAuth callback query strings; preserve the operational redaction follow-up without copying credentials into evidence.

Runtime candidate 1bd3b9486ea79c82413978c07e7d82a4c26ef52c is pushed. Hosted CI39161889443 passed all required jobs:440 passed/1 skipped each on SQLite and PostgreSQL, synthetic backup restore, container build/smoke, frontend planning/lifecycle checks, dependency audit (no known vulnerabilities) and exact beta scope. Independent review caught and closed three publication concurrency races; their interleaving regressions pass. The exact “Post this shlop” owned-video API/client case creates a caption with zero review/publication/schedule records. A final extra browser screenshot for that phrase was unavailable because CUA returned no browsers; the earlier attachment desktop/mobile visual evidence remains valid. No new live-model/provider result is claimed.

At validation time sandbox remained2fa13f7 / production unchanged; see the release record above for deployment. Sandbox SQLite/uploads are ephemeral. Rollback for this candidate is exact2fa13f72009fa4629129070c14b8e15fa9f73631; older code ignores additive message-media and retry snapshot JSON. Preserve receipts and never replay unknown submissions.

---

# Sandbox release verified — 18 October 2026

Owner requested publish. Deployed exact runtime 2fa13f72009fa4629129070c14b8e15fa9f73631 to the existing Free TikTok sandbox only. Render deployment dep-dbai30rrjlhs73akkom0 reports Deploy succeeded | Live (18 October, 20:44 BST). Required hosted CI39146945668 passed on that exact commit: 359 passed / 1 skipped each on SQLite and PostgreSQL, synthetic restore, container build/smoke, dependency audit and exact beta scope. Independent release review confirmed the bounded change set and all 79 known gaps retained.

Post-deploy checks: /health and /login return 200; versioned studio-state.js and studio-design.css match the tested candidate after newline normalization. Browser /studio correctly redirects to sign-in with no active sandbox session; the signed-in/provider path was not repeated after deployment. Pre-release synthetic desktop/mobile/reload/retry/keyboard/fork checks remain the functional evidence. Local evidence: social-proof/sandbox-release-2fa13f7.png and sandbox-release-2fa13f7-checks.json.

Production zova-social.com remains unchanged and TikTok inbox-only. No real social post, grant, billing change or native rollout. Sandbox remains isolated and ephemeral, auto-deploy Off; it may need a fresh Zova login and TikTok connection. Public Direct Post approval/audit remains pending; private sandbox cannot publish a paid partnership. Do not resend old test drafts. Next: owner signs into the sandbox and retries the paid-partnership caption/review demonstration with a new draft; acceptance/public posting restrictions remain in place.

Rollback: manually redeploy sandbox 89e7cf716d82f358d52515b58313862f0258c7eb. No schema migration; older code ignores pending_message metadata. Preserve any receipts/evidence before a restart, never point sandbox at production storage or replay posts. Source branch is codex/studio-send-recovery-20261018; the Render configured branch remains codex/tiktok-recording-sandbox-20261016 with auto-deploy Off, so future releases must select the intended exact tested commit.

---

# Studio sent-message and TikTok drafting correction — 18 October 2026 (pre-deployment evidence)

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

WebKit regression outcome: latest test-only b9dcd32 / native run39231451448 completed the12 unit tests (including real WebKit POST/header/body/303 redirect/session-cookie) and welcome UI test successfully; release compilation was running at this entry. Actual network test passed4.401s. Earlier15s timeout is recorded as a failed attempt, not a passing result. Evidence: social-proof/ios-webkit-ci-network.txt. Application39231451464 passed480/1 skipped on both SQLite/PostgreSQL with restore/container/dependency/scope gates. Final build5 source671bbdd has identical production native sources to b9dcd32; test-only changes require no new binary.
