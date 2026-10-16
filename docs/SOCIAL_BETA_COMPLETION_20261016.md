# Social beta integration evidence - 16 October 2026

Provider state:
- Instagram preserved. Existing Meta approval and owner-confirmed Post/Story delivery retained. Both Instagram routes keep their existing scopes and implementation.
- Facebook: owner authorised Page use case; saved to app1034305066042973. pages_manage_posts added to draft review1092715846868561, not submitted or approved. Existing Instagram permissions remain approved. Public customer Page publishing requires separate review; app-role testing is not proof of general access.
- X: live client matches DataPosts app33291055. Only an obsolete Render callback was registered. Owner authorised adding https://zova-social.com/callback/x, preserving the old callback. Saved and verified; Zova now reaches X's permission screen for @DataMaxxingUK. No grant or real publishing receipt yet. No credits purchased.
- TikTok: app7672846663509215253 is Live since7 September2026. Approved only user.info.basic and video.upload, Web platform. Direct Post disabled. Runtime TIKTOK_SEND_TO_INBOX=true confirmed. Users must finish caption/privacy/publishing in TikTok. Direct publishing, analytics/video.list, follower stats and native registration need separate approval/configuration.

Implementation:
Facebook requests its posting permission without changing Instagram-linked scopes, records actual grants and rejects missing success receipts. X requests media.write and preserves text publishing on older tokens lacking image permission. Missing X/TikTok scopes fail closed. TikTok inbox review avoids direct-only creator-info requests, requests only approved scopes, clearly labels inbox-only video transfer, binds immutable review to delivery mode, merges final upload chunk remainders, and distinguishes pending inbox delivery from completed publication. Unapproved TikTok analytics/feed/voice requests are skipped or unavailable.

Validation:
16 focused synthetic tests pass, including real local review/adapter paths with mocked HTTP, boundary chunks, actual grants, revoked/absent permissions, immutable confirmation, duplicate suppression, partial X thread timeout, Facebook missing receipt and pending/inbox/published transitions. Candidate d844afa passed CI38882996566: SQLite299 passed/1 skipped; PostgreSQL299 passed/1 skipped, synthetic backup restore, hosting image smoke test, Node suites, dependency audit and exact beta scope all passed. No production customer records or social posts changed by tests.

Deployment:
Code not deployed at this record. X callback correction is live; Facebook use case and review draft saved. Provider grants and delivery receipts remain outstanding. Do not call all socials beta-ready from mocks alone.

Shared iOS:
The same reviewed-publication adapters serve the pending shared API foundation, draft PR28. Native flags remain disabled. Integrate bounded fixes into that branch and rerun contract tests before native rollout. TikTok iOS platform is not registered; no native approval is claimed.

Rollback:
Redeploy0105751acd9ffb75dae94016548b8d25ba751ed3 without database restoration. No schema change. Preserve users/uploads/keys/sessions/publication ledger; never replay unknown outcomes. Keep additive X callback so login continues working. Do not revoke Instagram permissions. Leave Facebook submission draft until all evidence exists. Application rollback reintroduces TikTok's review bug; avoid new TikTok submissions if rollback is required.

All79 broader known gaps remain in docs/beta/deferred-register.json. Limited beta remediation is not commercial certification.
