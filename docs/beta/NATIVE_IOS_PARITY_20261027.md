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

## Iteration evidence

- `c6a4a9d`: GitHub native run 40557597046 passed 30 unit tests, six simulator
  journeys and unsigned iPhone Release compilation. Application run 40557597122
  passed. Simulator evidence is synthetic and was inspected at iPhone 17 Pro size.
- The first native run exposed a typing/autosave problem: background saves disabled
  the composer, dismissed the keyboard and showed an outdated welcome heading.
  Background save now keeps editing enabled, cannot be cancelled mid-PATCH by a
  newer keystroke, and preserves the newest local text. Regression test added.
- Mobile-web captures from the isolated fixture at 402×874 showed that Studio
  should open blank, Instagram format belongs in the composer, Next Move evidence
  belongs within its recommendation block, and Schedule separates Calendar and
  Saved posts. Candidate `fc9eda7` aligns these screens and adds status filtering.
- Protected recovery can be compared with the server, saved as a separate draft,
  exported or explicitly discarded. Deliberate sign-out clears the user's local
  recovery across brands. Expired authentication instead locks the UI and retains
  the copy under that user's identifier until reauthentication.
- Media is file-backed and protected rather than buffering entire videos. HEIC/
  HEIF conversion, compatible Photos selection, camera-denial recovery, bounded
  preview decoding and background/tab-change playback pausing cover native media
  differences. Images remain limited to 15 MB and videos to 100 MB by the server.
- Native-cookie regression checks confirm that profile, voice and draft edits
  are the same data read by the web client. Native snapshot confirmation rejects
  unreviewed changes and calls a synthetic provider once for duplicate requests.
- Additional UI checks cover strategy persistence, caption editing through final
  review/cancellation, and fresh TikTok privacy/commercial consent. Final results
  must be recorded after the latest candidate completes; earlier passing checks
  must not be used to certify later changes.

## Delivery boundaries

Draft PR35 targets the existing iOS beta branch, keeping the native replacement
reviewable separately from the earlier beta work. The shared backend must receive
the compatible presentation endpoints before the signed native app is distributed.
No database migration, new permission, payment enforcement or provider credential
change is needed. The Codemagic workflow retains the existing app/signing identity
and build counter, pins the native branch, and leaves automatic external submission
and App Store submission off.

Physical acceptance remains required for upgrading build 11 without losing access,
each provider's sign-in/cancel/return, a real photo/video and camera permission,
background/reopen, slow/offline recovery and device keyboard/accessibility. No real
post should be sent without a separate, exact-content approval. Apple processing
and external TestFlight eligibility must be verified rather than inferred from an
upload. All broader commercial findings and unavailable historical media remain
in the existing register.

- `fc9eda7`: application CI40560087940 passed. Native CI40560087886 passed
  32 unit and seven of eight UI tests; publication review was not reachable
  after caption editing. The candidate now ends caption focus explicitly,
  reserves keyboard space for the caption, and avoids autosave scrolling while
  editing. Preview/compare/add-platform and sent-attachment removal were checked
  against the web controls and restored. Undo now skips an unchanged snapshot.
  These changes require fresh simulator and Release checks.

- Further security review isolated fresh sign-in from a prior user's in-memory
  product cookie, invalidates earlier responses, and resets brand/tab/consent
  presentation on sign-out. Regression checks cover the account boundary.
- Picker/camera copies now live only in Zova's protected temporary directory and
  are cleared after use, sign-out and restart without deleting source files.
  Follow-up chat turns retain the attachment on the post without repeating it
  in each new message, matching the web composer. Added regression evidence.
- Production read-only preflight at 18:54 UTC: Stripe test mode, subscription
  enforcement false, live checkout false. Publications: seven published, one
  pending, one unknown, one cancelled; schedules: one cancelled, no active
  deliveries. Unknown/pending records are retained, never automatically resent.
  A fresh managed Render database export was requested at 18:50 UTC; completion
  still needs verification. No backend deployment has occurred.
