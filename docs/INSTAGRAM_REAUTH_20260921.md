# Instagram remembered-login correction — 21 September 2026

The user reproduced the problem on Instagram's own “You previously connected Zova-IG” consent screen. PR #8's confirmation step protected Zova connection saving, but did not fix the provider's initial login. The old outbound URL passed force_authentication=1, which did not force credential entry at the current /oauth/authorize endpoint.

Meta's current Business Login documentation (updated March 13, 2026) documents force_reauth=true for requiring Instagram credentials even when a browser is signed in. enable_fb_login=false hides the Facebook login option on that direct login page. Source inspected directly in the browser: https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/business-login (Query string parameters).

## Fix and real-provider reproduction

Changed only the direct Instagram authorization parameters to force_reauth=true and enable_fb_login=false. State, scopes, redirect, token exchange, both login routes and explicit Zova account confirmation are unchanged. No schema/configuration/secrets changes.

In the same signed-in browser session, the unmodified production start showed the remembered @zova.social consent screen. Repeating the authorization URL with the documented parameters showed Instagram's username/email and password fields. No credentials were entered; Allow was not clicked; no grant, connection or post was created. This is real-provider login-entry evidence, not a completed login/publishing acceptance test.

After a person signs in again to an Instagram account previously authorised for Zova-IG, Meta can still truthfully mention the earlier authorisation. Zova-IG is the integration's app name and remains the same for all customers. This fix requires choosing/authenticating the Instagram identity before consent; it does not erase provider grant history or rename the app.

## Regression coverage

The outbound-route test requires force_reauth=true and rejects the obsolete parameter. New end-to-end synthetic cases sign up a second user in the same cookie jar for Instagram, TikTok and X; check empty social connections in onboarding/Account/Studio, reject old-user OAuth callbacks, require fresh state, cancel a returned prior identity and verify prior credentials remain unchanged. A switch-account test verifies single-use review disposal and fresh reauthentication on restart. Existing callback/brand/session/confirmation tests remain.

Exact test/CI/deployment results are recorded in the root handoff. Do not infer provider-controlled behavior from mocks. Rollback is a code-only revert of this parameter change; preserve databases, uploads, sessions and tokens. Reverting restores the remembered-session defect, so prefer forward correction.
