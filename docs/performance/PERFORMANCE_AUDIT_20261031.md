# Zova performance audit

## Outcome and release state

The implementation is prepared in the isolated performance branch and PR 37. It substantially reduces repeated provider work, draft and series queries, optional research waits and image-preview bandwidth. Production rollout and an updated iPhone binary remain separate release steps. Render remains the host and customer charging remains disabled.

The primary controlled comparison reduced the saved-post endpoint from 513 ms to 58 ms, the recurring-series endpoint from 525 ms to 48 ms, and repeated Performance reads from 3,165 ms to 118 ms. First uncached Performance reads took 331 ms. Fresh Next Move batches took 527 ms versus 1,532 ms with identical simulated creative-model latency.

Cold password sign-in and caption generation showed little change. Browser cold-start and Schedule timings remain around their previous range. This work supports faster ordinary reads and progressive expensive work, with further device and production measurements needed before making an app-wide instantaneous-response claim.

## Measurement scope

- Base source a52fab1. The JSON evidence records source revisions and a content digest of the actual measured web/native runtime, including candidate changes made before the final commit.
- Real production public HTTP probes on 31 October measured approximately 191 ms for health and login responses and 191–192 ms for public CSS/JavaScript. These are five-request completion times from the operator's machine. Production already uses Cloudflare gzip. Its current public static responses had no explicit Cache-Control and reported DYNAMIC.
- The private workload runs the production FastAPI/Uvicorn application and dependencies with a disposable SQLite database. It contains 1,000 drafts, 10 recurring series with 100 occurrences, four connected-provider fixtures and a 3.05 MB image. No real credentials, social publications or paid AI requests are used.
- Controlled inputs are 2 ms per SQL round trip, 100 ms per provider read, 300 ms per creative-model operation and 1 second for optional research. Ten samples are recorded per endpoint. The p95 column uses the nearest-rank sample, which is the maximum with ten samples and is unsuitable as a production SLA.
- Browser journeys use real rendered pages in isolated Edge, a 390 × 844 viewport, 70 ms latency, 4 Mbit/s download and fourfold CPU slowdown. Public static gzip is normalised on both revisions to reflect the live edge. Each full browser journey is one run, with three repeated Studio navigations. Its timings include browser automation overhead.
- Database plan experiments contain 50,000 rows in each of the three measured tables, 50 owners and four brand partitions per owner. One hundred samples and refreshed query statistics are used. PostgreSQL functional checks run against a real isolated PostgreSQL 18 service. The workflow also runs the same index experiment in a separate synthetic PostgreSQL database.
- Absolute production-authenticated, real-provider, real-model and physical-iPhone latency distributions remain unmeasured. Synthetic provider delays establish the effect of application sequencing and duplicate work.

## Ten prioritised bottlenecks

Impact reflects the affected journey and frequency. Effort is relative to this application.

| Priority | Root cause and baseline evidence | Change and expected impact | Effort |
|---|---|---|---|
| 1 | Performance collected per-published-post metrics that its dashboard discarded, then fetched the recent feed. Four providers were processed serially. Thirty provider calls and about 3.17 s per view. | Remove the discarded reads and run independent providers through a bounded eight-thread pool. Eight reads and 331 ms on the cold controlled request. Very high impact. | Medium |
| 2 | Window changes, recent-post views and analysis repeatedly fetched unchanged social data. Four simultaneous forced refreshes made 120 provider calls. | A 60-second scoped read cache coalesces in-flight work. Explicit Refresh bypasses completed entries. Four concurrent refreshes now made eight calls. Very high impact. | Medium |
| 3 | Next Move waited for optional topic research before generating the proposal. The controlled research stage added one second to every fresh batch. | Persist and lease the optional research job, then reuse completed research for 15 minutes. The proposal uses saved strategy, voice and available performance immediately. High impact. | Medium |
| 4 | Compact image previews downloaded the complete original. The representative file was 3,052,910 bytes. | An authenticated 256-pixel preview is 7,667 bytes, a 99.75% reduction. Original media remains the editing/publishing source. High impact on mobile media lists. | Medium |
| 5 | Each draft caused a separate publication-link query. The 100-row endpoint made 106 SQL calls, and Studio fetched 100 rows while showing 20. | Batch publication links, retain pagination, and request only 20 rows in Studio. The 100-row endpoint now uses seven SQL calls. High impact. | Low |
| 6 | Recurring-series listing queried occurrences per series and drafts per occurrence. The workload made 115 SQL calls. | Two batched relationship reads preserve ordering, ownership and cancelled/published status. Seven SQL calls remain. High impact. | Low |
| 7 | Native Schedule awaited saved posts, schedules and recurring series one after another. | Independent reads use structured concurrency with current-authority checks. The native regression reduced three controlled 300 ms waits from 933 ms sequentially to 323 ms concurrently. High impact when network latency dominates. | Low |
| 8 | Owner/brand filtering and ordered draft/calendar queries lacked matching composite indexes. SQLite plans sorted or scanned unrelated partitions. | Two measured indexes remove the unnecessary draft sort and narrow calendar ranges. The SQLite microbenchmark improved approximately 7.18 to 0.41 ms and 7.83 to 0.29 ms. Moderate impact at larger account sizes. | Low |
| 9 | Real password verification accounts for much of the roughly 1.44 s sign-in API baseline. | Retain password work factors and session security. Existing native secure-session reuse avoids password work during normal navigation. Further gains require profiling transport and bootstrap on devices. High cold-start cost, intentionally retained. | High for a safe further change |
| 10 | Studio eagerly loaded 28,199 bytes of planning JavaScript. Asset versions were manual and public cache policy was implicit. | Load planning code on first use and apply content-derived versions to styles, scripts and platform marks. Repeat navigations transfer no public assets in the measured browser trace. Moderate cold-start opportunity, smaller measured gain than backend batching. | Low–medium |

The isolated PostgreSQL 18 experiment confirmed both selected indexes with 50,000 rows per table and 100 samples. Draft-page median latency improved from 0.380 to 0.153 ms, and calendar-range latency from 1.521 to 0.160 ms. EXPLAIN ANALYZE shows the owner/brand draft index scan and calendar index-only scan. These are warm, small-result query measurements. They do not establish full production-request latency.

The trial Activity composite index showed no benefit over its existing draft lookup index and was removed from the candidate. Its rejected measurement is retained in index-candidate-rejected.json.

## API before and after

| Route | Before median | After median | Before p95 | After p95 |
|---|---:|---:|---:|---:|
| Password sign-in | 1438 ms | 1421 ms | 1587 ms | 1568 ms |
| Studio HTML | 28 ms | 51 ms | 164 ms | 204 ms |
| Native account bootstrap | 40 ms | 30 ms | 50 ms | 58 ms |
| 100 saved posts | 513 ms | 58 ms | 585 ms | 74 ms |
| Schedule HTML | 65 ms | 60 ms | 114 ms | 203 ms |
| Recurring series | 525 ms | 48 ms | 577 ms | 76 ms |
| Performance 7-day view | 3165 ms | 118 ms | 3205 ms | 331 ms |
| Performance 30-day view | 3166 ms | 104 ms | 3192 ms | 143 ms |
| Recent social posts | 463 ms | 67 ms | 473 ms | 73 ms |
| Fresh Next Move batch | 1532 ms | 527 ms | 1617 ms | 584 ms |
| Caption generation | 460 ms | 462 ms | 474 ms | 490 ms |
| Compact image preview | 77 ms | 20 ms | 145 ms | 93 ms |
| Public stylesheet | 11 ms | 10 ms | 104 ms | 149 ms |
| Planning script | 8 ms | 8 ms | 9 ms | 11 ms |

The 7-day Performance median includes one cold read followed by nine cached reads. The cold sample made eight provider calls and took 331 ms. Subsequent reads made zero provider calls. The 30-day view reuses the same observed posts and computes its own date window. It preserves the observation timestamp and unknown metrics.

Studio HTML became 22 ms slower in the sampled median, while its query count stayed at nine. Caption generation stayed near 460 ms with 21 SQL calls and the same 300 ms model fixture. No speedup is claimed for these paths. Small-request measurements and ten-sample tail values vary on this Windows host.

Four simultaneous draft requests completed in 444 ms before and 101 ms after. Four simultaneous forced Performance refreshes completed in 3,278 ms before and 578 ms after, with all responses successful. Provider calls fell from 120 to eight for that refresh workload.

The compact-preview after measurement includes first generation followed by in-memory reuse. Its first sample and all response sizes are preserved in the JSON. At the browser test's 4 Mbit/s throughput, its byte reduction removes about six seconds of transfer for this particular image. That is a bandwidth calculation, rather than a separately observed phone download time.

A final correctness review normalised timezone-aware and database-naive expiry timestamps, preventing a just-renewed social token from incorrectly hiding its fresh observations. The new renewal regression and related analytics checks passed 21 focused tests. A further ten-sample run at 9718375 retained the gains, with saved posts at 63 ms, recurring series at 43 ms, repeated Performance reads at 106 ms and fresh Next Move at 571 ms. Its source digest, all samples and eight-call concurrent refresh result are in after-renewal-validation.json. The earlier primary comparison above is retained intact.

## Browser journeys

| Browser journey | Before | After |
|---|---:|---:|
| login page | 1531 ms | 1511 ms |
| login to composer | 2876 ms | 3136 ms |
| studio history ready | 3232 ms | 3347 ms |
| studio repeat 0 | 1070 ms | 817 ms |
| studio repeat 1 | 1078 ms | 815 ms |
| studio repeat 2 | 1077 ms | 761 ms |
| next move open | 3065 ms | 1700 ms |
| next move fresh | 1664 ms | 750 ms |
| next move cached | 357 ms | 372 ms |
| performance ready | 4184 ms | 1412 ms |
| performance window change | 3203 ms | 170 ms |
| schedule ready | 991 ms | 1107 ms |

The repeated Studio navigation median improved from 1,077 to 815 ms. Performance date changes improved from 3,203 to 170 ms. Initial sign-in to the composer measured 2.88 versus 3.14 seconds in the single browser runs, and Schedule 0.99 versus 1.11 seconds. Those journeys need more production/device samples. Cached Next Move opening remained similar.

The final browser traces report no JavaScript page errors. Studio's history response fell from roughly 36 KB for 100 rows to roughly 10 KB for the 20 displayed rows. The planning script is absent until the feature opens. CSS size remains 75,670 bytes for nova.css. Existing gzip is not counted as a newly achieved live improvement. Rendered Schedule screenshots were inspected for layout continuity.

## Other audit findings

- The web product uses FastAPI, SQLAlchemy, Jinja and browser JavaScript. The iPhone product uses SwiftUI. React render and component-bundle concerns therefore map to the actual DOM scripts, SwiftUI state updates and network entry points here.
- There is no third-party charting bundle to remove. Private dashboard payloads remain uncached by browsers. Existing loading states, request-version checks and immediate local draft edits are preserved. Publishing, deletion and social-account connection actions keep their explicit server authority and confirmation rules.
- AI retrieval already bounds recent drafts, prior ideas, schedules and saved voice examples. Creative prompts and configured models remain unchanged. Caption planning and generation have functional dependencies, so they remain ordered.
- Media inspection already caches model results against the source-content fingerprint, model and inspection version. It still reads and hashes the original when checking reuse. A future stored upload digest could reduce that I/O after an immutable-source migration is evidenced. Sampled video inspection and the original video delivery paths remain intact.
- Existing PostgreSQL pooling uses pre-ping, five base connections, ten overflow connections and a capacity check for multi-service mode. Provider tasks receive immutable snapshots, never SQLAlchemy sessions. There is no evidence here supporting a larger pool, larger Render instance or a hosting migration.
- Some caller transactions can remain open while waiting on external providers. Production pool-wait and slow-query telemetry should establish whether further transaction shortening is worthwhile before changing transaction boundaries.

## Correctness, privacy and reliability

Provider cache entries include owner, brand, provider, current connection/permission/token fingerprint and local publication activity. Each result is checked against current active ownership and grants after the provider read. Disconnects or account replacement during collection discard the result. Current Refresh semantics are preserved for older iPhone clients that omit the new flag. Missing metrics remain missing, and cached observations keep their original checked time.

The read cache coalesces concurrent misses, copies values on return, expires after 60 seconds and is bounded to 64 entries of at most 128 KiB each. Exceptions are retryable. A clear operation prevents an in-flight result from repopulating cleared storage. Available metrics may remain unavailable during the short reuse interval, with explicit Refresh available to retry.

Private thumbnails verify owner, brand and current source version on each request. They use one decoder slot, resize before EXIF-copy operations to limit peak memory, strip metadata from the small JPEG and retain no permanent derivative files. The original file remains unchanged. Private pages, APIs and media retain no-store.

Optional research has one persisted row per owner/brand, a conditional three-minute lease, a five-second worker poll and three bounded attempts with backoff. Crashed leases recover. Exhausted jobs wait for a later eligible request after cooldown. Strategy changes, account deletion and withdrawn AI consent invalidate old work. Newer requests cannot be overwritten by older results. Actual provider usage is recorded within the originating recommendation action without consuming a second customer action. A model request interrupted by a process crash can incur a repeated provider cost when retried. These jobs never publish content.

Account export includes the research state. Account deletion cancels research, clears cached observations and includes the job row in erasure. Broader privacy and commercial findings remain in the existing 79-entry register.

## Validation evidence

Application validation at 054588b passed 773 SQLite tests and 774 PostgreSQL tests, along with browser journeys, JavaScript checks, dependency audits, image build, constrained-host password checks, backup recovery and the exact beta guard. Two SQLite tests and one PostgreSQL test were skipped according to the existing environment-specific suite.

The initial complete run found an isolated template fixture missing the new asset helper. The fixture was corrected to use the production helper and both database suites passed on rerun. The final public-icon cache and thumbnail memory refinements passed focused checks and the full 054588b application workflow, including the PostgreSQL timing experiment. Native validation 41253265325 passed 44 unit tests, 19 interface tests and iPhone Release compilation. The final follow-up checks and PostgreSQL timing experiment are attached to PR 37. Final run details are recorded in VALIDATION_RESULTS.md.

## Remaining risks and next improvements

1. Run an authenticated canary after backend rollout and collect real p50/p95 timings across Studio, Performance, Next Move, captions and sign-in. Keep content and credentials out of telemetry. Synthetic model and provider delays cannot establish live tail latency.
2. Confirm the native changes on a physical iPhone with real network conditions, including saved attachments, account switching, app restoration and connection cancellation. Simulator evidence complements this device check.
3. External-provider delays can still hold a cold Performance view. The bounded pool and partial-result handling limit the effect, while truly progressive per-provider cards would need a separately measured API/UI change.
4. The cache is process-local. More replicas reduce its hit rate and increase provider reads. Measure hit rate and provider quotas before considering a shared cache or additional infrastructure.
5. Optional research requires a running compatible worker. Pending jobs survive restarts, but sustained worker failure requires operational attention. Its latest state is retained per brand until replacement or account erasure.
6. Cold login, caption generation and full mobile page rendering still need device profiling. Preserve password security and AI grounding. Avoid speculative model downgrades, broad CSS rewrites or optimistic publishing.
7. PostgreSQL index plans and performance are measured in the isolated workflow. Production cardinality, cache residency and disk behaviour can differ. Observe actual slow queries and pool waits after rollout.

## Deployment and rollback

Use the established backup and offline schema preparation with ZOVA_SCHEMA_MODE=initialize to add zova_discovery_jobs. Run scripts/prepare_performance_indexes.py with the migration identity to create the two reviewed indexes concurrently on PostgreSQL. The script verifies the index definitions and their valid/ready state, and fails if an existing index requires repair. Runtime verification mode never repairs missing schema.

Deploy the compatible backend before distributing the new iPhone binary. Older clients retain original media downloads and fresh Performance refreshes. Observe worker completion, API errors and provider-call volume during the canary. A code rollback can leave the additive table and indexes in place. Pending research resumes when a compatible worker returns.

The implementation is prepared for review in [PR 37](https://github.com/davidwilson92-cpu/DataMaxxing/pull/37). The App Store submission and customer charging settings are outside this candidate's release actions.

## Reproduction and evidence

- baseline.json and after.json contain the primary endpoint samples, SQL/provider counts, source digests and concurrent-request results. after-renewal-validation.json verifies the final token-renewal safeguard against the same workload.
- baseline-browser.json and after-browser.json contain browser timings, resource transfers, paint observations and long tasks. The adjacent PNGs show the rendered Schedule.
- production-public-baseline.json contains the real public probes and cache headers.
- index-benchmark.json contains the SQLite experiment. index-postgres.json is exported by the final isolated PostgreSQL workflow.
- benchmark_performance.py and benchmark_browser.cjs run the disposable application and browser workloads. Set BENCH_SOURCE_ROOT to the clean base worktree for the baseline. Run browser-only journeys against a fresh fixture after the endpoint samples to avoid carrying warm provider state into the browser comparison.
- benchmark_indexes.py creates a disposable SQLite database by default. In CI it accepts only an explicitly isolated loopback ZOVA_TEST_POSTGRES server and creates a separate zova_test_performance database, refusing to overwrite an existing one.
