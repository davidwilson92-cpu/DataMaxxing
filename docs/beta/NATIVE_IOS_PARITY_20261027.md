# Native iOS replacement — work in progress

Owner requests a native interface preserving the advanced beta, mobile-web design,
all functionality and existing security. This is an implementation and parity
record, not a release certificate. Existing TestFlight remains available.

## Architecture

SwiftUI screens replace embedded product HTML. Authentication remains Apple's
system authentication session with S256, exact callback/state checks, rotating
first-party credentials in Keychain and server revocation. The existing native
ticket exchange supplies an in-memory, device-bound application session to
URLSession. It is not persisted to disk, exposed to JavaScript or sent off origin.
JSON/form endpoints retain their existing ownership, workspace, rate, AI consent,
revision and publication-approval controls. No second publishing engine.
System browser authentication for social providers and legal external links is
intentional; it does not make the product screens web views.

## Required parity inventory (not yet accepted)

- Entry: branded launch, reduced motion, sign in/up/recovery/Apple login/MFA where
  configured, cancellation, auth expiry/revocation, protected app switcher.
- Studio: empty state and first-use skip/Guide, aligned header, brand switch,
  chat history/search/rename/delete, autosave/reopen/concurrency, sent messages,
  image/video/file/camera attachment, previews/removal/export, source link,
  platform selection, Instagram post/story/music, X threads, caption editing,
  conversational generate/rewrite/add-platform/insights, undo and copy.
- Next Move: strategy/voice/performance-backed suggestions, source evidence,
  one-card design, infinite batches/history/refinement, draft handoff, two-box
  strategy proposal/save/edit, stale/revision/permission/error recovery.
- Publication: destination selection, immutable final review, media/caption
  preview, TikTok privacy/interactions/commercial/AI disclosures and fresh
  consent, music agreements, publish/schedule confirmation, timezone, partial
  outcomes, uncertain-outcome protection, status polling and platform links.
- Schedule: searchable/filterable list and visual calendar, media thumbnails,
  rename/open/delete, reschedule/cancel/edit with version guards, recurring
  fresh/repeat series, preview/create/pause/resume/cancel, occurrence editing,
  repeat review/confirmation, results and refresh.
- Performance: 7/30-day selection, missing-versus-zero metrics, provider errors,
  platform results, recent posts/links, recommendations and question answering.
- Account: dark expandable rows, profile, voice/preferences/examples/learning,
  social connections and both Instagram routes, unlink, brands, AI permission,
  password/security/privacy, verification, account deletion, help and support.
- Security: no token/secret logs or disk HTTP cache, no cross-origin credential
  redirects, signed media owner checks, preserved backend guards, safe external
  URLs, no customer billing, no auto-publish/retry of ambiguous sends.

## Acceptance required

Each inventory group needs native implementation, positive/negative automated
checks, simulator screenshots compared to mobile web, and physical-device checks
where provider/keyboard/media behaviour cannot be established on this Windows
host. Existing application/PostgreSQL suites remain mandatory for backend changes.
Synthetic provider/AI fixtures are not evidence of real provider success.
No new build is released as native parity until remaining gaps are recorded and
resolved. All historical commercial findings remain in the existing register.
