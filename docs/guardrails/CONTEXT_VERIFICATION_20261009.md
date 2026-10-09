# Database access-control function verification

Candidate only. Validated at 18d1fa7: local/CI SQLite 415 passed / 41 expected
skips; PostgreSQL 455 passed / one expected skip. CI run 37999971907 also passed
migrated RLS restore, image build/smoke and dependency audit. Evidence:
`evidence/context-verification-20261009.json`.
No live deployment, database role, credential, policy or provider was changed.

Before this increment, staged service construction checked function ownership
and execution grants but accepted an altered function body under the same
signature. That leaves a gap between the checked privileges and the authority
checks actually executed by PostgreSQL.

Offline installation and startup verification now share one source for the two
context functions. Read-only startup compares catalog bodies, parameter names,
defaults, return types, languages, security-definer mode, search path, volatility,
parallel safety, null handling, leakproof flag and absence of a support function.
The issuer's allowed runtime identities are part of the verified definition.
The check rejects missing or changed definitions without executing or repairing
them and does not trust a digest stored alongside the installed code. Existing
ownership and execution-grant checks remain required. Only common indentation
and outer whitespace are normalized; SQL text is not loosely rewritten.

Synthetic PostgreSQL regressions change membership validation, backend replay
binding, execution mode, search path, volatility, leakproof/null handling,
defaults and issuer audience. They demonstrate that the previous grant-only
checks accept those changes, then require the new check to refuse startup and
allow startup only after an explicit fixture-admin repair. A missing issuer
function must also fail. The tests use isolated schemas and roles.

This is not a complete policy verifier: exact table-policy expressions, policy
role/operation sets, final content/worker column grants, account-level isolation
and service routing still need completion. This does not protect against a
database administrator changing functions after startup. Runtime integrity
monitoring and restricted migration administration remain operational work.
The staged service mode remains disabled for customers and has no production
activation switch.

Before activation, rollback is code-only. After activation, do not bypass a
definition mismatch: pause affected services, investigate drift and use the
reviewed offline migration while writes are paused. Preserve customer records,
security versions, pending/unknown publication states and existing credentials.
