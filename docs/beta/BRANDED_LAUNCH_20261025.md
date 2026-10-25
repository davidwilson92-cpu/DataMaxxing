# Branded iPhone launch — 25 October 2026

## Scope and release status

Owner requested a logo/strapline loading screen, followed by the Z magnifying
out of the screen as the app loads. Implemented in the native iPhone shell.
Uses the established Zova mark and existing strapline, “Your AI social manager.”
The near-black background has a restrained purple glow. The system's static
launch background now matches, avoiding the previous white opening flash.

Runtime candidate: `f9626885f72a44e336c61d6a40ae4e62cb3a4836`.
Not deployed or uploaded to TestFlight. Live remains d3bc09d; TestFlight remains
0.1.0 (11). This change requires a replacement iPhone build when publication is
requested. The prior compact connections candidate is also included but not live.

## Behaviour and review

- Startup/session work runs immediately behind the cover. On a fast launch the
  mark appears for 300 ms, followed by a 620 ms zoom/fade reveal.
- The cover waits for signed-out welcome, authenticated Studio readiness, or a
  first-page failure. Failure UI is revealed rather than masked.
- At three seconds a short loading message appears. At eight seconds the cover
  fades away even if readiness never arrives, exposing the existing loading or
  recovery interface. This does not cancel or retry authentication requests.
- Reduce Motion uses a short fade and no zoom, including the initial appearance.
- Underlying controls are unavailable to touch and VoiceOver during the cover.
- Existing background privacy protection remains above the launch cover. Normal
  foreground returns and tab changes do not replay the sequence.
- Studio, Schedule and Performance keep their light backgrounds after revealing;
  Account and welcome keep their dark backgrounds. No shared web styling changed.
- No new dependencies, permissions, tracking, API calls, assets or credentials.
  The test host is excluded from release builds.

## Validation

Final exact candidate validation passed:

- Native run **40212709229**: 20 unit/WebKit tests, four iPhone UI tests, and
  release compilation. Readiness/reveal, reduced-motion completion, slow fallback
  and background/foreground without replay passed.
- Application push/PR runs **40212709293 / 40212712444**: 678 SQLite / 679
  PostgreSQL tests; 2 / 1 platform-specific skips; client/browser regressions,
  synthetic PostgreSQL restore, hosting-image smoke/audit and exact-scope gate.
- Portrait and landscape renders inspected from the final native run:
  evidence/20261025/branded-launch-portrait.png and branded-launch-landscape.png.
  Centred brand, readable strapline, unclipped layout in both orientations.

XCTest's application screenshot cropped the landscape frame incorrectly; the
check now captures XCUIScreen.main instead. The full-screen evidence confirms
this was a capture issue. The test host stays excluded from release builds.

An initial simulator compile caught a read-only accessibility environment property
in the test host; fixed with an injected motion preference. Production still reads
the device's actual Reduce Motion preference. No failed candidate was released.

A second check inspected destination existence too early: XCTest can report the
underlying text while the cover is still visible. The test now waits for an
explicit completion marker that is inserted only after cover removal. The initial
recording confirmed those assertions ran before the transition finished.

Physical-device timing/feel remains a TestFlight acceptance check after publication.
All 79 broader commercial findings remain recorded; no commercial certification.
Render, disabled customer charges and inactive paid monitoring remain unchanged.
