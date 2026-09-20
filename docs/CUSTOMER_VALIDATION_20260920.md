# Supported beta study and cohort definitions

Status: ready to run; **zero participants recruited or tested by this task**. Synthetic accounts are not customers. Do not invent findings, retention or willingness to pay.

## Recruitment and consent

Recruit 5–8 people who regularly create content for a small business or personal brand. Include new social-tool users, an experienced scheduler user and a mobile-first creator. Recruit only through user-approved channels; no invitations were sent. Record participant codes, not customer content, in the report. Ask permission separately for recording/screenshots; participation and optional usefulness feedback are voluntary. Explain the purpose, what milestones are collected, access to results and the agreed deletion date. Confirm privacy basis/retention with the operator before enabling measurement.

## Session (30–40 minutes)

1. Ask the participant to explain what they believe Zova does and what it costs from the landing/signup experience. Do not teach them first.
2. Give a realistic brief: a local pottery studio opens Saturday, welcomes beginners and takes bookings on its website. Ask them to create X and Instagram versions using supplied synthetic details. Supply a synthetic photo description; do not imply Zova inspected the image.
3. Ask for a warmer revision that preserves the date and call to action. Ask which version sounds like their brand and why. Observe whether saved voice guidance is discoverable and correctable.
4. Reload the draft. Ask them to find it from the history/sidebar, inspect the selected platform and say whether it has been published.
5. Use mocked accounts to enter final review. Ask the participant to identify exact destination, final text/media and time. Do not publish a real post. Simulate one successful and one failed destination; ask what they would retry.
6. Ask them to find help, recover access, understand a seven-day trial and locate cancellation. Use test billing only, where configured.
7. Ask whether they would use this next week, what it replaces, what would stop them paying and how useful the draft was (1–5). Intent is not retention.

Do not coach until a task has been marked blocked; record coaching separately. Stop on distress or withdrawal. A moderator may recover the session without converting a failed task to unassisted success.

## Acceptance and report

Target at least 80% unassisted first-useful-draft completion: 4/5, 5/6, 6/7 or 7/8 participants. Separately require correct understanding of publication approval and destination; a success percentage must not excuse a wrong-account/accidental-publication risk. Report median and range of task time, blockers, voice ratings and critical misunderstandings. Small samples are directional, not statistical proof.

| Participant code | Device | First draft unassisted? | Seconds to useful draft | Voice 1–5 | Understood destination/approval? | Recovered after reload? | Help found? | Would return? | Observed blocker |
|---|---|---|---|---|---|---|---|---|---|
| Not collected | | | | | | | | | |

Run a follow-up after one week. Ask whether they returned and why; corroborate only where measurement is enabled and disclosed. Repeat-use intent, a signed-in visit and successfully publishing useful content are three different outcomes.

## Instrumentation

`PRODUCT_METRICS_ENABLED=false` by default. When enabled, server-owned milestones record signup, one Studio visit per UTC date, generation, saved workspace revision, connection, review and confirmed published results. A saved revision can be autosave; it is not proof of a meaningful edit. Pending/unknown outcomes are never published milestones. The optional **This draft is useful** action in Post options records explicit feedback after saving an owned draft. It is not inferred from generation.

No general client event-ingestion endpoint exists. Arbitrary client claims of publication are rejected. Events contain internal identifiers, kind and time; no prompt, caption, IP, email or token. Deduplication prevents repeated feedback/retries counting twice. Events are account-wide across brands; ownership still applies to feedback.

Authenticated `/internal/cohorts` reports signup-date cohorts, generated/useful/published counts and seconds to explicit usefulness. D7 return is a Studio visit 7–8 days after signup, with accounts younger than eight days excluded. UTC daily visit granularity limits precision around day boundaries; use weekly return/cohort trends, not precise session duration. Old accounts without an instrumented signup are excluded. A missing cohort is not zero retention. No historical backfill.

Before enabling: agree a retention period, assign an analyst, disclose collection, schedule deletion/export handling and test monitoring. The assisted lifecycle tool erases the account's product events. Current flags remain off outside the disposable preview/tests.
