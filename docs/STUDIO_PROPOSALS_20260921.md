# Studio proposals and proportions - 21 September 2026

Candidate on codex/studio-proposal-layout, based on production 78d9924. Not deployed.

## Changes
- Planner defaults to the selected destination, offers one concrete proposal, distinguishes follower opinions from measured analytics and resolves short drafting acceptance from prior user context. Creation and rewrite carry a self-contained brief. Vague acceptance never directly publishes.
- Default gpt-5-mini uses low reasoning effort; planner output budget increased from 700 to 3000. Explicit output-budget exhaustion gets one bounded retry, with both calls recorded. Other provider failures remain errors. Partial JSON is never treated as completed output. Overlong editorial replies are bounded before validation.
- One error per failed request. Prior draft is retained until new generation succeeds; retry input and conversation are saved. Save recovery appears only when saving actually fails.
- Brand switch moved into header; horizontal compact attachment cards; bounded textarea; destination and action controls share desktop row. Short screens cap composer height, retaining a scrollable conversation. Platform controls, conditional X format, post options, approval, watermark and history remain.

## Evidence
- Full local suite before final hardening: 147 passed. Final run recorded in handoff/PR.
- Added regression checks for short acceptance, selected-platform context, verbose replies, incomplete-response retry limits, partial output rejection and model-specific reasoning parameters.
- Isolated SQLite preview, mocked providers: Why not? produced an updated editable version; forced generation failure left the old draft and URL intact, retained text, displayed one error, and subsequently saved automatically. Reload preserved input/conversation and a real uploaded synthetic PNG. Attachment removal and keyboard traversal from remove to composer checked.
- Measured 1040x580: conversation 268.5px, composer area 247.5px including attachment/status. 390x844: conversation 437.1px, composer 342.9px with X format and attachment. Short 390x500: conversation 161px, composer capped at 275px; composer scrolls when needed. No horizontal document overflow. Visual inspections at these sizes.
- Real OpenAI requests through existing service credentials, synthetic text only, no database writes: initial full revised planner prompt produced editorial help but an oversized reply (would fail old validation); this drove reply-budget hardening. Follow-up focused concise-prompt check returned usable logo-feedback wording. Actual generator with candidate instruction/settings returned a complete Instagram caption. These are bounded smoke checks, not a model-quality guarantee or a full production browser end-to-end test. No real posts or social-provider actions performed.

## Limits and rollback
Attachments are still not visually inspected; the UI and prompts say so. AI can still fail or misinterpret requests, and one retry can increase latency/cost. No schema, data, auth, billing, provider-grant or production config changes. Revert this candidate commit or redeploy production 78d9924 to roll back. Production release and post-release verification remain separate.

OpenAI response-budget behavior checked against https://developers.openai.com/api/docs/guides/reasoning .
