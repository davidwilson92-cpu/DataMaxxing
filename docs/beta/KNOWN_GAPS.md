# Beta known gaps and required follow-up

On 10 October 2026 the owner authorised a limited beta for personal testing, deferring the broader commercial-readiness work until later. This is not a certification or a finding that any security issue is fixed.

## Release boundary

Use the focused UX candidate from PR 17, based on live 38f1c265. Do not deploy the unfinished account/service/RLS migration from PR 18. Authentication, encrypted social connections, existing approval controls and billing testing settings remain as in the focused candidate. No paid staging, forced MFA or real provider posts are authorised as release tests. The live hostname remains publicly reachable; beta does not make it private.

## Next update instruction

Whenever the owner next requests updates, read this file, ZOVA_CONTINUE_HERE.md and deferred-register.json first. Reproduce relevant findings against the actual deployed revision, prioritise security/data-loss/publication risks, implement and test bounded fixes, and update the status/evidence. Report what remains deferred. Do not silently drop these items, mark them fixed because tests pass, or publish the broad migration wholesale.

## Priority work

1. Complete compatible account/service isolation and exact database grants before enabling it. The focused beta does not contain the later optional MFA, identity and usage-ownership fixes; re-evaluate and integrate them incrementally.
2. Complete provider disconnect/revocation and scheduled-work cancellation, worker recovery, duplicate prevention and emergency automation pause.
3. Establish staff authentication/MFA, audited support access, immutable critical-action logging and actionable security monitoring.
4. Complete deletion/export and approved retention cleanup, secret rotation and private-media/egress protections.
5. Verify isolated staging, real hosting controls, production-like upload/key/database recovery and rollback; paid resources still need cost approval.
6. Complete full browser/mobile/accessibility/provider/load testing, independent security review and privacy/operator decisions before commercial launch.

## Evidence interpretation

The saved register retains all 79 sections from the broader candidate at f1dcc0f. Its evidence paths and implementation claims refer to that branch, not necessarily this beta. Earlier next actions may be partly superseded; reconcile them rather than treating all entries as new bugs. Preserve the full commercial gate on the remediation branch. Beta scope acceptance changes release policy only, not the findings.

## Rollback

Redeploy live baseline 38f1c265 while retaining data, uploads, credentials, session keys, publication ledgers and additive title/performance schema. Do not restore stale customer data or replay uncertain publications. Stop dispatch and investigate if a publication outcome is unclear. See docs/UX_RELEASE_20261008.md.
