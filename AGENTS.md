# Zova beta follow-up instructions

Read ZOVA_CONTINUE_HERE.md, docs/beta/KNOWN_GAPS.md and docs/beta/deferred-register.json before any update. The owner authorised a limited beta on 10 October 2026 and explicitly requires the known defects, security gaps and missing evidence to be addressed on future updates. Reproduce and prioritise them, implement bounded compatible fixes, validate, and update evidence; never silently forget or mark deferred findings resolved.

Do not deploy the unfinished broad account/service/RLS migration. Preserve users, data, uploads, authentication continuity, encrypted social connections, both Instagram routes, explicit publishing confirmation and unknown-outcome duplicate prevention. Keep charges/subscription enforcement disabled for testing. No paid staging or forced customer MFA without explicit approval. Broader commercial readiness remains unapproved.

The beta release gate is pinned to an exact candidate scope and known-gap register; runtime changes require a new deliberate review and validation. Required application/PostgreSQL checks remain mandatory. Do not fabricate a passing status or modify repository protection to merge.
