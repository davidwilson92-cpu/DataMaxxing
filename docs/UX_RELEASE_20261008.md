# Focused UX release — 8 October 2026

Publication is authorised. Prepared on a separate release worktree from live main `38f1c265`; the broader local candidate is preserved separately. This manifest supersedes broader candidate scope for this release.

## Included

- Studio restored/explicit platform selection, editing scope, conditional Instagram/X formats, stale-response and retry/save protection, brand-preserving navigation, concise labels and keyboard semantics.
- Editable/searchable draft titles with ownership and revision checks; compact scoped Your week summary, pending-results filter and weekly schedule windows.
- Goal-first strategy proposal and state-specific guidance; bounded brand-scoped Performance evidence with 24-hour freshness, truthful 7/30-day metrics and manual review actions.
- Consistent Performance navigation, mobile/signup proportions, optional country, clear free beta/no card offer and secondary future pricing.
- Schedule claim matches the scanned due time/update timestamp so accepted reschedules and cancellations win before publishing.
- Title and Performance snapshot export/erasure; derived media observation erasure; authenticated schema readiness and synthetic restore comparisons.

## Excluded and preserved locally

September password-hash upgrades, MFA, Apple/login changes, durable recovery email, upload/storage changes, newsletter integration, monitoring/cost expansion and broader worker recovery changes. No activation of charges, subscription enforcement, marketing, provider grants or new publishing automation. Existing publishing approvals and both Instagram routes stay intact. No real social post is part of release verification.

## Data compatibility and rollback

Additive `nova_drafts.title VARCHAR(120) NOT NULL DEFAULT ''` and `zova_performance_snapshots` table. Existing rows/content are not rewritten. Migration is idempotent. Performance snapshots contain bounded recent post excerpts and metrics; included in assisted export and erasure.

Unlike the broader candidate, this release does not change password formats or introduce MFA. If rollback is required, redeploy `38f1c265` code while retaining the database, uploads, encryption keys, sessions and provider ledgers. Do not restore an old database or remove additive schema. Stop and review any unknown publication outcome; never resend as part of rollback. Reapply the isolated schedule race fix in a forward correction as soon as possible if rolling back the whole release.

## Validation and release gates

35 focused Python tests and three Node harnesses passed on the isolated release. Remote full SQLite/PostgreSQL tests, dependency audit, PostgreSQL dump/restore, Docker build/smoke and final live checks must pass before declaring deployment complete. Provider delivery and real-customer outcomes remain unverified by synthetic checks. Evidence and exact deployment revision are appended after release.
