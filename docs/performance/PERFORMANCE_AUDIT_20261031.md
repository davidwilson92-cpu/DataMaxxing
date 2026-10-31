# Zova performance audit

## Candidate and measurement scope

31 October 2026. Base a52fab1. The implementation is isolated on
codex/performance-20261031. This report will be completed with the final measured
comparison and exact-candidate validation results before handover.

The web product uses FastAPI, SQLAlchemy, Jinja and browser JavaScript. The iPhone
product uses SwiftUI and the same guarded APIs. Production keeps Render, existing
authentication, explicit publishing approval and disabled customer charging.

Public production probes measure network response and asset headers. The private
workload uses disposable accounts, 1,000 drafts, 100 series occurrences and four
controlled social providers against the real production application routes.
Provider latency is fixed at 100 ms, SQL round-trip overhead at 2 ms, creative AI at
300 ms and optional topic research at 1 second. These inputs allow attribution of
application overhead. They do not measure live social-provider or model latency.

The isolated browser uses a 390 × 844 viewport, 70 ms network latency, 4 Mbit/s
download and fourfold CPU slowdown. Public static compression is normalised on both
revisions because the production Cloudflare edge already compresses these assets.
The index experiment uses 50,000 rows per table and current query plans/statistics.

## Review boundaries

Short-lived social observations are keyed by owner, brand, current connection,
permission/token fingerprint and local publication activity. Every response checks
current ownership and grant state. Explicit refresh bypasses cached observations,
including when the existing iPhone build omits the new refresh flag. Cached data
keeps its original observation time. Unknown metrics remain unknown.

Optional research is stored once per owner and brand. A conditional lease prevents
duplicate workers. Expired leases recover, retries back off, and three failed attempts
stop until a later eligible request. Strategy changes, withdrawn AI consent and
account deletion invalidate old work. The research is part of its originating
recommendation allowance, with actual provider usage still recorded. No publication
or scheduling operation uses these jobs or the read cache.

Private thumbnails check ownership and brand on every request, validate the current
stored source, decode one image at a time and retain only a bounded in-memory
preview. Original media remains the editing and publishing source. Private pages,
API responses and media continue to use no-store.

## Release prerequisites

Run the mandatory SQLite and PostgreSQL application workflows and native simulator
tests plus iPhone Release compilation on the exact candidate. Preserve the complete
79-entry known-gap register. The final report will record results and any remaining
limitations rather than infer production readiness from synthetic timing alone.

For an existing database, first use the established offline schema preparation
with ZOVA_SCHEMA_MODE=initialize to add zova_discovery_jobs. Then run
scripts/prepare_performance_indexes.py with the migration identity. It creates only
the two reviewed indexes, using concurrent creation on PostgreSQL, and verifies
their definitions and valid/ready state. Runtime verification mode never repairs
a missing table. Take the normal backup and review the deployment plan first.

Deploy compatible backend endpoints before distributing an iPhone binary using
thumbnails. Existing iPhone clients retain the original download route and fresh
Performance refresh behaviour. Rolling back application code can leave the additive
table/indexes in place. Pending research resumes when a compatible worker returns.

No hosting migration, resource upgrade or live customer charge is part of this work.
