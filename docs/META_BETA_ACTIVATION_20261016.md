# Meta beta activation and verification 16 October 2026

## Current result

Meta app 1034305066042973 is published. The dashboard confirmed approval of instagram_business_basic and instagram_business_content_publish on 16 October, then confirmed the app is available for public use. These are direct Instagram Login permissions; they do not prove Facebook Page publishing or Instagram insights approval.

The bounded web fix is live: PR29 merged as 0105751acd9ffb75dae94016548b8d25ba751ed3, Render deployment dep-db8th5h7lnhs73aj2e20. No schema migration, additional permissions, charges or paid services. Existing users, sessions, encrypted connections and publication ledgers are preserved.

## Implemented

- Accept Meta's documented token data envelope and the existing flat response.
- Save permissions actually granted by Instagram. Reconnection cannot retain an old publishing grant when the replacement token has unknown or reduced permissions.
- Refresh known long-lived direct Instagram tokens during use when within seven days of expiry and at least 24 hours old. Expired tokens require reconnection. Legacy tokens without lifecycle evidence remain usable until expiry but need reconnection to establish refresh eligibility. This is demand-driven renewal, not a scheduled guarantee for inactive accounts.
- Refresh failures preserve the saved credential. A conditional database update prevents a late refresh from overwriting a concurrent disconnect or token replacement.
- Apply the same shared backend changes to PR28. Add native Post and Story tests for immutable format approval and duplicate prevention.

## Verification

| Area | Evidence | Status |
| --- | --- | --- |
| Meta approval and publication | Signed-in Meta review and publication dashboard; local screenshot docs/validation/meta-published-20261016.png | Verified live |
| Web deployment | Render exact commit and Live deployment | Verified live |
| Public routes | Health, login, signup, privacy, terms, deletion return HTTP 200 | Verified live |
| Account isolation and testing access | Signed-in fresh account shows no connections or drafts; free beta/no automatic charge | Verified visually |
| Studio, drafts and analytics | Fresh-account screens load; missing performance data prompts connection rather than inventing results | Verified visually |
| OAuth, media, publishing, scheduling and security regressions | 283 passed/1 skipped on both SQLite and PostgreSQL; restore, image smoke and exact-scope CI checks pass on PR29 c1c70d9 | Mocked/synthetic provider evidence |
| Shared native foundation | PR28 3ede54c: SQLite 305 passed/2 skipped, PostgreSQL 306 passed/1 skipped; local full run 305 passed/2 skipped | Tested, not deployed |
| Native Instagram formats | Post and Story tests pass; final implementation acbad5b passed CI38875534070 with SQLite307/2 skipped and PostgreSQL308/1 skipped plus all required checks | Tested, not deployed |
| Real Instagram login | Owner confirmed successful connection in normal Edge/Chrome on 16 October; earlier embedded-browser attempt looped before callback | User-confirmed success; app-role status and exact grants not independently inspected |
| Real publishing | Owner confirmed on 16 October that both Instagram Post and Story work; no posts sent by the agent | User-confirmed delivery for both; provider receipts not independently inspected |

## Platform matrix

| Platform/path | Beta position |
| --- | --- |
| Instagram direct | Approved and published; owner confirms successful normal-browser connection; embedded-browser login compatibility remains unresolved |
| Instagram Post/Reel | Shared reviewed publishing and duplicate guards tested with mocks; owner confirms successful live Post delivery on 16 October; individual media types not separately verified |
| Instagram Story | Separate saved/reviewed format; business-account eligibility check; shared web/native dispatch tests; owner confirms successful live Story delivery on 16 October |
| Instagram via Facebook | Existing route preserved; direct Instagram approval does not establish this route's separate permissions |
| Facebook Page publishing | Current OAuth scope lacks pages_manage_posts and publishing guard rejects missing permission. This Meta review did not approve it; do not claim ready or expand scopes without verified access |
| X | Existing integration preserved and regression tested; owner reports approval but no new dashboard/account/provider evidence this session |
| TikTok | Existing OAuth requests video.upload, while direct posting requires video.publish. Inbox versus direct mode must match approved product and grants; no new dashboard/provider evidence this session |
| Instagram analytics | Basic/media access is not evidence of approval for every insight metric; do not advertise advanced analytics based on this review |

## iOS gate

PR28 remains a draft, undeployed. Native access and queued AI stay disabled. The shared endpoints use the same reviewed publication handlers, not a separate provider implementation. Before enabling: verify database/media/secrets recovery, deploy the additive foundation with flags off, register the real Apple team/bundle and owned universal-link callback, and validate system-browser authentication, Keychain/session lifecycle, replay/revocation, device callbacks and poor-network recovery. Social connection uses the existing browser account/confirmation flow; a full native connection-management screen is not implemented. Do not ship a client secret or social token in iOS.

## Rollback and next evidence

For the focused web release, redeploy f1c7c12ed3076990b1262e7cefbd614c699f95bd without restoring or deleting customer data. Retain session/encryption secrets and publication records. Never resend unknown outcomes. Meta publication is separate from code deployment; unpublishing would restrict beta access and requires a deliberate operator decision.

Help copy still describes the old Next move recurring-drafts entry point; update it to Post options in the next UX change. Signed-in Help and Security pages load; anonymous Help requires authentication.

Normal-browser connection is now user-confirmed. Treat the embedded-browser loop as a separate compatibility issue; its underlying cause is not established. For iOS, retain system-browser authentication and validate on a real device rather than relying on an embedded web view.

Next: verify exact connected account and granted scopes; retain owner-confirmed Post/Story success and capture provider receipts during further beta testing; verify X/TikTok approved modes and Facebook permissions independently. Retain all 79 broader known gaps. This update is limited beta activation, not commercial certification.

## Provider reference

Meta Business Login documentation, inspected 16 October 2026: https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/business-login . Documents response envelope/permissions, server-side secret handling, 60-day tokens and refresh eligibility after 24 hours while unexpired.
