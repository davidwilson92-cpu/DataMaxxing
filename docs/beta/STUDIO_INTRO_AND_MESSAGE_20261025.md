# Landing message and first-time Studio introduction — 25 October 2026

Candidate: `9f912b825327e3f967e9b79d41f7e513ffb644d6`.
Not published. Live remains d3bc09d; TestFlight remains 0.1.0 (11).

## Selected message

**Because content is the fun part.**

Turn your ideas into captions and a content plan with Zova, your AI social media manager.

Landing and sign-in use the selected headline and description. Native welcome
uses the same message; launch/VoiceOver use its short headline. The landing title
and shared footer carry the headline. The landing's old vague closing statement
is replaced by “Make your next post.” Mobile headline sizing fits the new copy;
the existing light closing button now has readable dark text.

## Introduction

Three speech-style purple/white callouts point at the actual Studio controls:

1. **Start with an idea:** type a brief; use + for photos or video.
2. **Choose your socials:** select platforms, edit the caption, publish or schedule.
3. **Need an idea?:** Next move and Your strategy.

Skip intro is always available, as is Escape. Back/Next navigation shows progress;
the final action is “Let’s create”. Nothing is generated, saved as a draft or
published by the tour. Finishing/Skipping does not summon the mobile keyboard.
It uses native HTML dialog focus containment, labelled content, a live step
description, touch-sized controls and no motion dependency.

The saved account flag is atomically claimed before the automatic tour starts.
Only one competing tab/device can claim it. Skip, completion, reload, login and
workspace changes cannot replay it automatically. An existing account migrates as
already introduced, preserving the owner's returning blank-Studio experience.
New ORM-created password/Apple/Facebook accounts start eligible. Raw legacy
account inserts default to already introduced. Guide allows explicit replay.

Deep links to drafts, Strategy or recurring work are not interrupted. The tour
also yields if the user already interacted, focused a field, or opened a dialog.
A failed intro request never prevents Studio use. There is no local tracking,
AI request, new cookie, permission or customer charge.

## Guide

`/guide` reuses the existing Help content and a compact three-step guide, with
expandable topics and “Show me around Studio”. `/help` remains a compatible alias.
Studio's footer, workspace navigation and Account link to Guide, so iPhone users
also have access after skipping. No parallel help content is maintained.

## Migration and release

One additive user preference, `studio_intro_pending BOOLEAN NOT NULL DEFAULT
FALSE`, preserves all existing user data. The ORM explicitly defaults new users
to true. The migration is idempotent and exercised against old rows and new ones.
The claim endpoint requires the current session, ignores supplied user identifiers,
and retains the existing origin/workspace request checks. The flag is not tied to
optional product metrics.

Schema initialization mode applies the migration during deployment. Verification
mode requires offline schema preparation first. Rollback leaves this additive
column in place. No production migration was run during development.

The shared Studio tour and Guide ship with the web update; updated native welcome
and launch copy need the replacement iPhone build already required by the launch
animation candidate. Preserve Render, disabled charges and inactive monitoring.
All 79 broader commercial findings remain tracked, with no commercial certification.

## Evidence and validation

- Local backend: 30 passed, 1 PostgreSQL-specific skip across intro, onboarding,
  compatibility and account suites. New cases cover competing claims, account
  isolation, authentication/origin checks, public Guide and additive migration.
- Browser: first visit, Skip, reload, another device, Guide replay, completion,
  Escape, no text changes/keyboard focus, and 320/390/844/1440 layouts passed.
  Tab/Shift+Tab wrap within the callout. A delayed-response check verifies that
  typing is retained and automatic introduction yields to interaction.
- Existing native-shell/connection client checks: nine passed.
- Synthetic captures: `evidence/20261025/studio-intro-first.png`, responsive
  `studio-intro-*.png`, `landing-content-fun-mobile.png`, `guide-mobile.png`.
  Reviewed in development; no customer data or real provider requests.
- Full CI initially exposed the new anonymous test sharing an already exhausted
  request bucket with earlier cases. The test now uses its own client identity;
  no production security limit was relaxed.
- Final exact-candidate PR application CI **40222009264 passed**: 682 SQLite /
  683 PostgreSQL tests (2 / 1 platform-specific skips), all client/browser
  regressions including the keyboard loop, synthetic database restore, hosting
  image smoke/audit and the pinned beta gate. Native CI **40221189980**
  passed 20 unit/WebKit tests, four UI tests and release compilation on 7ef083b.
  Native source/project/signing files are byte-identical in final 9f912b8; the only
  subsequent runtime edit is the shared web keyboard loop, covered by the browser
  regression. Native launch and welcome renders were inspected and saved as
  `landing-message-native-launch.png` / `landing-message-native-welcome.png`.
  Physical iPhone tour acceptance remains a post-publication device check.
