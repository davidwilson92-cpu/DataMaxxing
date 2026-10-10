# Explicit usage and billing ownership

Usage reservations previously resolved a global key without verifying its owner or kind; completion accepted only a key. Existing routes generate keys and check ownership, so this is an internal boundary defect, not a demonstrated external account takeover.

The candidate validates owner, kind, key and amount before accounting. Completion now requires owner and kind at every publishing, scheduling, series and AI caller. Matching retries share one reservation; active amounts cannot change. Released reservations can legitimately move to a new accounting month and amount. Disabled subscription limits remain independent of billing availability.

Billing lookup checks the canonical key against stored owner and test/live mode before locking, displaying membership or resolving limits. A mismatch returns a support page with signed-in navigation, no foreign billing identifiers and no checkout. Disabled billing cannot create an off-mode record. Existing testing/free-beta access stays enabled.

Validated 0f8ada5: local/CI SQLite 524 passed / 87 expected skips; PostgreSQL 609 passed / two expected skips. CI 38048348613 also passed synthetic restore, image build/smoke and dependency audit. Evidence: evidence/usage-ownership-20261010.json. The first full run caught a fixture using disabled billing while testing a mocked checkout. The fixture now explicitly selects test mode; a separate regression verifies disabled mode does not create billing records. No expected security assertion was weakened.

Browser review used a static rendering of the real mismatch response with synthetic users and existing assets: 1280x720 desktop and 390x844 mobile. Text and primary action fit without overlap. Keyboard Tab moves from support through verification to Back to Studio, with a visible focus ring. This verifies the page presentation, not live subscription or cross-page navigation.

Remaining work: database invariants for billing key/mode/customer binding and usage key/kind; restricted account service integration; live provider, operational and independent review evidence. Application checks do not establish protection against arbitrary direct database writes. Account RLS stays offline until compatible lifecycle routes and grants are complete.

Rollback: this increment changes application checks and call signatures only, not stored data or schema. Roll back the complete increment and all finish callers together if necessary; do not mix signatures or rewrite usage/billing records. Preserve earlier additive security migrations and unknown publication outcomes. No production deployment, paid setup, provider requests or customer data changes were performed.
