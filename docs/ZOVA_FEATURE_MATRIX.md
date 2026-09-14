## Stripe integration candidate — 14 September 2026

Hosted Checkout, billing portal, verified subscription reconciliation, durable duplicate-event handling, test/live isolation and billing recovery UI are implemented on `codex/stripe-billing`. Local full suite: 88 passed. See [STRIPE_BILLING.md](STRIPE_BILLING.md) for the detailed matrix, configuration and rollback. Stripe sandbox validation, approved pricing/credentials and deployment are pending. Checkout remains off by default and subscription enforcement remains disabled.

# Zova feature matrix — 14 September 2026 local candidate

“Implemented” below describes this local candidate. Nothing has been deployed. Provider approval is never inferred from code or a mock.

| Capability | Implementation / compatible change | Evidence and remaining gate |
|---|---|---|
| Signup and login | Existing email/password flow; named country selector; non-secret signup fields survive errors in a short-lived encrypted cookie | Existing onboarding/login tests plus signup error test; production reviewer credentials untouched |
| Both Instagram routes | Direct Instagram and Facebook-linked Instagram routes retained | Existing route/state tests; direct review last recorded in progress; no new OAuth grant or live post |
| Password and sessions | Attached ORM writes, password version increment, individual logout revocation; eligible legacy sessions continue | Old password fails, new password works, logout replay fails, unaffected sessions continue |
| Recovery | Hashed single-use 15-minute links, authenticated TLS email, version-bound reset | Mock delivery/replay/expiry tests; SMTP/DNS/real inbox and timing assessment pending |
| Profile, preferences and billing persistence | Attached user changes and clearing guidance persist; learned voice text editable | Independent-session persistence tests; current subscription testing access retained |
| Voice learning | Existing social scan retained; profile/date visible and fields correctable | Template/account tests; real model quality and simultaneous scan/manual-edit conflicts need further evaluation |
| Generation and rewriting | Existing AI adapters retained; contextual planner with deterministic negation/creation safeguards | Intent tests and synthetic browser generation/failure; no claim of universal intent accuracy |
| Media/source grounding | Explicitly says media was not inspected and links not fetched for generation | Prompt and UI reviewed; actual vision/source fetching remains absent by design in this increment |
| Attachments | Decode/allowlist/size checks, safe suffixes, quotas, previews/removal, persisted owner references | Image/video/security tests; mobile upload/reload/removal and rejected-upload check; lifecycle/decoder isolation risks in operations document |
| Full Studio state | Conversation, variants, composer, selected platforms, media and source saved with revision checks | Reload and ownership tests; two-tab browser conflict retains local input; only one active draft editor |
| Draft library | Existing filters/open/delete plus text search and schedule management | Browser/page checks; delivery history is retained; deletion of unsubmitted reviews is tested |
| Review and confirmation | Server-owned expiring snapshot: exact account, final text/link, media and settings | Tamper, concurrent confirmation, exact-account and finalised-link tests; reviewer’s simple confirm path retained |
| X | Text, threads and up to four images retained; scope gate; videos remain unsupported | Mocked adapter/legacy compatibility tests; live X validation pending |
| Instagram | Single image or video; direct and Facebook-linked login preserved | Multi-image selection fails clearly instead of silently dropping files; live permissions/container behaviour pending |
| Facebook Pages | Text/link or one image; pinned Page and explicit publishing-scope requirement | Mocked partial/retry tests; `pages_manage_posts` approval/grant remains an external gate |
| TikTok | Existing photo/video adapters, reviewed privacy/interactions/disclosures, configured inbox/direct mode, pending-state polling | Mode/scope checks and server workflow; provider settings/live pending lifecycle need external validation |
| Publication results | Per-platform states/links; successful platforms cannot be retried; failed-only review/retry; unknown held for reconciliation | Partial results, definitive failure retry, duplicate-click and concurrency tests; no real posts |
| Scheduling | Exact reviewed account/content, timezone/DST validation, cancel/reschedule, atomic worker claim and interruption recovery | Concurrent-worker, cancelled-job, reschedule and DST tests; PostgreSQL contention and host worker monitoring pending |
| Time suggestions | Existing AI suggestions retained as optional starting points, clearly not performance-derived | API retained and UI connected; real-model usefulness not re-evaluated |
| Analytics and questions | Dated seven-day post cohort, explicit sample/lifetime definition, refreshed timestamp, null/partial metrics, honest sidebar | Window/missing-data tests and UI check; pagination/history and comparable per-platform metric definitions remain limited |
| Billing and offer | Existing integration retained; persistence fixed; checkout blocked while subscription enforcement is off | Mocked persistence and testing-checkout tests; no charge, live checkout or webhook certification |
| Privacy/deletion | Unlink clears credentials; signed callback records scope/status; unknown status code returns 404 | Record/expiry/security tests; account deletion remains assisted, not a demonstrated full erasure workflow |
| Mobile/navigation | Menu restores workspace links, sign-out/legal links; source/X format and Account remain reachable | 320/390/768/1280 responsive checks; physical keyboard/zoom/landscape/screen-reader testing pending |
| Accessibility | Associated labels, visible focus, real upload button, keyboard platform tabs, larger controls and reduced-motion support | Browser focus check and semantic inspection; not a WCAG conformance claim |
| Administration | Existing admin user listing and authorisation retained | Existing suite; no production admin data mutation or new operational audit trail |
| Operations | Authenticated operational counts, CI/dependency checks, additive migration and synthetic restore tests | Local evidence only; monitoring destinations and managed PostgreSQL/upload restore drill pending |

Team approvals, media editing, email marketing, native mobile apps and enterprise SSO are not newly assumed launch requirements, consistent with the original audit.


## Experience increment — 14 September 2026

| Capability | Local implementation | Evidence / limit |
|---|---|---|
| Persistent canvas | Edit, Preview, Compare separate from chat | Desktop/mobile browser inspection; approximate previews |
| Text undo | Three sanitised snapshots stored in owned workspace | Round-trip/bounds tests and browser undo; no media rollback |
| Voice visibility | Saved guidance and examples in Studio, correction link | Truthful-state regression test; provenance not inferred |
| Destination continuation | Explicit ready-target review, individual status, copy unsubmitted versions | Mocked X publication and editable Instagram continuation |
| Save conflict recovery | Retained input, download, saved/current comparison | Two-tab browser conflict; no automatic merge |
| First-draft journey | Honest signup CTA, editorial example, optional setup shortcut | Template/route checks; pre-signup idea capture absent |
| Focused mobile work | Conversation / Draft / Preview modes | 390px no overflow, composer hidden in editor, keyboard focus check |

Detailed implementation, limitations, provisional experience scores and rollback: `ZOVA_EXPERIENCE_IMPLEMENTATION.md`. Latest automated suite: 76 passed; no production deployment.
