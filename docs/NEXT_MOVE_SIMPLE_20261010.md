# Next move simplification

Problem reproduced on live beta: a saved strategy with no recommendations showed an empty panel and several overlapping explanations. Opening now re-reads the saved strategy, loads existing actions, and generates recommendations once when none are available or every undrafted idea is stale. Existing usable ideas do not trigger another AI request. A failed request leaves a visible retry button.

One post recommendation leads the view, with a full-width Draft post button. Other ideas, reasons, evidence, feedback and settings remain accessible through disclosure controls. The plan form keeps the goal and platforms up front; audience, voice, resources and import are optional details. Source disclosure and explicit strategy confirmation are retained. Manual review actions remain distinct from post creation.

Drafting saves the current workspace first, stops on save failure, reuses linked drafts and preserves explicit platform/format and draft title. A changed workspace epoch suppresses late navigation. Clear busy state before navigation to avoid triggering the unsaved-work warning. Nothing publishes or schedules without the existing separate approval flow.

Review iterations: first pass still had an oversized modal; combined the secondary settings and feedback to reduce visible rows. Real browser testing then caught a busy-state navigation regression; corrected it and added a regression. Desktop and 390x844 local preview showed an unclipped primary action; keyboard Enter created/opened the post, and reload retained title/content/Instagram-only selection. Synthetic provider fixtures do not establish live model quality.

Validation: focused strategy tests and Node onboarding/journey/schedule/Studio harnesses passed. Full local Python suite passed 265 with one skip before the final small client fix; final candidate receives CI application/PostgreSQL/restore/image/dependency and scoped beta checks. Record CI/deployment result in the handoff after completion.

Rollback: redeploy beta 4c0b041 without reverting data. This change has no schema migration. Keep newly created drafts; never resend uncertain publications. Known commercial/security gaps remain in docs/beta/KNOWN_GAPS.md and deferred-register.json.

PR19 deployed as ebb6f48 (Render dep-db585qmk1f9s73e55l9g) at 18:25:42 UTC. CI38075491135 passed 265/one skip on each database. Assets/health/login/signup verified. Live generation exposed a rejected model response despite mocked journey passing. Follow-up adds precise schema constraints and one validated repair; it does not discard source/format restrictions or invent fallback recommendations.

Final verification: PR20 live as4d86fe7 at18:31:51UTC, deployment dep-db588kn40ujc73c8cp90. CI38075939402 passed271/one skip on each database, plus required scoped checks. A real provider recommendation generated successfully; its Draft post opened an actual saved Instagram draft in Studio, survived reload, and became Open draft when revisited. No real publication. See sanitised validation JSON.
