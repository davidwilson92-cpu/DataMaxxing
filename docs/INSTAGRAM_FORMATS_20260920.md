# Instagram Post and Story

Small additive Studio change based on live main 504b617. No database migration, grant changes or production deployment in this task.

- Instagram selection reveals a labelled Post/Story dropdown beside X format. Deselecting Instagram hides it; new chats and old drafts default to Post. Workspace autosave/reload retains the choice.
- Post retains image-to-feed and video-to-Reel/shared-to-feed behavior. Preview and confirmation describe the actual destination format.
- Story sends one image/video using media_type=STORIES through the existing direct-Instagram or Facebook-linked adapter. Current Business eligibility is checked before review and again before creation. Unknown/unavailable eligibility fails closed. Neither login route nor its permissions changes.
- Stories publish the uploaded visual only. Draft text is explicitly planning copy, not an automatically rendered overlay or caption. Source links, stickers and music are not added. Generation/rewrite instructions reflect this. Final confirmation shows the visual and explains omitted text.
- Saved format must match review options. Changing either the saved format or confirmation payload rejects approval. Scheduled jobs carry the immutable Story option. A Story counts as one publication; existing duplicate prevention remains.
- JPEG and MP4/MOV are accepted for the Story review. Provider media size/duration/aspect/codec restrictions still apply; no transcoding, cropping or overlay editor was added. One Story per draft, not a multi-frame series or simultaneous feed-and-Story publication.

Validation: 138 tests passed, including 13 focused format tests; four changed JavaScript files pass syntax checks. Isolated mocked tests cover adapters for image/video on both login routes, account eligibility, legacy Post default, save/reload, review tampering, changed saved format, scheduling, one-unit allowance and duplicate prevention. Browser checks used synthetic local data: conditional control, connection prompt, persisted Story after reload, keyboard Home/Tab, 390x844 mobile with no horizontal overflow. No real provider upload or publication performed; a controlled Business-account Story acceptance test remains an external gate.

Meta reference: https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api (Business-only Stories restriction). Developer content-publishing pages were inaccessible to the documentation fetch tool. Live provider validation must confirm account/API-specific behavior and media constraints; mocks do not establish provider acceptance.

Rollback: retain saved instagram_format and immutable Story job/review payloads. Do not run the preceding adapter while Story jobs are queued: it would interpret video as Reel/image as feed. Pause/cancel affected jobs with the supported workflow, or forward-fix while retaining format-aware dispatch. No data restore is needed.
