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

# Saved stopping point - 16 October 2026

Owner will return tonight; no scheduled reminder or background posting requested. TikTok Direct Post works in the isolated sandbox: draft1 returned Published after refreshing provider status, for @davidwilson493 with Only me visibility. Do not resend this draft. Independent viewing of the private video in TikTok remains unconfirmed.

Next session: read this handoff, check sandbox availability/session first, and have owner verify the private video on TikTok. Prepare a NEW draft for the recorded demonstration: connect account, upload original media, edit caption, show privacy/interactions/disclosures and consent, final review, owner-authorised private publication, refresh status, then show the actual TikTok post. Review recording before submitting TikTok production video.publish revision and separate public-access audit. Neither is submitted/approved yet. Production stays inbox-only; approval enables eligible customers to publish publicly from the main site. No further implementation or production activation is implied by the successful private test.

Sandbox https://zova-tiktok-sandbox.onrender.com is FREE with ephemeral SQLite/uploads; restart/spindown/redeploy can lose test state and require a fresh test login/reconnection. Auto-deploy is Off. Do not reconnect its database to production. Code/configuration evidence and recording plan are saved in docs/TIKTOK_DIRECT_POST_20261016.md; screenshots and synthetic video remain locally under social-proof/. Do not expose credentials or upload the whole proof folder. Preserve all79 known beta gaps and existing connections.

---

# TikTok recording sandbox ready for account connection - 16 October 2026

Reused existing FREE Render service zova-tiktok-sandbox (srv-d9u4joad0e5s73afpu10). Discovered it previously shared the production PostgreSQL database; changed this test service ONLY to sqlite:////tmp/zova-tiktok-recording.db, verified saved. Production users/data/keys/service unchanged. This temporary database and local uploads may be lost on restart/spindown/redeploy. Do not promise durable staging; record in one session and keep external evidence. Auto-deploy is Off to avoid branch updates resetting recording state.

Owner explicitly approved copying existing TikTok Sandbox client key/secret into this existing Render service. Configured those credentials, PUBLIC_BASE_URL and callback to https://zova-tiktok-sandbox.onrender.com, TIKTOK_SEND_TO_INBOX=false, SELF_ONLY default config (user must still explicitly select privacy), REQUIRE_SUBSCRIPTION=false, ZOVA_ENV=sandbox, and TIKTOK_VERIFIED_MEDIA_PREFIX=https://zova-tiktok-sandbox.onrender.com/media/raw/. Verified saved nonsecret values after deployment. No public post or new user grant sent.

Sandbox7672854716816082965 under TikTok app7672846663509215253 already has Direct Post and video.publish. Existing target user davidwilson493. Updated sandbox website to recording host. TikTok verified https://zova-tiktok-sandbox.onrender.com/ URL prefix using downloaded signature file; screenshot social-proof/tiktok-sandbox-prefix-verified.png. Production TikTok draft/live settings were not changed in this increment.

Dedicated branch codex/tiktok-recording-sandbox-20261016 pinned on test service, Live7fdec1573a004bd28d79ee0e54c0628461969247, deploy dep-db91mlcvk9tc73ea9df0. Only runtime change versus PR33 is static sandbox verification route. Initial CI caught CRLF digest mismatch; corrected normalised digest, CI38901929057 passes all required jobs:315 tests/1 skipped on SQLite AND PostgreSQL, restore/container/dependencies/guardrails. Local Direct Post tests16passed. Verification endpoint200 with exact signature; signup rendered and no subscription charge. Production remains cc093687 inbox-only; no broad native branch deployment.

User has been asked to create a SEPARATE Zova login at https://zova-tiktok-sandbox.onrender.com/signup then connect registered TikTok tester davidwilson493, or identify another account to add as sandbox target. Do not share passwords. Real OAuth, creator restrictions, uploaded media fetch, final review and private Direct Post outcome remain pending their connection; no ready-to-record end-to-end claim yet. Before sending anything obtain exact post/account/privacy approval. Complete provider verification, then recording; do not submit old inbox recording as Direct Post evidence. No iOS device validation performed. All79 broader beta gaps retained.

Rollback: keep test DB isolated; do not point sandbox back to production. Set only sandbox TIKTOK_SEND_TO_INBOX=true to disable Direct Post or suspend test service if requested. Keep production unchanged. Preserve any publish receipts before restarting disposable sandbox.

---

# TikTok Direct Post preparation - 16 October 2026

## Status and boundaries

Production remains on the approved inbox path (TIKTOK_SEND_TO_INBOX=true). Its live delivery was confirmed by the owner. No Direct Post grant, public-access audit approval, direct feed delivery or native iOS approval is claimed. No new real post was sent in this increment. Existing Instagram, Facebook and X connections remain unchanged. All79 broader beta findings remain open.

TikTok app7672846663509215253: created and saved a Production draft revision with Direct Post enabled and video.publish added; user.info.basic and video.upload retained. The live version still has inbox-only approval. Saved draft notes explicitly say implementation is deployed but real Direct Post evidence is pending and the old recording demonstrates inbox only. URL properties already verifies https://zova-social.com/ as a URL prefix; the separate bare-domain entry is unverified and unnecessary for that prefix.

The separate audit form at https://developers.tiktok.com/application/content-posting-api has organisation/purpose/data-field answers entered in the browser, with Building a new application selected instead of inventing a usage estimate. It is at Supporting documents, not submitted; these in-browser answers are not confirmed durable. Requires a genuine new recording of authorisation, review controls, confirmation and provider outcome. Never present synthetic tests as live provider evidence.

# Direct Post deployment evidence - 16 October 2026

PR33 is merged as cc093687bc92f5600283918d330ef70691e4216e and verified Live on Render dep-db91bkvavr4c739qd50g. Public /health and versioned Studio publishing script return200; the script contains the new Direct Post controls and policy declaration. Required hosted checks passed:315 tests /1 skipped on SQLite and PostgreSQL plus restore, container, dependency and release checks.

Production remains inbox-only. Direct Post is NOT enabled or provider-validated. TikTok production draft contains video.publish and Direct Post. Updated notes were entered and Save clicked; subsequent reload and Manage apps navigation returned Request aborted, so persistence of the latest notes could not be reverified. Earlier draft save was verified. Separate audit at Supporting documents is unsubmitted. Verified URL prefix is https://zova-social.com/; TIKTOK_VERIFIED_MEDIA_PREFIX still needs configuring and validating against hosted storage before direct testing. Do not change delivery mode or resend previous test posts.

Native PR28 includes the same server implementation. Its contract was regenerated for the additive connection_ids field (05e2c93);40 focused tests pass /1 skipped. All required hosted native checks passed in38900036915 and38900044596. Native remains disabled and undeployed. Desktop synthetic UI inspected; attempted mobile viewport override did not take effect, so mobile visual validation is still outstanding.

Remaining: isolated real Direct Post authorisation and exact-approved private test, new provider recording, reviewer access check, app revision plus public-access audit submission and approval, then reconnect for video.publish and controlled feed rollout. Existing inbox recording is insufficient. All79 broader beta gaps retained. Rollback and recording script: docs/TIKTOK_DIRECT_POST_20261016.md.

## Implementation

The shared server validates actual media duration, UTF-16 caption length, current creator privacy/interactions, explicit consent, commercial disclosure and private partnership restrictions at review and dispatch. Direct videos use PULL_FROM_URL on a configured verified HTTPS prefix. Existing inbox FILE_UPLOAD is preserved. Direct photos accept JPEG/WebP and exclude video-only interactions; no unsolicited automatic music or generated title is added. AI-generated-media labelling is an explicit selection, not inferred from AI-written captions.

Studio has no default privacy or interaction selection. It displays the current creator name, unavailable controls, optional commercial disclosure with dependent labels, Music Usage Confirmation and Branded Content Policy where applicable. A server-owned final snapshot binds the exact media/text/settings and destination. Changing destination refreshes context; changes to legal/disclosure selections clear consent. Caption editing and media preview remain available before confirmation. Pending delivery is never labelled published. Provider-confirmed inbox delivery has a distinct result label.

## Rollout sequence

1. Complete required SQLite, PostgreSQL, restore, dependency and frontend checks on the exact candidate. Review desktop/mobile synthetic evidence.
2. Integrate the bounded changes into draft shared-native PR28, keep native flags disabled; rerun its contracts. No iOS bundle registration/device evidence exists yet.
3. Deploy through normal protected release flow, keeping production inbox mode. Set TIKTOK_VERIFIED_MEDIA_PREFIX=https://zova-social.com/media/raw/ only for media URLs beneath the verified property; verify serving and expiry on the actual storage setup. If storage changes, verify its prefix separately. Do not expose private buckets to pass this check.
4. Configure an isolated, access-controlled provider test environment and approved reviewer account for Direct Post. Request/obtain video.publish, reconnect with explicit user approval, and validate actual creator_info and a specifically approved private test. Unaudited access has TikTok restrictions; never bypass them or change a personal account's privacy automatically.
5. Record the real hosted application: connect the exact TikTok account; upload creator-owned media; edit caption; show nickname, no-default privacy, disabled interactions, disclosure choices and consent; preview; confirm once; show processing then actual private provider outcome. Demonstrate photo-only interaction restrictions if claiming photos. Keep files under the portal's displayed limits. Recordings must not show passwords, tokens or unrelated personal data.
6. Replace/supplement the old inbox-only video with direct evidence. Recheck reviewer credentials, data handling and implemented behaviour. Finalise the app revision and separate audit submission only when truthful and complete, with any required terms confirmation.
7. After TikTok approves public Direct Post, switch the configured mode, ask existing users to reconnect for video.publish and run an exact owner-approved public feed test. Roll out gradually; preserve unknown-outcome no-resend protection. The old video.upload-only token cannot be silently upgraded.

## Recording narration

“Zova helps creators prepare their own original content. I am connecting my TikTok account and confirming the destination in Zova. Here is my uploaded video and editable caption. TikTok supplies the available privacy and interaction settings; none is chosen on my behalf. I can disclose my own brand or a paid partnership and label AI-generated media. Private paid partnerships are unavailable. I review the media, account, caption and policies, then explicitly confirm. Zova shows processing until TikTok confirms publication. Here is the resulting post in TikTok.”

Only narrate completed actions and an actually observed result. An inbox notification does not demonstrate Direct Post. A synthetic local UI does not prove provider approval.

## Rollback

Redeploy8ef1230b61fb67895dd2a2adf2446f5d5434d9cc without restoring databases or keys. Preserve tokens, media, drafts and publication ledger. Keep production inbox mode until audit approval; never resend an uncertain direct post. No schema migration or billing change is introduced. Stop dispatch before changing delivery mode; existing pending results must still be reconciled, not replayed.

## Sources

- https://developers.tiktok.com/docs/en/content-sharing-guidelines
- https://developers.tiktok.com/docs/en/content-posting-api-reference-direct-post
- TikTok app portal, verified URL properties and audit form inspected16 October2026.
