# Account protection verification and startup enforcement

Candidate only; full local/PostgreSQL validation pending. Production unchanged.

Regressions reproduced startup acceptance with a missing account guard and SQLite
verification accepting a same-name trigger whose body did nothing. Account guards
now have catalog-only verification, independent of the offline row-integrity scan.
This allows restricted service identities to verify protection without reading
customer account contents or receiving additional grants.

SQLite installation and verification share the complete three-trigger definitions
for each account table, comparing normalized source. PostgreSQL verifies the exact
function body, language, volatility, invoker security, search path and trigger
shape, including all-column UPDATE coverage. Foreign keys must be validated,
immediate, non-cascading, target the local account primary key and have enabled
enforcement triggers. Multiple matching foreign keys must all meet this policy.
Owner nullability matches the manifest, including nullable anonymous AI usage.

Runtime schema verification now requires the account migration version and guard
definitions. Populated bootstrap databases also fail before schema work when
account guards are absent. Separated-service configuration checks the same catalog
in addition to workspace policies/functions and its existing grant manifests.
No runtime verification repairs missing protection.

Fresh explicit bootstrap installs the guards alongside workspace protection. The
offline preparation command sets its internal account-preparation marker only
after requiring explicit migration credentials and --apply --writes-paused. This
allows existing schema preparation followed by guarded account migration. Ordinary
startup never sets that marker, and PostgreSQL's default verify mode ignores it.
It must not be set in a deployed service's environment. Earlier workspace registry
and reference migrations remain prerequisites for populated databases.

Tests cover missing guards, altered SQLite definitions, cascading/additional
cascading/deferrable/unvalidated PostgreSQL foreign keys, disabled enforcement,
changed function security and narrowed triggers. The populated offline-upgrade
test verifies refusal, explicit preparation, and preserved email/hash/security
version. Existing legacy-upgrade tests also preserve canonical draft content.

Remaining: account RLS/read/delete/insert authorization, secondary identity fields,
registration/callback/worker integration, runtime post-startup drift monitoring,
production rehearsal and independent security review. These checks verify the
declared account-owner guard policy, not all possible database schema changes.

Rollout must install the offline migration before starting this candidate. Keep
accounts, data, credentials and ownership protections during forward recovery.
Never set an offline preparation flag to bypass runtime failure; diagnose and
repair through the authorised maintenance process with writes paused. No production
migration, flag, service configuration or deployment was changed here.
