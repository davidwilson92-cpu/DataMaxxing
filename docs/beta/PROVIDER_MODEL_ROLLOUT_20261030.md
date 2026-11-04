# Production provider and AI rollout — 30 October 2026

Owner request: activate approved TikTok Direct Post, use Terra, and allow customers to connect Facebook through their own profile. This is a limited-beta rollout, not commercial certification. The existing 79-section deferred register remains in force.

## Live changes and verification

- Render production service `srv-d9rqg6navr4c739thoeg` now runs exact validated commit `761153c443e26f56fcaa582c4fcce29ccf29739a` (runtime identical to `0173121a24ad39b0043f0d6cb335d79d8d48c8c2`). Deployment `dep-dbi6j3cs728c73cg3gdg` succeeded; final environment-only deployment `dep-dbi6lgajnfac73cvik00` also succeeded on that same commit.
- A completed Render-managed database export at 09:51 UTC was visible before deployment. Three-day point-in-time recovery remains available. No production backup was downloaded or restored.
- TikTok app `7672846663509215253` shows Production Live and Direct Post Approved, with provisioned user access. Existing approved production credentials replaced the incorrect sandbox credentials in Render. No credentials are stored in this record.
- `TIKTOK_SEND_TO_INBOX=false`; live authorisation requests exactly `user.info.basic,video.publish` with the existing `https://zova-social.com/oauth/tiktok/callback`.
- `TIKTOK_VERIFIED_MEDIA_PREFIX=https://zova-social.com/` matches the production portal's verified URL prefix. Five existing signed media URLs, including JPEG and MP4, passed prefix validation and returned HTTP 206 to bounded range requests. Media bytes, signed URLs and customer content were not saved in this report or sent to TikTok.
- `OPENAI_CONTENT_MODEL=gpt-6.1-terra` is active for generation, rewrites, strategy/Next Move, voice and performance analysis. Intent routing/media inspection retain `OPENAI_MODEL=gpt-5-mini` under the reviewed split-model implementation. This is not a claim that every AI call uses Terra.
- A synthetic live `generate_variants` check returned a valid Facebook caption, preserving the one-off Saturday class, 10am, 12 places, GBP12 and supplied booking link without inventing a recurring offer or free trial. No draft or social publication was created by that test. The earlier four-case comparison and full regression evidence remain in `QA_REMEDIATION_20261030.md`.
- `/health`, `/login`, `/privacy-policy`, `/terms-of-service` and `/guide` returned 200 after deployment.
- Runtime billing verified: Stripe test mode, live checkout false, subscription requirement false and plan enforcement false. Hosting remains Render.
- Publication aggregates were unchanged across the initial rollout: X published2/unknown2/cancelled1; Facebook published1; Instagram published7/unknown1; TikTok pending1. No social post, deletion, resend or Instagram grant change was performed.

## TikTok Direct Post — one private video delivery verified

The owner explicitly approved TikTok's Music Usage Confirmation and one private test. The final frozen review matched the approved video, destination, caption and privacy settings; Confirm publish was clicked once. Studio automatically changed from Waiting for platform processing to Published at 16:11 UTC on 30 October 2026.

- The owner chose the existing browser Zova account and reconnected TikTok there. New active connection27 was saved at16:07:36 UTC with exactly user.info.basic,video.publish. Live publishing settings identify David Wilson @davidwilson493. The visible destination selector was verified as27 before submission.
- Saved draft75 / publication16: six-second 720x1280 H.264 silent graphic labelled ZOVA DIRECT POST TEST. Caption exactly: “Zova Direct Post test - checking our reviewed publishing flow.” Visibility SELF_ONLY / Only me; comments, Duet and Stitch off; commercial promotion and AI-media labels off. This is a programmatic integration-test graphic, not a depiction of a real person or an advertisement.
- At16:12:40 UTC a separate read-only query through the production resolve_tiktok_post adapter returned PUBLISH_COMPLETE with no failure. The saved publication is published, pending=false, requires_tiktok_completion=false. Exactly one publication record exists for draft75. This verifies Direct Post delivery without requiring completion in the TikTok inbox.
- TikTok returned zero public post IDs and no public URL for this restricted-visibility post. Studio correctly says that no public link is available. No public permalink was invented. Actual viewing on the owner's phone has not independently been observed.
- Old connection17 and the separate account's connection26 remain intact. The old pre-switch publication8 remains pending; it was not resent, reclassified or deleted. A new test does not resolve that historical receipt.

Evidence: evidence/provider-rollout-20261030/tiktok-private-published.png and tiktok-private-completion.json. The final-review screenshot, source video, inspected preview and manifest remain under .artifacts/provider-direct-test-20261030/. Video SHA256: 13615851748b9d3a7d229d911e070f80b7dda75b5af04c212d7f8ae851e60a77; 41,827 bytes,144 decoded frames and no audio tracks.

### Account matching and remaining limits

The first browser login was a separate recovery-test account. The next login was the owner's older account with connection17, while the initial newly approved grant26 belonged to another owner login. The boundary check correctly blocked the older grant. No credentials, connections, drafts or sessions were transferred across users. After the owner chose to retain the browser account, the normal TikTok authorisation and Zova final account confirmation created connection27. Draft75's attachment and caption persisted throughout. The owner explicitly approved AI processing before generation; the historical AI-was-not-used conversation entry belongs to an earlier declined attempt.

TikTok offers this account Followers, Friends and Only me; it did not return PUBLIC_TO_EVERYONE. Do not invent that option or infer the reason. This private-video test does not establish public, commercial-content, photo or native-iPhone publication acceptance. Existing users of the former app/mode still need to reconnect for production video.publish.

The approved TikTok revision explicitly describes Web only. The native app shares browser OAuth/backend functionality, but separate iOS platform registration/coverage is not established here. video.list and user.info.stats remain unapproved and are not requested; this test does not certify TikTok analytics.

Presentation follow-ups observed: Account and the destination picker show identical David Wilson labels for the retained old and new connections; Post settings earlier exposed the old raw account ID; and the branded-content privacy hint appears with commercial content off. Preserve old receipts/grants while addressing their presentation. Do not treat these as resolved by the successful delivery.

## Facebook: code supports customer-owned Pages; provider review remains open

The existing OAuth flow uses each customer's Facebook user token to call `/me/accounts`, presents the Pages that person manages, and binds the confirmed Page connection to their own Zova user/brand. There is no hardcoded requirement to publish through David's Facebook profile/Page. Personal-profile timeline publishing is not offered by this integration.

Meta app `1034305066042973`, existing review draft `1092715846868561`, still has unsubmitted requests for `pages_show_list`, `pages_read_engagement` and `pages_manage_posts`. Published app status and developer-role Page success do not establish public customer access. Existing Instagram approvals were preserved.

Saved this turn:

1. Specific usage descriptions for all three Page permissions, reflecting actual code: customer Page selection; own-Page content/aggregate engagement; explicit reviewed publishing with receipt/result link.
2. Reviewer instructions covering customer-owned Facebook login, Page confirmation, Performance and Studio publication; historical Instagram instructions/recording retained and clearly distinguished from missing Facebook evidence. Reopening the instructions confirmed persistence.
3. Meta displays required API test calls Completed for `pages_read_engagement` and `pages_manage_posts`.

Not submitted: no suitable Facebook end-to-end recording was found among the existing review videos. The three allowed-usage declarations remain unchecked. Data handling retains previous answers and still needs owner review; do not certify stale declarations or invent compliance evidence. Existing reviewer credentials also need a fresh successful access check before final submission; do not copy credentials into reports.

### Recording required for Meta

Use the live Zova website with an authorised test Page and an app-role test login while public review is pending. Record one continuous, concise journey:

1. Sign into Zova, open Account → Social accounts → Facebook → Connect Facebook.
2. Show Facebook authorisation and the Page selection, then Zova's final confirmation of that same Page by name. Keep passwords/codes out of the recording.
3. Open Performance and show the selected Page's real posts and available engagement. Do not invent metrics.
4. In Studio, create/edit a short test caption (optionally an image), select Facebook, show the final Page/content review, then publish only an explicitly authorised test.
5. Show Published and open View post to the matching post on that Page. Optionally show the existing Schedule control without sending another post.

Attach the recording to each of the three permission requests. Verify the reviewer login, review data processors/controller/request-handling answers, obtain the owner's action-time acceptance of the three usage agreements and any final legal declaration, submit, then verify the explicit receipt. After approval, test with a genuine non-app-role customer who manages their own Page. Do not add all beta customers as app admins to bypass review.

## Evidence / release limits

Evidence folder: `docs/beta/evidence/provider-rollout-20261030/` (masked portal screenshots, runtime/AI check and media-delivery result). Exact candidate CI was already green: application push41029720787 and PR41029726687; native PR41029726721. Runtime validation recorded 754 SQLite tests/2 expected skips, 755 PostgreSQL tests/1 expected skip; native42 unit/18 UI tests and Release compilation. These are not independent unique counts across both databases.

No new native binary was uploaded or testers notified in this turn. The server-side configuration applies to web and existing iPhone clients. Native UI fixes in the candidate still need their separate signed build/device acceptance; this rollout does not close QA24/35/42 or all 51 workbook findings. QA36's wrong-client configuration, real reconnection and one private web Direct Post delivery are verified; native/public/commercial-content acceptance remains separate; QA34 remains blocked by Meta approval.

Rollback: preserve all user/media/session/social/publication records and the existing production TikTok credentials. Prefer rolling back code only to the previously healthy `2de31e19401367d909cb320986122b28093fdeb6` if a runtime regression requires it; that older runtime ignores the optional content-model route. Reverting to inbox delivery changes consent/review requirements and must be a deliberate controlled change, never a way to retry an uncertain post. Do not restore a database merely to revert application code.
