# Performance validation results

## Reviewed implementation

Runtime candidate 054588b5f4d59ff9ea3d3888f1598e9666f7f5a5.

Measured runtime content digest
`30145425a168d2a3388d36e58e0fe2ce0ea0cef41a4301d142f68539d99436a4`.

The digest covers the actual nova and ios files. It matches the final measured
working tree. Subsequent evidence-document commits do not change runtime, tests,
workflow definitions or the pinned release scope.

## Application and PostgreSQL

The complete application workflow passed at the reviewed implementation on
1 November 2026. SQLite passed 773 tests with two environment-specific skips.
PostgreSQL passed 774 tests with one skip. Browser journeys, JavaScript checks,
backup/restore verification, image build, constrained-host password work,
dependency audits and the exact beta guard also passed.

[Application validation 41254789905](https://github.com/davidwilson92-cpu/DataMaxxing/actions/runs/41254789905)

The workflow created a separate loopback zova_test_performance database and
benchmarked 50,000 rows per measured table. Both selected indexes were used by
PostgreSQL. Draft-page median query time improved from 0.380 to 0.153 ms and calendar
range time from 1.521 to 0.160 ms. The existing Activity draft lookup remained
approximately 0.11 ms. See index-postgres.json for EXPLAIN ANALYZE, buffers, p95
samples and row counts.

## Native iPhone

Native validation passed 44 unit tests, 19 UI tests and iPhone Release compilation.
The controlled Schedule test measured 933.49 ms sequentially and 322.83 ms in
parallel with three 300 ms transport waits.

[Native validation 41253265325](https://github.com/davidwilson92-cpu/DataMaxxing/actions/runs/41253265325)

That run used 0359bc6. A Git comparison confirmed no differences in ios or
.github/workflows/ios-beta.yml between it and the reviewed runtime 054588b.
Native tests exercise isolated simulator fixtures. Physical-iPhone performance,
real providers and an updated TestFlight binary remain deployment acceptance work.

## Benchmark and visual evidence

Endpoint, browser, concurrency and source-digest evidence is in baseline.json,
after.json, baseline-browser.json and after-browser.json. The latter browser
reports zero JavaScript page errors. Both Schedule screenshots were inspected.

The ten-sample endpoint timings and single mobile-browser journeys are controlled
comparisons. AI/provider timing inputs are simulated. Public production probes are
recorded separately. The audit lists remaining cold-start, provider-tail,
transaction and device-measurement risks.

## Release state

The implementation and evidence are prepared in PR 37. Production deployment,
additive database preparation and a new iPhone distribution remain pending.
Render hosting and the disabled customer-charging requirement continue to apply.
The retained 79-entry commercial register is complete and keeps its prior statuses.

[Current review and checks](https://github.com/davidwilson92-cpu/DataMaxxing/pull/37)
