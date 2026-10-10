# Account policy authority and operation coverage

Validated d388dd6: CI run 38010717743 passed 576 PostgreSQL tests (two expected
skips), 491 SQLite tests (87 expected skips), account/workspace restore, image
build/smoke and Python dependency audit. The full production gate remains blocked.

The previous policy verifier compared table flags, complete policy predicates,
function definitions and execution recipients. It did not recheck runtime-role
attributes and effective privileges after installation, or distinguish a function
grant with delegation authority. An administrator granting BYPASSRLS could therefore
invalidate row isolation without changing any of those policy definitions.

Verification now reuses the installer's role-authority checks: no superuser,
database/role creation, replication, RLS bypass, privileged-role membership,
migration-owner membership, schema/database creation or destructive table rights.
Function execution must have exactly the declared recipients, with no grant option
for runtime roles. Verification is read-only and reports drift without repairing
it. This is not continuous monitoring and cannot prevent an administrator changing
privileges after verification.

The PostgreSQL regression deliberately enables BYPASSRLS in an isolated role,
confirms that otherwise unchanged policies now expose both synthetic owners, then
requires verification to reject that role. Additional cases exercise role creation,
schema creation, TRUNCATE, inherited predefined privileges and function delegation.
No production role or database is used.

Operation coverage checks read-only contexts cannot insert or delete across all
13 account tables, with explicit row-policy errors rather than accepting unrelated
SQL failures. Editing contexts cannot delete security/billing/membership/measurement
records or foreign preferences. Own preference replacement and temporary brand
creation/deletion succeed. These direct-SQL tests verify row authority; they do not
constitute the application brand-provisioning workflow, which must atomically
provision its canonical workspace and membership through dedicated service routing.

Account policies remain an offline foundation. Full service integration, exact
account column grants, secondary identity invariants, runtime drift monitoring,
operational evidence and independent review remain open. Forward recovery must
retain data and protections: pause writes, diagnose failed verification and repair
via the trusted maintenance path. Do not disable RLS, grant runtime ownership or
restore old customer data to get a service running. Production remains unchanged.
