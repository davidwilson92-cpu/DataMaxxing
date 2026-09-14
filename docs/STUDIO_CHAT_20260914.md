# Studio chat correction — 14 September 2026

## Design brief
Replace the split Studio with one calm, centred conversation. Remove the working canvas, permanent context panels and mobile mode switching. Keep Zova's purple mark, typography and restrained accents. The message and reply should dominate; reveal secondary tools when requested. Keep every existing capability reachable, saved work compatible and publishing explicitly reviewed.

## Implemented
- One chat column and a bottom, growing message box. Two optional starter prompts fill the composer.
- Draft text appears as a readable reply. Edit and copy are adjacent; comparison, preview, undo and scheduling are under More.
- A navigation drawer retains Drafts, Analytics, Voice, Socials, Account, Help and Security. Post settings hold platform selection, source, X format and account readiness.
- Native dialogs provide Escape dismissal and focus restoration. Draft editing and final reviews receive keyboard focus. Mobile Enter inserts a line; desktop Enter sends (Shift+Enter inserts a line).
- Scroll respects reading earlier messages; Latest reply returns to the bottom. Upload progress/errors and save recovery remain visible beside the composer.
- Existing workspace persistence and immutable review use the same server APIs. No database, authentication, provider or subscription changes.

## Evidence
Local synthetic SQLite suite: 76 passed. Four Studio JavaScript files pass node syntax checks. Browser checks at desktop and 390 x 844: no horizontal overflow, full viewport workspace, Zova logo visible, settings focus returns after Escape, mobile multiline input, navigation exposes all areas. Edited draft text and conversation survive reload. Failed mocked generation retains input; retry-save succeeds. Mocked X review displays exact account and edited text; explicit confirmation reports Published and leaves Instagram unsubmitted. No real provider was contacted.

## Release and limits
GitHub CI adds PostgreSQL 18 tests, synthetic backup/restore, dependency checks and Docker smoke validation before merge. Record final CI/deploy status in the workspace handoff. This improves presentation; it does not establish an industry-leading score or expand media inspection/provider capabilities. Device emulation is not physical iOS/Android testing. Production provider publishing is intentionally untested.

## Rollback
Revert this presentation commit through a reviewed PR and redeploy the previously verified main revision f2389c34f28d4c0711b09e2efa30c3c07e9891c7 if necessary. No schema migration or data restoration is required. Preserve current database, upload disk, encryption key and session secret.
