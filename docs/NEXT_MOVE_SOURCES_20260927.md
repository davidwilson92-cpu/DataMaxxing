# Next move placement and sourced recommendations — 27 September 2026

Status: implemented and tested locally; NOT deployed. Branch `codex/next-move-sources` starts at 653528a, whose tree matches production merge 021aad7. The previous strategy release is live; this increment is separate.

## Changes and aesthetic review

- Moved the single Next move launcher from the composer to the top-right header, next to New chat. Retained Zova's purple sparkle, translucent Z, black navigation rail and quiet chat layout.
- Refined its purple pill, focus outline, panel header, import control and secondary actions. Dated source evidence expands inside a card rather than making the initial view dense.
- Mobile keeps navigation, logo, New chat and Next move on the first line and the brand switcher on the second. At 390x844 the conversation is 572px high; at 320x640 it is 368px high. Both document widths equal their viewports; the 44px launcher stays inside the right edge.
- Review verdict: clearer separation between planning and composing, consistent branding, sources discoverable without overwhelming the chat. Source/strategy/recurrence detail still requires scrolling; this is deliberate progressive disclosure, not an all-in-one dashboard.

## Discovery and strategy logic

`nova/trends.py` makes two bounded Responses API web-search requests: general web and public-social-domain search, concurrently. Each requires a completed search tool call, requests source provenance, uses external web access and permits at most two tool calls. Requests use the existing model and API key, store=false and 35-second HTTP timeout. No new dependencies, credentials or platform scopes.

Only public content themes go to the search requests. The UI labels that field and explains the disclosure; full strategy, drafts, account IDs and social tokens do not enter search requests. The subsequent existing AI recommendation request receives confirmed strategy, recent work/feedback and accepted evidence. It ranks goal/audience/resources/exclusions ahead of novelty, explains fit, and uses explicit source IDs for current-topic actions. Proposal guidance asks for industry-specific public themes.

Sources must be HTTPS public hostnames, occur in actual tool sources/citations, and carry a reported publication date within the past 14 days. No undated/future sources accepted. Social-source cards require a public social hostname. Source checks expire at 24 hours and block NEW drafting until refreshed; already-created drafts remain accessible. Sources and strategy context carry through into draft instructions.

Search failure, missing configuration or no recent evidence produces explicitly labelled evergreen suggestions. An invalid source ID rejects the generated batch without replacing saved actions. Stable action keys exclude check timestamps, preserving deduplication/feedback. No schema changes: evidence is in existing action JSON and included in the existing export/erasure path.

## Validation

- Full isolated SQLite suite: **224 passed**, 17 existing deprecation warnings, 60.06s.
- Final focused run after adding outage/social-domain tests and sharpening proposal guidance: **43 passed**, 2 existing warnings. This includes two additional tests beyond the full run.
- JavaScript syntax and Git whitespace checks pass.
- Browser: disposable local account and mocked AI/search, 1280x720 desktop, 390x844 and 320x640 mobile; no overflow. Proposal -> confirm -> source card -> generated linked draft -> reload verified. Source expansion, Escape dismissal and focus return passed. No console errors observed. Mobile viewport override reset.
- Screenshots: `validation/next-move-desktop.png`, `validation/next-move-mobile.png`.

## Explicit validation limits / release gates

- No usable local OpenAI key exists. Real provider/model acceptance, latency, search billing and recommendation quality remain UNVALIDATED. No live searches, social publishing or production mutations performed. Use synthetic public themes with the existing staging provider before release.
- Public indexed social search is NOT a private feed, full social API stream, engagement metric or proof of platform-wide popularity. Source publication dates are extracted by the model and labelled reported; links/provenance are validated, factual claims/dates still need human checking.
- No fresh PostgreSQL/CI/deployment run for this increment. The previous release's green CI is historical evidence only.
- Search usage is bounded and token calls recorded; existing token-only cost estimates do not include web-search tool fees. Validate actual invoices before making a margin claim.
- Existing broad/ambiguous themes should be edited to identify the industry/topic. Avoid confidential information in public themes.

## Rollback

Revert this increment to 653528a / production-equivalent 021aad7 code. There are no migrations or destructive data operations. Retain strategy/action JSON, drafts, uploads, authentication and connections. Old code ignores added evidence fields. No recurring schedule or publication approval behavior was changed. Do not restore production data to roll back this UI/search change.
