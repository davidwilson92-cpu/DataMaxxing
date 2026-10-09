# Installed workspace policy verification

Candidate only. Validated at e3376ef: CI SQLite 415 passed / 50 expected skips;
PostgreSQL 464 passed / one expected skip. CI run 38000761139 passed migration/
restore, full restored access-control verification, image build/smoke and
dependency audit. Evidence: `evidence/policy-verification-20261009.json`.
No live deployment,
schema, role, account, credential or provider state changed.

The previous startup check proved the context-function definitions and selected
service grants, but did not establish that PostgreSQL actually applied the
expected table policies. Disabling row security or weakening a policy could
therefore leave correctly checked functions unused by content queries.

Staged service construction now reads PostgreSQL catalogs for every one of the
16 workspace-owned tables. Each must be an ordinary table with both row security
and forced row security enabled. The complete policy set must match: four public
restrictive operation policies and one permissive runtime policy for the exact
configured runtime identities. Read predicates, mutation predicates and insert/
update checks must match the expected full canonical expression, including the
operation's exact capabilities. Unknown policies, missing policies or different
roles/commands/permissiveness are rejected. No substring/name-only matching is
used. Unexpected PostgreSQL deparser formatting fails closed; supported database
versions require CI verification before adoption.

The verifier uses the same operation_capabilities manifest as installation. It
reads actual definitions and does not execute policy functions, create objects,
repair drift or trust a database-stored digest. Startup remains read-only.

Synthetic tests reproduce acceptance by prior startup checks, demonstrate
unbound draft disclosure when protection is disabled/weakened, and require the
new startup check to reject each mutation. Adding another permissive policy
alone still cannot override the existing restrictive boundary, but is rejected
as an unexpected configuration. Explicit offline reapplication repairs known
policies; unexpected policies require a separate reviewed disposition. The
backup restore check now also verifies the full policy/function definitions.

Limits: this verifies the installed policy manifest, not complete runtime/worker
column grants, account-level isolation or all web/worker authority routing. It
does not detect an administrator's changes after startup. Restricted migration
administration and runtime integrity monitoring remain operational work. The
partially mapped service mode still must not be enabled for customers.

Rollback before activation is code-only. After activation, a mismatch requires
investigation and a reviewed offline repair with writes paused, not a bypass or
an automatic policy rewrite at startup. Keep existing customer records, keys,
security versions and pending/unknown publications intact.
