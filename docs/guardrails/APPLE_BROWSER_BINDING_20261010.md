# Apple sign-in browser binding

Candidate only; full local/PostgreSQL validation pending. Production unchanged.

The previous callback required a valid unused state and matching identity-token
nonce, but did not bind that state to the browser that initiated sign-in. Tests
reproduced acceptance from another browser with no cookie, a different cookie or
a tampered cookie. This could establish an unintended account session.

Apple start now issues a ten-minute `__Host-zova_apple_state` cookie with Secure,
HttpOnly, SameSite=None, Path=/ and no Domain. The callback requires a matching
cookie before claiming state or contacting Apple. The host prefix prevents a
compliant browser accepting a subdomain-scoped replacement; SameSite=None supports
Apple's cross-site form POST without changing the normal session cookie. Existing
database state expiry and the atomic one-use claim remain authoritative. Successful
sign-in and MFA challenge responses clear the binding. Starting again replaces the
previous attempt; stale tabs receive a restart message. No schema change is needed.

Tests cover missing/mismatched/tampered binding, preserved existing account session,
no state consumption or provider exchange after rejection, successful original
browser retry, secure cookie attributes and deletion, replay, expired state,
superseded attempts and retained optional MFA. Provider identity responses are
mocked. Existing account and callback concurrency regressions now explicitly
supply the browser binding as part of their setup.

Sources: [OAuth security best practice, section 4.7.1](https://www.rfc-editor.org/rfc/rfc9700.html#section-4.7.1)
and [Apple form-post authorization flow](https://developer.apple.com/documentation/signinwithapple/configuring-your-webpage-for-sign-in-with-apple).

Limits: TestClient does not emulate browser cookie enforcement or cross-site
navigation. HTTPS desktop/mobile browser and live Apple validation remain required.
The cookie is always Secure; local testing needs HTTPS to complete this flow.
In-flight Apple attempts started before rollout will need to restart, but existing
Zova sessions, accounts and social connections remain intact. Apple service routing,
complete token-validation assurance and independent security review remain open.

Rollback: no data migration or credential rotation. Prefer a compatible forward
fix preserving browser binding. Do not restore acceptance of unbound callbacks;
temporarily disable new Apple sign-ins if browser validation fails, retaining
existing Zova sessions and password sign-in. No production change was made.
