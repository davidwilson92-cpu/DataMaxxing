# Latest verified status - 16 October 2026

PR31 is Live as7cdb945 on Render dep-db8vpf49v7es739c6840. New Facebook consent verified with only Page list/read/manage-posts for Zova Social; final Save awaits owner permission. PR32 merged8ef1230b61fb67895dd2a2adf2446f5d5434d9cc and is Live on Render dep-db8vtgjrjlhs73betts0; health200. Required CI38888393661/38888419196 passed. Reloaded real draft27 now shows correct inbox-only TikTok settings and final Send to TikTok review, resolving observed stale frontend controls. Exact synthetic six-second video send awaits owner approval; nothing delivered yet. Shared native draft PR28 integrates main at93af22c, flags still disabled;20 focused tests pass. No native deployment.

Rollback this cache-only increment to7cdb945 without database restoration if required; older browser controls may return, so avoid TikTok submission until review mode is correct.

---

# Social beta integration evidence - 16 October 2026

Provider state:
- Instagram preserved. Existing Meta approval and owner-confirmed Post/Story delivery retained. Both Instagram routes keep their existing scopes and implementation.
- Facebook: owner authorised Page use case; saved to app1034305066042973. pages_manage_posts, pages_show_list and pages_read_engagement saved to draft review1092715846868561, not submitted or approved. Existing Instagram permissions remain approved. Public customer Page publishing requires separate review; app-role testing is not proof of general access.
- X: live client matches DataPosts app33291055. Only an obsolete Render callback was registered. Owner authorised adding https://zova-social.com/callback/x, preserving the old callback. Saved and verified; Owner authorised and connected @DataMaxxingUK. The explicitly approved text-only test was published through Studio final review and independently verified on X: https://x.com/DataMaxxingUK/status/2111033940157055189 . Draft26 is Published. Do not resend or delete this test. Images and threads remain mocked-provider evidence only. No credits purchased.
- TikTok: app7672846663509215253 is Live since7 September2026. Approved only user.info.basic and video.upload, Web platform. Direct Post disabled. Runtime TIKTOK_SEND_TO_INBOX=true confirmed. Users must finish caption/privacy/publishing in TikTok. Direct publishing, analytics/video.list, follower stats and native registration need separate approval/configuration.

Implementation:
Facebook requests its posting permission without changing Instagram-linked scopes, records actual grants and rejects missing success receipts. X requests media.write and preserves text publishing on older tokens lacking image permission. Missing X/TikTok scopes fail closed. TikTok inbox review avoids direct-only creator-info requests, requests only approved scopes, clearly labels inbox-only video transfer, binds immutable review to delivery mode, merges final upload chunk remainders, and distinguishes pending inbox delivery from completed publication. Unapproved TikTok analytics/feed/voice requests are skipped or unavailable.

Validation:
16 focused synthetic tests pass, including real local review/adapter paths with mocked HTTP, boundary chunks, actual grants, revoked/absent permissions, immutable confirmation, duplicate suppression, partial X thread timeout, Facebook missing receipt and pending/inbox/published transitions. Candidate d844afa passed CI38882996566: SQLite299 passed/1 skipped; PostgreSQL299 passed/1 skipped, synthetic backup restore, hosting image smoke test, Node suites, dependency audit and exact beta scope all passed. No production customer records or social posts changed by tests.

Deployment:
PR30 merged as786183f05619d2706f71765cd2b86d56536a87d3 and Render dep-db8v84brjlhs73be54j0 was verified Live; health200 and deployed publishing script matched. Required final CI38883251969/38883260285 passed. PR31 merged as7cdb945f9e9927d52586d9584b1b3f65705b9f38 after required CI38884308415/38884361048 passed; it removes business_management from Facebook requests only, preserving Instagram-linked scopes. Its hosting rollout still needs verification. TikTok David Wilson connected with owner approval; synthetic video is saved in draft27, not sent. Live review displayed stale direct-post privacy controls while local inbox review passed. Current follow-up versions studio-publish.js to invalidate old browser cache and asserts inbox mode through the actual context API. Twenty focused tests passed; follow-up not deployed yet. Facebook Page grant and live delivery, TikTok inbox delivery and customer Facebook approval remain outstanding. Do not call all socials beta-ready.

Shared iOS:
The same reviewed-publication adapters serve the pending shared API foundation, draft PR28. Native flags remain disabled. Integrate bounded fixes into that branch and rerun contract tests before native rollout. TikTok iOS platform is not registered; no native approval is claimed.

Rollback:
Redeploy0105751acd9ffb75dae94016548b8d25ba751ed3 without database restoration. No schema change. Preserve users/uploads/keys/sessions/publication ledger; never replay unknown outcomes. Keep additive X callback so login continues working. Do not revoke Instagram permissions. Leave Facebook submission draft until all evidence exists. Application rollback reintroduces TikTok's review bug; avoid new TikTok submissions if rollback is required.

All79 broader known gaps remain in docs/beta/deferred-register.json. Limited beta remediation is not commercial certification.
