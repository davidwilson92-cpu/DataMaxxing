# Intuitive social connections release

Based on deployed main 19227834753838ecc59dfb32e9169ece8b690fb1. This isolated release excludes the larger uncommitted product/security changes in the original worktree.

## Intended journey

Zova email/password → Zova workspace → choose a social account → read the platform-specific explanation → continue to that platform → grant permissions there → return to the same Zova workspace and check the connected identity.

- Instagram explicitly offers two methods, as requested by the owner: direct Instagram Login with instagram_business_basic and instagram_business_content_publish; or Instagram through Facebook with a linked professional account and the separate instagram_basic/instagram_content_publish scopes. Missing direct credentials never trigger a silent fallback; the user chooses Facebook themselves.
- The standalone Facebook button connects Pages only and does not request Instagram scopes. The explicit Instagram-through-Facebook button records a separate OAuth intent and connects only linked Instagram accounts, not Facebook Pages. A Facebook route never downgrades an existing active direct Instagram grant. Existing connection rows and encrypted tokens are preserved. The retained Facebook Page scopes do not include pages_manage_posts: Facebook publishing approval remains a separate requirement, not solved or promised by this login release.
- TikTok authorisation requests video.upload, not video.publish, consistent with the previously agreed upload-to-inbox review scope. Existing grants are not revoked or migrated.
- X uses its existing X authorisation flow.
- Both Account and onboarding share the same connection descriptions. Existing Facebook-based Instagram connections are explicitly labelled.
- A signed-out visitor returns to a safe connection explanation after Zova login, never directly into an OAuth grant. Unknown/external next destinations are discarded.
- OAuth callbacks with a code must match the signed-in Zova user who created the short-lived, single-use state. Provider errors are not reflected into the page. Cancel/failure paths return to the appropriate workspace screen; no Facebook Pages is not reported as success.

## Production prerequisites found on 12 September 2026

Render has INSTAGRAM_REDIRECT_URI, but no INSTAGRAM_APP_ID or INSTAGRAM_APP_SECRET and no linked environment groups. Meta's Instagram sub-app is Zova-IG, ID 888302834029398 (not parent Meta app 1034305066042973).

Meta's Instagram Business login settings currently list only https://zova-tiktok-sandbox.onrender.com/oauth/instagram/callback. Add https://zova-social.com/oauth/instagram/callback without removing the sandbox entry, after action-time approval. Owner must enter/save the Instagram credentials in Render; do not paste secrets into chat, repository or recordings. Verify Render callback value matches exactly.

Meta also has old sandbox deauthorise/deletion URLs. These require a separate validated callback update before App Review. Do not point the deauthorise POST at the human-readable GET /data-deletion page. No endpoint update should falsely imply full deletion semantics.

Keep REQUIRE_SUBSCRIPTION=false. No schema/data migration, user deletion, OAuth unlinking, encryption-key rotation, social publication, paid-plan changes or App Review submission belongs to this release.

## Validation

12 September: 34 tests passed (existing regression tests plus both Instagram routes, cancellation, expiry, replay, cross-workspace ownership, missing-key handling, safe return destinations and connection-preservation tests). Desktop onboarding and Instagram preflight templates were inspected in a local read-only preview; spacing and explanation layout were corrected. This is not a live OAuth grant test. Git push is now available through the existing credential helper, although gh CLI is not signed in. Release is being prepared for deployment.

The previous Instagram-only App Review draft does not cover the Facebook-based Instagram scopes. The submission narratives, requested permissions and recording must be reconciled with the owner's two-method choice before App Review is submitted. Enabling a login route in code does not confer Meta approval for ordinary external users.

Tests run against new synthetic SQLite files in the OS temporary directory, never production. Live external grant/publishing tests still require configured credentials and user approval. A successful unit test is not proof that Meta has granted production permissions.

Rollback: revert the isolated release commit, retaining all existing environment secrets, persistent disk, PostgreSQL data and connection rows. Do not reset the dirty development worktree.
