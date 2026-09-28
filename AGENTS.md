# Zova engineering guardrails

Read `docs/PRODUCTION_GUARDRAILS.md`, `docs/guardrails/assessment.json` and
`docs/guardrails/ITERATION_PROCESS.md` before changing this application.
The 79-section production baseline is required, not optional guidance.

For each change, reproduce the relevant gap, implement a bounded fix, validate
with isolated tests, and update the affected assessment findings and evidence
hashes. Preserve customer data, identity links, credentials and publication
outcomes. Never resend an uncertain external action to make a test or status pass.

Run the relevant tests, the complete test suite and
`python scripts/release_gate.py --check`. Production additionally requires
`python scripts/release_gate.py` and the required PostgreSQL, deployment,
operational, product and security evidence. A successful register-integrity
check is not production approval. Keep unresolved or unverified requirements
open; do not invent reviews, weaken criteria, or waive failures to get a green gate.

Use `docs/guardrails/ITERATION_PROCESS.md` for the remediation order, release
enforcement and rollback constraints. Existing historical release notes do not
override the current guardrail assessment.
