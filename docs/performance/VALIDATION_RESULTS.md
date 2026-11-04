# Final performance validation

Validated runtime 9e7aad18dbc3af20e6a5f7ce97ef3dfc78ecdc5c.
All checks on PR 37 passed for this runtime on 1 November 2026.

## Application

774 SQLite tests passed with two skips. 775 PostgreSQL tests passed with one skip.
Browser journeys, JavaScript checks, dependency audits, hosting-image build,
constrained-host password checks, backup recovery, PostgreSQL timing measurements
and the pinned beta guard passed.

[Application run 41258233905](https://github.com/davidwilson92-cpu/DataMaxxing/actions/runs/41258233905)

[Pull-request application run 41258238988](https://github.com/davidwilson92-cpu/DataMaxxing/actions/runs/41258238988)

## Native iPhone

44 unit tests, 20 interface tests and iPhone Release compilation passed.
The screen's actual summary/saved-post/month-delivery loader measured 927.87 ms
sequentially and 306.21 ms concurrently with three controlled 300 ms transport waits.
The six-week calendar, landscape, largest text, schedule management and return-to-
Studio checks passed. Their screenshots were inspected.

[Native run 41258239044](https://github.com/davidwilson92-cpu/DataMaxxing/actions/runs/41258239044)

An earlier run at b284ef9 passed unit tests but stalled in five Schedule-related
interface checks. Review also found that the first concurrency change targeted an
unused helper. The final implementation connects the screen to the shared parallel
loader, uses bounded eager calendar rows and decodes each post timestamp once per
render. The five failing cases and the added six-week-month case pass in the final run.

## Measurement provenance

The primary baseline and optimisation comparison are retained in baseline.json,
after.json and the adjacent browser evidence. The final token-renewal safeguard
was measured in after-renewal-validation.json at 9718375. Its combined runtime digest
is 3f9b02377b7c861df37e8ac8e1d5f4dc1acae9c2392630883af852681e527c36.
A Git comparison confirms no web/backend or benchmark-script differences between
9718375 and final runtime 9e7aad1. The native follow-up is measured and tested
separately by the final native run above.

The PostgreSQL 18 timing experiment at 054588b used 50,000 rows per measured table
and 100 samples. It measured draft query medians of 0.380 to 0.153 ms and calendar
query medians of 1.521 to 0.160 ms. Both selected indexes appear in EXPLAIN ANALYZE.
The final application workflow repeats this experiment. No index-definition changes
were made after the initial PostgreSQL result in index-postgres.json.

## Remaining release work

The measured provider and creative-model delays are controlled inputs. Real
production-provider/model latency and physical-iPhone performance need a canary
and device pass after rollout. Production deployment, additive database preparation
and a new iPhone distribution remain pending. Render hosting and disabled customer
charging remain the release requirements. The 79-entry commercial register retains
its prior statuses.

[Implementation and current checks](https://github.com/davidwilson92-cpu/DataMaxxing/pull/37)
