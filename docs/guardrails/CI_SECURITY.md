# Validation supply-chain controls

All Actions in the validation workflow are pinned to full commits rather than
movable tags. These refs were resolved directly from the official repositories
on 28 September 2026:

| Action | Upstream tag | Verified commit |
|---|---|---|
| actions/checkout | v4 | 11d5960a326750d5838078e36cf38b85af677262 |
| actions/setup-python | v5 | a26af69be951a213d495a4c3e4e4022e16d87065 |
| actions/upload-artifact | v4 | ea165f8d65b6e75b540449e92b4886f43607fa02 |

Checkout does not persist credentials for later test/build commands. Workflow
permissions remain read-only for repository contents. Validation runs on hosted
runners using synthetic data; no production secrets are supplied. Job timeouts
bound stalled execution; uploaded test/audit evidence expires after 30 days.

Dependabot configuration proposes weekly updates for Actions and Python packages.
It takes effect after the configuration reaches the default branch; it is not
yet evidence of an active update service. There is no automatic merge. Review
the upstream source and release notes, verify action commits belong to the
official repository, and run the required checks before accepting updates.
Treat critical vulnerability remediation as urgent; do not wait for the weekly
schedule. Record unresolved vulnerabilities as release blockers.

Full Python/transitive locks, immutable container image references, static/type
analysis and independently reviewed cloud/registry access remain outstanding.
These controls do not prove that upstream code itself is trustworthy or that
all supply-chain requirements are met. Preserve the existing required checks
and keep the production gate blocking while the assessment remains open.

Reference: [GitHub secure use guidance](https://docs.github.com/en/actions/reference/security/secure-use).
