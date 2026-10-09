# Production guardrail remediation and release process

The normative baseline is `docs/PRODUCTION_GUARDRAILS.md`, preserved from the owner's supplied document. `assessment.json` records every section; `ASSESSMENT.md` is the readable initial appraisal. **Production is blocked.** Passing unit tests does not close the register.

Run `python scripts/guardrail_iteration.py --output ../guardrail-evidence` to execute a local iteration. It creates a fresh evidence directory, validates the register, runs the full synthetic suite, runs the production gate, and writes the remaining actions in priority order. It exits nonzero while anything is blocked and never automatically changes assessment statuses. PostgreSQL, hosting and operational evidence remain separate required checks.

## Repeat for each increment

1. Select the highest-priority unresolved requirement in the register. Identify the affected objects, endpoints, workers and user journey. Inspect the current implementation and deployment evidence; distinguish a confirmed defect from missing assurance.
2. Write a regression that reproduces the unsafe behavior or a measurable acceptance procedure for operational/product requirements. Use isolated synthetic data and mocked external writes.
3. Make a compatible, bounded change. Keep customer identities, credentials and data intact. Database work needs a versioned migration, backfill reconciliation, restricted-role tests and a forward-recovery plan before rollout.
4. Run the regression, relevant integration tests, the full suite, PostgreSQL CI, migration/restore checks and deployment-image checks. Add browser/accessibility, load, contract or external-security evidence when the requirement calls for them.
5. Update the finding and next action. A section remains `partial`, `gap` or `unverified` until **all applicable requirements within it** have evidence. Do not mark it `met` because one test or source file exists. `not_applicable` needs a concrete scope rationale and an accountable review.
6. Store sanitized evidence in `docs/guardrails/evidence/` or link a versioned evidence summary there. Never commit credentials, production exports, customer content or private provider diagnostics. Each evidence entry names a repository-relative file and its SHA-256, normalized to LF. Supply `reviewed_by` and ISO `reviewed_at` only for an actual accountable review.
7. Run `python scripts/release_gate.py --check`. It verifies complete coverage, baseline integrity, evidence hashes and review fields. A successful register check **is not release approval**.
8. Run `python scripts/release_gate.py`. Any unresolved applicable section, missing evidence or stale source review returns a nonzero exit code. Continue from step 1. Severity affects work order; even a P2/P3 applicable requirement must be closed to meet the owner's full release gate.
9. Once all evidence is complete, obtain an actual review of the candidate and put `python scripts/release_gate.py --fingerprint` in `reviewed_source_digest`. The fingerprint covers application, tests, scripts, CI, dependency specification and deployment configuration. A source change invalidates the review. Run the full gate again.

Do not weaken the baseline, skip a failed test, invent approval, or add a blanket waiver to make the gate green. The gate checks evidence integrity and recorded decisions; it cannot establish that a human attestation is truthful. Review and protected repository/hosting permissions remain essential.

## Prioritized architectural increments

| Order | Increment | Required closure evidence |
|---|---|---|
| 1 | Canonical tenants, memberships and six-role capability enforcement | Verified mapping/backfill of legacy owners; two-tenant attacks on every sensitive object and operation; no unauthorized reads/writes |
| 2 | Restricted PostgreSQL roles and RLS | Separate migration/application/worker/admin identities; direct database attack tests under non-owner roles; rollback/forward recovery rehearsal |
| 3 | MFA/identity and recovery | Owner/staff MFA, supported recovery, session privilege-change revocation, compromised-password checks; compatibility with existing identities |
| 4 | Finish publishing architecture | Legacy idempotency and worker routing; independent always-on worker; retry classification, dead-letter operations, quota backpressure, global/owner pause; every §61 fault scenario |
| 5 | Privacy, private media and audit | Private expiring asset delivery, retention execution, owner export/deletion, provider/billing/storage reconciliation, immutable attributable action records |
| 6 | Operational assurance | Secret rotation, alert delivery, SLOs, measured backup restore/RPO/RTO, incident and OAuth-compromise exercises, environment separation |
| 7 | Product and independent verification | All critical responsive/loading/error/empty journeys; WCAG 2.2 AA review; load and provider contract tests; ASVS Level 2/independent security review |

These are work packages, not completed approvals. Infrastructure configuration, legal/privacy review and an independent penetration test cannot be inferred from local code.

Owner direction, 9 October 2026: optional authenticator enrollment is authorised.
Existing accounts must not be forcibly enrolled. Privileged mandatory MFA and
verified support recovery remain separate unresolved requirements. See
`OPTIONAL_MFA_20261009.md` for validation and rollback constraints.

The owner also paused paid staging until the app is approved. Preserve the
follow-up in `STAGING_PLAN.md`; do not create resources or incur charges.
Continue locally testable work. Once the owner confirms app approval, revisit
the staging plan and costs before provisioning. Neither deferral closes a gap.

## Enforce the gate outside this branch

- The workflow adds the **Production guardrails** check, dependent on successful application and PostgreSQL jobs. It is intentionally red while the register has open items.
- Repository administrators must require that exact check in protected-branch/ruleset policy, prevent bypass, and review changes to the gate and baseline. This branch cannot itself enforce GitHub account settings.
- Verified on 28 September 2026: GitHub ruleset `24140009` is Active on `main`,
  requires `Production guardrails`, `synthetic-tests`, and `postgres-release`
  from GitHub Actions, requires up-to-date branches and resolved conversations,
  and blocks force pushes and deletions. Its bypass list is empty. Required PR
  approvals are currently zero; this does not establish independent review.
  [Ruleset](https://github.com/davidwilson92-cpu/DataMaxxing/settings/rules/24140009).
- `render.yaml` adds `preDeployCommand: python scripts/release_gate.py`. Confirm that the actual hosting service consumes this blueprint and that no alternate deploy path bypasses the command. Editing YAML does not prove a deployed service has adopted it.
- Do not merge/deploy this candidate as production-ready while those controls or the register remain open. A draft remediation PR can still run application tests and show its blocked production check.

## Iterations completed in this candidate

1. Preserved the complete 79-section baseline; built an evidence register, strict validation, fail-closed release command and CI/deployment-blueprint hooks.
2. Applied a shared 15–256-character policy to signup/reset/change, rejected a small local common-password list, retained existing login compatibility, and updated form guidance. A maintained breach corpus and MFA remain open.
3. Removed raw exception output from selected voice/AI/legacy-send paths and scheduler logs; removed an unused unrestricted URL fetcher. A full egress and telemetry audit remains open.
4. Rejected tenant ownership reassignment through ORM flushes, verified the exact owner/brand/account/media at worker dispatch, and capped PostgreSQL pool overflow. Raw SQL/RLS defense and fleet capacity remain open.
5. Moved immediate Studio publishing into the existing durable job table atomically with approval and publication state. Added safe recovery for crashes before the external-send claim and retained non-retry behavior after ambiguous sends. Added queued-state UX and cancellation. Legacy Custom GPT publishing remains a release blocker.
6. Reproduced cross-brand connection/media/draft and missing-permission failures
   in pre-ledger scheduled jobs. Added exact ownership, brand, account activity,
   platform, media-reference and scope checks before dispatch. Rejected jobs
   become failed without a provider call; ambiguous sends stay unknown and are
   never automatically retried. This does not resolve the separate synchronous
   `/x/post` route or establish database RLS.
7. Pinned all validation actions to commits verified in their official GitHub
   repositories, disabled persisted checkout credentials, bounded job runtimes
   and evidence retention, and added reviewed dependency-update configuration.
   Application/dependency locks, image digests, independent review and cloud
   access assurance remain open. See `CI_SECURITY.md` for update procedures.
8. Replaced synchronous Custom GPT X sending with a creator-scoped idempotency
   ledger and durable worker jobs, explicit queued/status responses, conditional
   cancellation, immutable approval fields and conservative unknown outcomes.
   Added a versioned additive migration, restore comparison, dedicated worker
   entry point and metadata-only operational signals. The GPT action contract
   must be updated before rollout; see `LEGACY_QUEUE_ROLLOUT.md`. The independent
   worker is implemented but not deployed or operationally certified.
9. Added exact owner/brand/draft/review/account checks before Instagram and TikTok
   result reconciliation, with adversarial tests. These application checks do
   not replace the remaining canonical workspace/membership/RLS migration.
10. Replaced permanent local media delivery with authenticated owner previews
    and signed downloads (five-minute previews, at most one-hour provider URLs).
    S3 delivery now generates expiring URLs instead of trusting stored public
    URLs. Unsigned, modified and expired local URLs are rejected. Existing bucket
    policies, cache copies, persistent storage and provider fetch compatibility
    still require deployed evidence; see `PRIVATE_MEDIA_ROLLOUT.md`.

The Render inventory review found `zova-cs-staging` runs a different repository
and `zova-tiktok-sandbox` shares the production database. Neither is approved for
these migration tests. See `STAGING_PLAN.md`; no cloud services were changed.

## Rollback and operational limits

Iteration 8 adds the `zova_legacy_publications` table through migration
`20260929_legacy_publication_queue`; historical sends are never backfilled as
work. Follow `LEGACY_QUEUE_ROLLOUT.md` before rollout or rollback. Earlier queued
Studio publishing uses existing `ScheduledPost` and `Publication` records. Do
not deploy old workers over those records without first pausing writes and
reconciling/draining them: old recovery can mark queued work unknown after
15 minutes. Preserve all unknown/pending outcomes and never blindly resend.
No rollback should restore an older database or rotate encryption keys to undo code.

The existing scheduler wakes on its configured interval (default 60 seconds). The queued UI states that work is saved and continues after closing the page. A production deployment still requires an always-on worker, operational alerting and capacity verification. In-flight calls cannot be safely recalled by closing a browser.

This branch changes the proposed release policy; it does not alter the running service or claim current production compliance.
