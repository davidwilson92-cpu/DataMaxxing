# Security update deployed — 26 October 2026

Owner explicitly requested publication after the engineering review. Render
deployment `dep-dbfieva9lscs73a97u80` successfully deployed runtime
`a9fe5a7a4724231b3491517abed35224f3f8d011`. Started 10:12:13 UTC, duration
52.5 seconds; Render reported Live and the service responded normally.

## Before deployment

- Exact application PR CI 40301485867, duplicate push CI 40301479522 and native
  CI 40301485777 all passed. SQLite 707 passed/2 skipped; PostgreSQL 708 passed/1
  skipped. Application/client/browser, synthetic recovery, image audit/smoke,
  constrained password work and iPhone simulator/release compilation passed.
- Exact beta release scope validated locally. Documentation-only commits after
  a9fe5a7 were not substituted for the validated deployed runtime.
- Fresh managed database export completed in Render, listed as 26 October
  10:06 UTC. The job had initially shown 10:02 while processing. Backup remains
  in Render; no restore or backup download was performed.
- 29 media records: zero local-public-URL origin mismatches; four previously
  documented missing legacy files remain missing. No files or records removed.
- No queued/publishing publication or scheduled job due within 15 minutes.
  The recent pending TikTok item is already delivered to its inbox and awaits
  TikTok completion. The old Instagram unknown outcome dates from 22 September;
  it remains protected against automatic resend. Neither item was changed.

## Live acceptance

- 18 public/protected-route, asset and anonymous-upload checks passed; receipt:
  `evidence/20261026/live-security-smoke.json`. Public pages and new Studio JS
  return 200; six protected pages redirect signed-out browsers to login;
  anonymous POST /api/media returns 401. Health returns 200.
- A read-only check inside the deployed service fetched an existing registered
  asset via the public production origin. Unsigned/tampered/expired requests
  return 404; valid signed request returns 200/no-store and identical bytes.
  No signed URL, file contents, password, token or customer data was exported
  into this evidence. Runtime environment confirms exact a9fe5a7 commit.
- Existing Zova Recovery Check browser session survived deployment. Account,
  Studio, Schedule (fully loaded October calendar) and Performance loaded.
- Runtime flags remain STRIPE_MODE=test, STRIPE_LIVE_CHECKOUT_ENABLED=false,
  REQUIRE_SUBSCRIPTION=false, PLAN_LIMITS_ENABLED=false.
- No social post, new payment, account deletion or new TestFlight upload was
  performed. Shared web/backend changes apply to the existing iPhone app;
  TestFlight remains last known 0.1.0 (11).

Screenshots: `render-pre-release-backup.png`, `render-security-release-live.png`
and `live-media-protection.png` under `evidence/20261026/`.

## Retained constraints

This publishes the bounded security fixes, not commercial certification. Keep
the 79-item register, prior QA findings and review's privacy/retention,
operational-recovery and independent-assurance requirements. Four old missing
media files and historical ambiguous publication remain unresolved.

Rollback must retain scrypt-v2 verification once any new/upgraded password hash
is stored. Do not use Render's old-image rollback to d090e6e or earlier without
a compatible verifier; prefer a tested forward correction. Do not restore an
old database over newer user data. Render remains the host; no AWS migration,
paid monitor, subscription enforcement or live customer charges enabled.
