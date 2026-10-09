# Restricted draft-service privileges

Candidate only; local and PostgreSQL validation pending. No production role,
grant, data, credential, provider or deployment changed.

The earlier row-policy fixture granted broad operations on every workspace
table. Row isolation alone did not prevent a draft-service connection from
reading its workspace's encrypted social credentials or editing an approval
payload with an issued publishing capability. Those privileges are unnecessary
for the currently mapped draft endpoints.

An explicit table/column manifest now defines the draft service's grants. It
can read/create/edit/delete drafts, read planning context, validate attachment
metadata and perform the existing atomic cleanup of a deleted unsubmitted
draft. Updates cannot alter draft IDs, ownership, creation times or delivery
status. Review access permits locating/deleting the obsolete review during
draft deletion, not reading or modifying its approved payload. Delivery tables
expose only ownership and identifiers needed to retain delivered history.
Attachment validation selects metadata without storage locations or analysis
payloads. Activity summaries select platform/link fields rather than full rows.

The issuer has no direct table/column privileges; it executes its separately
checked context function. Sequence verification now applies to all configured
services: only the draft allocator may be used, with no reset/UPDATE privilege
and no access to other identifier allocators. Authentication, identity, recovery
and issuer services have no sequence grants. This is a read-only startup check,
not automatic role provisioning or grant repair.

Tests reproduce excess authority under the broader row-policy fixture, then
test denied credential/media-location/approval/account access, delivery-state
mutation, sequence reset and unauthorized allocation under the restricted role.
Startup rejects missing or excessive table/column/sequence privileges. Actual
default/second-brand HTTP flows include attachment persistence, Instagram Story
selection, foreign-attachment rejection, linked planning context and atomic
review/plan cleanup. Providers remain mocked and data is synthetic.

This manifest is complete for the currently mapped draft routes, not for all
Studio, publishing or worker routes. Additional services require separate
authority/grants and tested route integration. Trusted identity/auth/recovery
account isolation, signup/lifecycle, callback/telemetry/worker integration,
production grant provisioning/restore rehearsal and operational review remain
open. The partially mapped mode must remain disabled for customers.

Before activation, rollback is code-only. After activation, do not restore broad
grants to make a route pass: pause the affected service, verify the manifest and
use a reviewed compatible repair. Preserve data, security versions, immutable
approvals and unknown publication outcomes. Never retry an external send as a
database permission test.
