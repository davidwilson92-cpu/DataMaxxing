# Zova Social iPhone beta — 19 October 2026

## Release identity and boundaries

Isolated branch `codex/ios-beta-20261019`, based on reviewed Studio/TikTok runtime `1bd3b9486ea79c82413978c07e7d82a4c26ef52c` and handoff `0639b87`. Selectively reused disabled PKCE/session foundations from PR28; did not adopt the broad service/account/RLS/queue migration. The bounded backend is deployed for internal iPhone beta; final deployment receipt is recorded below.

Apple team `7B4W8RN6GX`; newly registered bundle `com.zovasocial.app`; new App Store Connect app **Zova Social**, ID **6824416979**. Existing **Zova Market**, ID6820674737 / `com.zovasocial.ios`, is a different installed beta and must not be overwritten. Owner approved the Associated Domains capability and app-specific signing profile. New profile **Zova Social TestFlight**, Apple ID4UF5DP7795, uses the existing distribution certificate; imported to existing Codemagic as `zova-social-testflight`. Existing Apple integration `zova-testflight` and certificate `zova-market-distribution` are reused without exporting private keys. No new API key, paid subscription or public App Store release.

Codemagic app6ad5cbbeadaac76a4f1f8525 imports the public DataMaxxing repository without extending its GitHub integration permissions. Workflow is manual, restricted to the isolated branch, with internal-TestFlight-only export and public App Store submission disabled. Free account had28/500 macOS minutes used when checked.

## Implementation / evidence matrix

| Area | Implementation | Validation and limits |
|---|---|---|
| Studio, drafts, Next Move, analytics, account | First-party web screens retained inside a SwiftUI iPhone host; no separate publishing implementation | Existing application suite, ownership and immutable review tests retained. Signed-device inspection still required. |
| Navigation and branding | Purple Z identity, native dark bottom navigation, retained tab views, keyboard hides bottom bar, duplicate web navigation removed | Welcome-screen simulator UI test passed on e9a2043. Studio handset layout and VoiceOver require device evidence. |
| Sign-in | System authentication browser, S256 PKCE, exact HTTPS callback, explicit signed-in account confirmation, one-use code, Keychain tokens | Backend code replay, cookie binding, ownership and revocation tests. Standard PKCE vector and callback checks pass on simulator. |
| Shared browser authority | One-use60s handoff; revocable iOS cookie bound to native device session; exact destination and workspace allowlists | Synthetic expiry, concurrent ticket consumption, purpose separation and other-user boundaries tested. Native tokens never enter JavaScript or WebKit requests. |
| Social connection | System Safari sheet with explicit Zova account handoff; returns refresh connection presentation without discarding Studio input | Provider permissions and publishing mode remain those of the server. Actual iPhone OAuth returns still require a device check. No new social grants or real posts in this task. |
| Media and exports | WebKit user-selected file/photo/video input, native camera permission descriptions, protected temporary exports and share sheet | Real-device photo picker, camera, large videos and export sheet remain unverified until installation. No silent photo-library scan. |
| Security | Refresh rotation/replay revocation, password-version binding, secure Keychain access, no API redirects, HTTPS host allowlist, app-switcher privacy cover, redacted logs, late-response epoch guards | Native session regression tests added. Simulator secure-storage and unsigned release compilation passed on e9a2043; later tests must pass before release. |
| Privacy and account lifecycle | Privacy manifest, clear OpenAI selected-media disclosure, in-app full-account deletion request and persistent receipt; verified assisted erasure updates the same receipt and removes native credentials |44 targeted synthetic tests pass locally. Deletion is explicitly pending until operator processing; no claim of instant erasure. Operator turnaround and remote-storage retention remain wider beta gaps. |
| Purchases | Native beta blocks billing paths and hides web purchase links; no StoreKit products, customer charges or subscription enforcement enabled | Synthetic native403/web billing continuity tests. A commercial iOS monetisation decision remains separate. |
| Offline / recovery | Preserve live tab input; safe GET recovery to saved work, never replay a failed publishing POST | No promise of offline editing/sync, background publishing on the handset, push notifications or native-only feature parity. Server scheduler remains authoritative. |

## Reviews by discipline

- Backend: additive tables and routes; browser authentication and provider engines retained. Verify exact candidate against PostgreSQL and restore/container checks before deploying. No destructive migration.
- Frontend and iOS: preserve the Studio interaction rather than introduce a second editor. Loading/error overlays now observe each retained page; failure recovery cannot repeat publication. Minimum iOS18.0. Native WKWebView embeds the existing interactive product; this is not a claim of fully native screen rendering.
- Security: separate bearer authority from browser cookies; no persistent signing secrets in Git or application assets. Revoking a device invalidates its web and OAuth handoff cookies. A network-failed logout cannot promise remote revocation; sessions expire and password revocation remains available.
- Privacy: deletion initiation now happens in-app with an honest receipt. Manual processing remains an operational obligation, not an automatically resolved commercial-readiness finding.
- Design: recognisable purple/dark Zova identity and shared Studio. Simulator welcome evidence is insufficient to award an8/10 score to real-device Studio accessibility, keyboard/media behaviour or provider callbacks.

## Validation ledger

- ca8e676: local full application suite466 passed /1 skipped; hosted application validation39215920440 passed. Initial iOS run found unsigned-simulator Keychain failure; did not waive it.
- e9a2043: hosted application validation39217758410 passed; hosted iOS39217758342 passed simulator tests and iPhone release compilation after enabling local simulator signing. No distribution credential used in this validation job.
- f44dd72: hosted application validation39219002007 passed; native run39219001843 passed. Includes additional native concurrency/late-response checks and screenshot export. Later final-source checks also passed, as recorded below.
- Later deployment, signed archive, TestFlight processing, invitation and physical-device checks must be recorded below with actual results. None is implied by source or simulator success.

## Rollback and retained blockers

Disable `ZOVA_MOBILE_ENABLED` to stop new native authority and invalidate native-bound browser sessions, preserving ordinary browser login and social connections. Keep `ZOVA_IOS_REDIRECT_URI` exact and `ZOVA_IOS_APP_ID=7B4W8RN6GX.com.zovasocial.app`. Retain additive tables on rollback; do not drop user data. Roll back the web runtime to the previously verified production commit if needed, without reversing independent user content writes or provider grants. Expire the new TestFlight build in Apple if an unsafe client is found; do not expire the unrelated Zova Market beta.

All79 wider beta findings remain in `docs/beta/deferred-register.json`. This work is a limited iPhone beta, not commercial certification. Do not change TikTok production posting mode or scopes solely because the owner approved submission of a public-access audit; verify the provider approval and live grants separately. No real post, public App Store submission or charge is authorised as a validation shortcut.

## Final implementation and release evidence

- Native build **0.1.0 (4)**, source16fbb9a8e168d774a130f5cecfcc266928960141, Apple UUIDe5b9c889-61cb-463a-b0b0-fb3cdfe744ef, uploaded09:40 BST; Apple reports **Testing** after manual assignment to Zova Social Internal Beta. Group has1 tester/1 build; David Wilson invited10:08 BST. Invitation delivery/installation has not yet been confirmed by the owner. iOS18 or newer, iPhone only.
- Final Codemagic build6ad5d6977550aed810900ec8 uploaded successfully as independently confirmed by Apple's processed build. Its Publishing UI remained running after Apple processing; do not duplicate the upload. Earlier build3 is Ready to Test but intentionally not assigned.
- Backend f47e1be540f167f6bf6594318dde56f3a107d822 has an unchanged native tree and final dynamically loaded Account social refresh. It replaces only the owned workspace's social section, preserving unsaved profile edits; Studio input is retained. Three Node regressions cover refresh success/failure and irrelevant tabs.
- Cancel sign-in now returns exact state-bound access_denied without issuing credentials. Native callbacks reject incorrect host/path/state. Signup and Apple sign-in resume only a valid pending grant; Apple state includes the protected grant reference before hashing. Ordinary web Studio is not intercepted by abandoned native login cookies. Full mocked Apple-to-native exchange/handoff path tested; real iPhone provider return remains pending.
- Expired native grants/sessions are pruned during rate-limited setup; user drafts/media remain untouched. Removed two unreferenced legacy output artifacts. This is scoped hygiene, not a full legacy rewrite.
- Initial signed IPA was rejected for accidental iPad target family. Fixed target-level iPhone family and added actual archive metadata validation plus5 regression tests. No Apple requirement was waived.
- Final hosted runs: application39225907537 and39225914327, native39225914321, all success. **476 passed/1 skipped** per SQLite/PostgreSQL; synthetic dump/restore, container build/smoke, pip-audit with no known vulnerabilities, beta scope guards. **11 native unit tests,1 welcome UI test**, release compilation and simulator screenshot export. Frontend native refresh3 tests passed.
- Live native config is enabled, exact callback https://zova-social.com/mobile/callback; review_required true, native_billing false. Public AASA and Apple association CDN both return the exact app ID7B4W8RN6GX.com.zovasocial.app. Unauthenticated native profile returns401. Existing signup/login and Studio assets return200; DENY/nosniff headers present.
- Signed-in production Account inspection retained Facebook Zova Social, TikTok David Wilson, X DataMaxxingUK. Instagram was not connected in this inspected account. No account reconnection or real publication was performed.
- Production database:3-day PITR verified, logical export created19 October09:03 BST completed inside Render. Not downloaded. CI synthetic restore passed; no production restore drill claimed.
- Specific-commit deployment disables Auto-Deploy; keep it off until reviewed main includes this release. Latest backend f47e1be deployment dep-dbats96q1p3s73d3c2ig reports Deploy succeeded | Live,46.9s. Final independent public preflight passed all9 endpoints and exact served ios-shell.js matches the tested source; evidence social-proof/ios-live-preflight-final.json. Previous live16fbb9a / dep-dbatd5ks728c739k4hc0. Pre-iOS rollback cc093687bc92f5600283918d330ef70691e4216e / dep-db91bkvavr4c739qd50g.

## Required first-device acceptance

Install the invitation's Zova Social0.1.0(4), sign in normally, confirm correct account/workspace and saved drafts, attach a disposable photo/video, draft/edit/reload without publication, inspect keyboard and tab layout, cancel and return from a social connection without changing grants, check export and VoiceOver. Real publishing requires separate exact-content authorisation. These checks are pending, so no unsupported8/10 or commercial-ready score is awarded. External TestFlight review/public availability are not configured by this internal release.

Rollback clarification: mobile flag-off invalidates native authority **while disabled**. Explicitly revoke affected sessions or increment the relevant authentication version before re-enabling if permanent revocation is needed. Preserve additive tables and all content; never restore over newer writes or replay unknown publications. Expire only this app's unsafe build if needed. Known79 gaps remain authoritative.
