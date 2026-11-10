# Campaign controls candidate — 10 November 2026

Scope: incremental changes on PR46's campaign workspace, with its pending PR45 dependency. This candidate is not deployed. Keep Render, customer charges disabled, and existing publishing approval and ownership boundaries.

## Product behaviour

- One compact Campaign actions menu: pause/resume, move remaining dates, add posts and reuse. Improve remaining posts has a direct button. Web and native iOS use the same endpoints and language.
- Pause stops unsent scheduled deliveries atomically. Resume retains drafts and requires fresh final approval. Unknown/in-progress delivery blocks campaign state/date changes. Published posts remain intact.
- Moving dates preserves relative local times through daylight-saving transitions and flags date-sensitive captions. Active scheduled posts become drafts; approval cannot silently follow a changed date.
- Reuse asks for a name and start time, creates a separate unpublished plan, keeps owned media, and flags old date wording. An idempotency key prevents duplicate copies after a lost response. Expanded/missing canonical posts fail explicitly rather than silently losing content.
- Improvements use the campaign brief, identity, saved strategy/voice, scoped current performance evidence and owned media observations. Repetition is checked against other retained campaign posts with one bounded retry. Missing evidence is described as an experiment, not a measured success.
- Proposals persist for review. Original captions can be expanded beside proposals. Only Apply changes replaces captions; existing media and platforms stay selected. Scheduled posts return to drafts. Extension previews up to ten additional posts, with a campaign cap of 26, before creating canonical drafts.
- Campaign, draft, series and schedule revisions protect concurrent changes. Consent and Premium eligibility are enforced server-side, including after generation. No social posts or real charges are initiated by this workflow.

## Simulated focus-group critique

These are structured persona reviews, not interviews, usability participants or market validation. No real group has been contacted.

| Perspective | Concern | Refinement |
| --- | --- | --- |
| Impatient gym owner | A row of controls competes with the posts. | Keep secondary controls in one menu and one direct improvement action. |
| Florist with a weekly offer | Duplicate could mean duplicate publishing; dates might remain stale. | Label Reuse campaign, request a new name/date, keep the source intact and flag relative-date captions. |
| Cautious low-AI-proficiency owner | AI may overwrite a caption already approved. | Persist a separate preview, show original captions, require Apply changes and reject stale revisions. |
| Bakery owner between customers | Pausing first just to preview AI changes adds steps. | Preview scheduled captions directly; explain that applying them returns those posts to drafts. |
| Content creator | Rewrites may change selected videos invisibly. | Caption improvements retain media; previews show attachments. |
| Social media specialist | New follow-ups may repeat published hooks or invent performance proof. | Compare proposed captions against retained posts, limit one rewrite retry, disclose absent measurements. |
| Accessibility review | Dense horizontal controls and hidden consequences are hard on small screens. | Wrap web controls, native ViewThatFits, inline labelled forms and explicit scheduled-post consequence at review. |

Second review: primary journeys are aligned across platforms and proposals are reversible until applied. Reuse deliberately refuses multi-platform/thread-expanded posts rather than flattening them. Live provider results, subjective model quality and real owner willingness to pay still require observation; simulated personas cannot establish them.

## Verification record

Validation is in progress; final results will be added before handoff. Coverage includes isolated database tests for revision conflicts, workspace/account boundaries, Premium/consent, lost-response reuse, scheduled state changes, unknown outcomes, rollback, daylight saving, extension and proposal failures. Browser journeys use synthetic owners and AI output on phone and desktop. Native UI coverage exercises pause and original/proposal review; existing native suites retain other journeys.

Not exhaustive: all possible network/provider/iCloud/device combinations cannot be exercised. Actual iPhone picker behaviour, production provider publishing, live AI quality and real customer feedback are separate acceptance checks. The existing 79-section commercial register is retained without claiming closure.
