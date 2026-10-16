# TikTok Direct Post preparation - 16 October 2026

## Status and boundaries

Production remains on the approved inbox path (TIKTOK_SEND_TO_INBOX=true). Its live delivery was confirmed by the owner. No Direct Post grant, public-access audit approval, direct feed delivery or native iOS approval is claimed. No new real post was sent in this increment. Existing Instagram, Facebook and X connections remain unchanged. All79 broader beta findings remain open.

TikTok app7672846663509215253: created and saved a Production draft revision with Direct Post enabled and video.publish added; user.info.basic and video.upload retained. The live version still has inbox-only approval. Saved draft notes explicitly say implementation/evidence are pending and the old recording demonstrates inbox only. URL properties already verifies https://zova-social.com/ as a URL prefix; the separate bare-domain entry is unverified and unnecessary for that prefix.

The separate audit form at https://developers.tiktok.com/application/content-posting-api has organisation/purpose/data-field answers entered in the browser, with Building a new application selected instead of inventing a usage estimate. It is at Supporting documents, not submitted; these in-browser answers are not confirmed durable. Requires a genuine new recording of authorisation, review controls, confirmation and provider outcome. Never present synthetic tests as live provider evidence.

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
