# Zova commercial release assessment — 19 October 2026

## Decision

**Continue the limited beta. Do not launch paid access or migrate live customer data yet.** The product has useful creation and publishing foundations, a recognisable identity and extensive synthetic tests. Commercial readiness is held back by incomplete operating evidence, provider/device coverage, privacy lifecycle work and an unfinished paid offer. A polished screen cannot compensate for those gaps.

This assessment concerns the active `codex/ios-beta-20261019` application, starting at `db7fc42` / live runtime `419d452`. Historical claims in other worktrees are not treated as deployed features. The full 79-section register remains intact. These are one reviewer's evidence-based judgements across the requested disciplines, not independent expert certifications or customer research.

## Scoring method

0–2: absent/unsafe; 3–4: major gaps; 5–6: usable beta with material limits; 7: strong implementation with incomplete acceptance; 8: release-quality implementation and representative acceptance evidence; 9–10: sustained customer/operational proof and independently validated excellence. Half points indicate partial progress. Equal-weight averages aid prioritisation only. Privacy, security, money, data-loss and publishing blockers override the average.

| Area | Before | Reviewed candidate | What changed / why the ceiling remains |
|---|---:|---:|---|
| Simplicity and navigation | 6.5 | 7.5 | Removed repeated headings/copy in Account, Drafts and Performance; actual results appear much earlier on a phone. Test first-use comprehension with new creators. |
| Visual clarity and Zova brand | 7 | 7.5 | Light core screens, dark Account/bridges and violet accents retained. Larger metrics, clear platform marks, no meaningless comparison bars. Full zoom/Dynamic Type/VoiceOver audit still needed. |
| Studio creation and editing | 7 | 7 | Existing blank workspace, Next move, editable captions, sent attachments and explicit final review retained. Existing state/error regressions pass; real-model quality and all device flows are not newly proved. |
| First use and guidance | 6 | 6.5 | Help now points to the real controls; Account labels describe their actual destination. New-user completion/time-to-first-useful-draft study remains. |
| Retention and return value | 5 | 5 | Strategy, saved drafts and scheduling exist. No eligible cohort evidence here establishes repeat use or willingness to pay. Adding nudges without measuring value would not earn a higher score. |
| Publishing and provider coverage | 7 | 7 | Existing reviewed snapshots, ownership, durable results and no uncertain resend preserved. Historical successful tests cover limited formats/accounts, not all customer permissions or all iOS paths. |
| Performance and recommendations | 5 | 7.5 | Correct 7/30-day questions; missing metrics stay missing; failed refresh clears old results; late answers cannot replace a newer window; no fabricated cross-platform winner. Limited samples remain explicitly labelled. |
| iOS delivery and accessibility | 5.5 | 6 | Native9 now verified Testing in the existing one-tester group; testing notes saved. Real iPhone social-return, VoiceOver and Dynamic Type acceptance remain pending. This increases delivery confidence, not provider acceptance. |
| Security and account isolation | 5 | 5.5 | Safer provider errors, redacted review URLs and safe correlated request failures. Existing ownership/revocation tests remain. Broad service/RLS migration, staff MFA and independent security testing are unfinished. |
| Privacy and data lifecycle | 4 | 5.5 | Explicit versioned AI permission before content processing, revocable in Account and included in export/erasure. Retention, provider/media/backup deletion evidence and operator decisions remain incomplete. |
| Reliability and operations | 4.5 | 5.5 | Request references and separate-worker readiness/heartbeat controls implemented. Real alert delivery, production-like restore and incident rehearsal still needed. |
| Commercial offer and payments | 4.5 | 4.5 | Free-beta/no-charge messaging remains honest. Paid activation, iOS purchase policy, final offer, support commitments and real settlement/refund evidence are not approved/complete. |
| Code quality and scalability | 6 | 6.5 | Bounded modules and regression coverage; configurable database pools, separate scheduler and explicit schema preparation. No broad unfinished worktree merge. Load evidence, CSS debt and service/grant separation remain. |
| **Equal-weight average** | **5.6** | **6.3** | **Not a launch pass. Scores describe the reviewed candidate, not an assertion that it is deployed.** |

## Customer journey review

| Journey | Current strength | Remaining friction / next acceptance test |
|---|---|---|
| Discover → signup | Clear AI social-manager proposition; no-charge beta visible | Ask five target creators to explain the offer and limitations without assistance. Validate form errors, verification delivery and abandoned signup recovery. |
| Signup → first useful post | Can draft without connecting every provider | Measure useful output, not generation count. Target: a new creator produces and edits one useful caption in under three minutes, with no moderator rescue. |
| Studio → Next move → draft | Recommendations stay in their own compact surface; one idea at a time | Actual model/search relevance, source freshness, strategy fit and turning feedback into a better draft need a fixed evaluation set. No invented trend claims. |
| Draft → review → publish | Explicit destination/content/settings review; approvals bound to reviewed payload | Verify every supported format with authorised test accounts. Test expired grants, partial results, process death after provider acceptance and failed-platform-only retries. Never resend an unknown result. |
| Return tomorrow → next action | Saved workspace and Drafts/scheduling exist | Establish a measured habit: creator returns, finds their work and makes the next useful post. D7 return metrics already have definitions; no cohort results were invented or tracking switched on here. |
| Phone → social login → app | Working Instagram connection owner-confirmed on earlier build; native9 adds automatic return | TestFlight9 delivery is now verified. Test four providers, cancellation, interrupted login and a changed account on a real iPhone. Browser simulation is insufficient. |
| Account → help/privacy/delete | Flat expandable categories, current help, clear AI controls | In-app deletion initiation exists; fulfilment across providers/media/backups still needs verified records and an approved retention policy. |

## Implement → review → improve record

1. **Reproduced from source/live screens:** 30-day Performance questions still used seven days; old charts/answers could remain after a failed or late request; fallback answers inferred a platform leader from incomplete data. Help referred to controls that had moved. Account/Performance/Drafts repeated headings and explanations. AI content was sent without a separate explicit sharing choice.
2. **First implementation:** corrected Performance windows and fallback semantics; guarded stale requests; added account-bound AI permission; simplified copy/help; redacted provider exceptions and added server-generated request references. Prepared a separate publishing worker without activating it.
3. **Visual re-review:** phone Performance still had excessive space, tiny metric labels and bars implying comparability. Removed the redundant management button/aggregate card decoration and bars, enlarged metrics, and showed one clear unavailable state per account. A dark Account consent dialog had poor contrast; corrected theme inheritance and versioned its asset. This was discovered by rendering, not a source-only assertion.
4. **Interaction re-review:** cancel retains the question; explicit permission is saved before the original request; simultaneous AI requests share one permission prompt; failed permission save sends nothing; Account can revoke the choice. Backend enforcement is independent of the browser. Desktop and 393px synthetic phone views checked. Previews used disposable accounts and synthetic responses; no real AI or provider operation was performed.
5. **Saved-work re-review:** opening a previously created Next move or recurring draft now navigates directly to that saved draft, without an AI generation request or a new sharing prompt. Current work must save first; failed saves and switched workspaces still prevent navigation. Server-side draft ownership checks remain unchanged.
6. **Recovery re-review:** added a dedicated disposable CI fixture before pg_dump, then verified restored password/credential usability, existing and revoked sessions, an unresolved publication, withdrawn AI permission and an uploaded file recovered from a checksum-checked backup. The fixture cannot target a remote database, connection override or arbitrary file. Receipt must pass; this does not prove managed-cloud recovery, key custody or RPO/RTO.
7. **Regression pass:** initial full local run found the expected stale scope manifest and two old wording assertions (533 passed, 3 failed, 2 skipped). Updated those assertions to the new user-visible behaviour; focused rerun passed 34, with one PostgreSQL-only skip. Candidate `7e6a7fe` passed hosted SQLite (541 passed, two PostgreSQL-only skips), PostgreSQL (542 passed, one skip), dependencies, synthetic restore, container build and exact scope. The final saved-draft refinement requires a new exact-candidate run; the final receipt is saved under `social-proof/commercial-validation-20261019.json` and in PR34 checks. No failed gate is waived.

## Commercial gates, in priority order

| Gate | Required outcome / evidence | Owner or dependency |
|---|---|---|
| G1 — Security boundary | Complete compatible least-privilege account/service routing, reconcile legacy publishing to immutable approvals/idempotency, staff access/MFA and support audit; independent abuse/ownership review | Engineering/security; reuse isolated earlier work selectively, never merge the broad migration wholesale |
| G2 — Data and recovery | Approved retention/deletion matrix; test deletion across database, media, provider grants and backup expiry; restore encrypted connection samples with the correct keys; recorded recovery/rollback rehearsal | Operator decisions + engineering; use isolated synthetic data first |
| G3 — Real product acceptance | Five creator usability sessions; iPhone9 acceptance, keyboard/VoiceOver/Dynamic Type, all supported formats and provider scopes/statuses | Owner/test users and authorised test accounts; Apple build9 group delivery is complete |
| G4 — Operations | Delivered and acknowledged test alerts for stale worker, overdue schedule, unknown result, repeated AI error and budget threshold; incident owner; demonstrated recovery target | Monitoring destination and operating owner; no external messages sent here |
| G5 — Paid offer | Confirm GBP plans/trial/limits; decide lawful App Store purchase route; test upgrades/downgrades, cancellation, webhook outage/replay, refunds and reconciliation before enabling charges | Product/operator + Apple/Stripe configuration; testing enforcement stays disabled |
| G6 — Cloud | Credit eligibility confirmed, written award/expiry, approved post-credit estimate, staging restore/canary/rollback and one active publishing worker | Business facts + chosen provider account; see migration plan |

Recommended internal acceptance targets: no unresolved critical/high security or data-loss finding, no reproducible unapproved/duplicate publication, all six gates evidenced, and at least 8/10 in every release-critical dimension. Targets are proposed product standards, not industry statistics. Do not inflate scores merely to reach them.

## Implementation, test, provider and deployment status

- **Implementation:** this branch contains the increment described above. Two additive tables hold AI choices and worker heartbeat. Existing users, password/session/credential keys, uploads and social grants are preserved. No new real posts, plan charges or grant changes.
- **Tests:** local synthetic regression and browser evidence; required SQLite/PostgreSQL, restore, container and dependency checks must pass for the exact candidate. `tests/conftest.py` explicitly bypasses permission for pre-existing synthetic AI fixtures; the separate privacy suite exercises the production-default gate. Do not count bypassed fixtures as consent tests.
- **Provider validation:** no new live provider publishing test. Instagram owner-confirmed connection and earlier X/Facebook text/TikTok test evidence remain narrow evidence. User reports TikTok Direct Post approval; current production mode, public paid-content access and all-format acceptance must be verified separately before advertising full coverage.
- **Native:** no Swift changes in this increment. Build9 was verified Testing in the existing Zova Social Internal Beta group with one tester at21:41BST. Notes saved; no new app/signing rights/tester. Owner phone acceptance remains separate.
- **Deployment:** see the latest handoff/validation receipt. A candidate or CI pass is not evidence of deployment. Render remains the live host; charges remain disabled. External-worker mode, private-storage migration and cloud resources are not activated.

## Benchmark basis

Use concrete behaviour as the benchmark: compose/edit in context, move an idea into a saved draft with few steps, maintain mobile continuity and show truthful publish status. Buffer documents AI inside composition and an ideas workflow; Hootsuite documents mobile drafting and scheduling. These are primary-source feature comparisons, not a hands-on performance ranking: [Buffer AI](https://support.buffer.com/en-us/articles/using-buffers-ai-assistant-qbBulfw9sn), [Buffer ideas](https://support.buffer.com/en-us/articles/creating-ideas-in-buffer-7gu7n0Hyyq), [Hootsuite mobile publishing](https://help.hootsuite.com/s/article/publish-schedule-mobile).

Apple's privacy rules require explicit permission for sharing personal data with third-party AI, and apps supporting account creation must offer account deletion initiation. Implemented controls still need real-device/App Review acceptance; this is not legal certification. [Apple review guidelines, 5.1.1 and 5.1.2](https://developer.apple.com/app-store/review/guidelines/).

## Next iteration brief

Continue this exact application and preserve the full register. Reproduce the selected gate against the current runtime; implement a bounded fix; test failure, ownership, replay and interrupted flows; visually inspect desktop/phone; update the evidence and score only where earned. Start with G1/G2, then close G3/G4 using real acceptance evidence. Do not rebuild, enable charges, replace grants, restore stale customer data or activate unfinished RLS. Do not use a successful mock, upload receipt or attractive screenshot as a substitute for operational/provider proof.

## Rollback

Keep database contents, encrypted connections, media, publication ledgers and the new additive tables. Prefer a forward repair or revert only the affected presentation layer. Returning to the earlier runtime removes AI consent enforcement: **before a full rollback, pause new AI processing at the gateway/provider configuration or retain the consent gate**; a withdrawn privacy choice must not be bypassed. Disable scheduling before moving worker ownership, and never run old and new dispatchers concurrently. Inspect uncertain provider outcomes instead of replaying them. No production backup restore was performed in this increment.
