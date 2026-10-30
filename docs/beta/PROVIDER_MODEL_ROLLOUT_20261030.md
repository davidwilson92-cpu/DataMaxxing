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

## TikTok connection verified; delivery acceptance still required

Follow-up at 11:13 UTC: the owner completed final account confirmation. Production now has new active connection26, saved at 11:12:01 UTC, with exactly `user.info.basic,video.publish`. A read-only call through the production `_tiktok_creator_info(access_token(...))` adapter succeeded at 11:13:18 UTC. Direct mode is active. TikTok returned Followers, Friends and Only me privacy choices (`FOLLOWER_OF_CREATOR`, `MUTUAL_FOLLOW_FRIENDS`, `SELF_ONLY`) and a maximum video duration of 3600 seconds. It did not return `PUBLIC_TO_EVERYONE`; do not add that choice or infer the reason without provider evidence. This supersedes the pending-confirmation status below. Final saved connection and provider-side Direct Post settings are verified; actual delivery still needs an explicitly authorised test. No video, photo or post was sent by this read-only check. Evidence: `evidence/provider-rollout-20261030/tiktok-connection-verified.json`.

Follow-up at 11:10 UTC: owner reported successful iPhone connection. Read-only production checks found TikTok OAuth started at 11:06:35 and consumed successfully, but the returned Zova PendingConnection was still unused (expires 11:17:05); no SocialConnection had been saved/updated in the preceding four hours. This establishes successful provider sign-in/return, not completion of Zova's final account confirmation. Asked the owner to confirm the displayed account in the returned Zova browser screen, or restart Connect if that screen was closed/expired. No pending payload, credential or confirmation code was exposed or reused, and no post was sent. Await actual saved connection before certifying the new grant or requesting a publishing test.

Existing connections created against the former app/mode must reconnect for production `video.publish`. The owner has now completed this on iPhone through Zova's final confirmation. Credential configuration, signed media delivery checks, saved connection and provider publishing settings are established. A separately authorised real Direct Post delivery remains unverified.

The old TikTok pending publication8 could not be resolved before the switch: read-only status check raised RuntimeError. Preserve its receipt and pending/unknown handling. Do not resend, mark it failed/published, or erase it to tidy the rollout. Reconnecting cannot retroactively turn an old sandbox/inbox receipt into a production direct-post receipt.

The approved TikTok revision explicitly describes Web only. The native app uses the shared browser OAuth/backend, but iOS platform registration/coverage is not established by this rollout. `video.list` and `user.info.stats` remain unapproved and are not requested. Do not claim TikTok analytics or general native approval is complete.

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

No new native binary was uploaded or testers notified in this turn. The server-side configuration applies to web and existing iPhone clients. Native UI fixes in the candidate still need their separate signed build/device acceptance; this rollout does not close QA24/35/42 or all 51 workbook findings. QA36's wrong-client configuration is corrected, with real reconnection still pending; QA34 remains blocked by Meta approval.

Rollback: preserve all user/media/session/social/publication records and the existing production TikTok credentials. Prefer rolling back code only to the previously healthy `2de31e19401367d909cb320986122b28093fdeb6` if a runtime regression requires it; that older runtime ignores the optional content-model route. Reverting to inbox delivery changes consent/review requirements and must be a deliberate controlled change, never a way to retry an uncertain post. Do not restore a database merely to revert application code.
