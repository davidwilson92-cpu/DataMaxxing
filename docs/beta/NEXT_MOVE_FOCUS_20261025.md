# Next Move: focused proposal and two-box strategy

Candidate prepared on 25 October 2026. **Not deployed.** The live server remains
d15f619; TestFlight 0.1.0 (11) remains the published binary. This change affects
the shared web experience and backend, not native code or signing.

## Owner feedback addressed

- Every visible idea has the same structure: dark-purple post proposal, one
  draft/open button, a pale-purple **AI recommendation**, and **Your strategy**.
- Removed the long requirements/checklist, admin-review cards, “Details”,
  “Change this idea” and duplicate refresh control from the idea screen.
  Source evidence remains available in a compact disclosure when relevant.
- Recommendation copy is bounded to 32 words and titles to 14; generation asks
  for shorter, specific, plain-language copy. This is display brevity, not a
  guarantee that generated recommendations will be useful.
- Strategy has two boxes for both creation and editing: the business/audience
  description and optional content direction. Three suggestions append to the
  second box without replacing the user's writing. No advanced survey remains.
- AI proposes a compact plan for explicit saving. Both original inputs and the
  structured plan persist per user/brand; legacy content constraints are retained
  when opening existing plans. Changes invalidate old idea batches.
- Next idea shows the next item, then requests three new proposals after the
  third. The counter continues. There is no three-idea loop or artificial total.
  Existing rate/usage limits still apply; requests are made on demand, not in a
  background generation loop. Back navigation is within the current batch.
- Fresh generation excludes recent exact titles and administrative tasks, with
  one bounded repair attempt. Failure retains the current usable batch. Recent
  drafts/feedback still inform generation; semantic uniqueness is not guaranteed.
- An older saved draft no longer pins itself ahead of each fresh batch. Existing
  draft records and their open links are preserved.

## Review and evidence

Local browser fixtures exercise two-box setup, suggestions, saving, reload,
editing, 390px-wide phone layouts at 650/760px tall, fourth-idea generation and
one-click draft creation. Screenshots use synthetic content, not real AI quality
or real trend evidence:

- evidence/20261025/strategy-two-boxes.png
- evidence/20261025/next-move-focused-650.png
- evidence/20261025/next-move-focused-760.png
- evidence/20261025/next-move-fresh-batch.png

Client tests cover duplicate clicks, failed requests and stale view responses.
Backend tests cover both saved input fields, repeated fresh batches, preserved
drafts, duplicate rejection/repair and post-only repair. Existing mobile composer
layout tests remain in place. Final application/PostgreSQL validation passed for candidate
`d3bc09dec27039786c2291af86de8de5ffbdf52a`:

- [Application push checks](https://github.com/davidwilson92-cpu/DataMaxxing/actions/runs/40207508948)
  and [PR checks](https://github.com/davidwilson92-cpu/DataMaxxing/actions/runs/40207513086)
  both passed.
- 678 SQLite tests (two platform-specific skips); 679 PostgreSQL tests (one
  platform-specific skip); 29 client tests/groups plus Studio clarity tests.
- The new real-browser Next Move journey and existing mobile composer regression
  passed. Additional local checks covered 320/390/1440px widths and enlarged body
  text, including reachable strategy navigation and no horizontal overflow.
- Synthetic PostgreSQL restore, hosting-image smoke, exact-scope beta gate and
  package audits passed. Audits reported no known package vulnerabilities; this
  is not proof that the application has no security defects.
- No production acceptance or real recommendation-quality claim is implied.

## Comparison with current tools

Reviewed official documentation on 25 October 2026, not hands-on competitor
accounts:

- [Buffer AI Assistant](https://support.buffer.com/en-us/articles/using-buffers-ai-assistant-qbBulfw9sn)
  offers prompt-based creation, business/audience ideas and a try-another/use-it
  path. Zova now keeps that same short idea-to-draft path, with saved direction.
- [Later content ideas](https://help.later.com/hc/en-us/articles/14711113026327-Generate-Content-Ideas-with-AI)
  uses a brand description, content pillars and three-idea batches. Zova retains
  small batches but removes the stopping point and presents one focused idea.
- [Hootsuite Wisdom](https://help.hootsuite.com/s/article/get-started-owlygpt)
  combines brand context with social listening. Zova's sourced-topic disclosure
  helps transparency, but does not establish comparable breadth or intelligence.

The revised design is competitive on simplicity and visual consistency. It is
**not certified market-leading**: that requires real recommendation relevance,
time-to-useful-draft, repeat-use and customer feedback evidence. The next tester
check is whether a new user can save a strategy, find a useful fourth idea and
draft it without guidance, then return to edit their strategy successfully.

## Boundaries

No schema migration, native change, provider grant, real social post, customer
deletion, billing activation, paid monitor or hosting move. All 79 broader gaps
remain in the retained register. This does not resolve or re-score the full
tester workbook, certify all provider journeys or certify commercial readiness.
