# Experience implementation — 14 September 2026

## Status

Implemented and inspected locally in `codex/studio-attachment-ux`, on top of the existing uncommitted security/persistence candidate. Nothing committed, pushed or deployed. No real posts, provider grants, review submissions or customer charges. The detailed continuing brief is `ZOVA_EXPERIENCE_IMPLEMENTATION_PROMPT.md`.

## Changes

- Persistent Studio canvas separates the current versions from conversation. Edit, Preview and Compare use actual text and media. Desktop gives the document the former analytics space; analytics remains available through navigation and an explicit link.
- Mobile Conversation / Draft / Preview modes remove the composer from the editing surface. Optional media/source/format controls reduce composer density. Editing text is larger and normal weight; buttons and focus styles follow the ink/purple identity.
- Three bounded text snapshots support Undo text edit, including persistence through reload. Undo does not roll back media, source or publication. Server sanitisation excludes arbitrary history fields and unknown platforms.
- Saved voice guidance/examples are visible in Studio with an Account correction route. Onboarding only claims a saved voice when one exists. Connection alone is not evidence of successful learning.
- Destination readiness shows account names, disconnected drafting and basic media requirements before publication. Permission checks still occur server-side. Customers explicitly choose ready destinations; approval still uses the exact immutable server snapshot.
- Settings, confirmation and results live in the canvas. Tabs use individual results rather than labelling every version published. Unsubmitted versions can be copied to a separate editable idea after a partial destination selection; submitted versions are excluded from that copy.
- Save failure exposes retry, local JSON download and a side-by-side saved/current comparison. Reload is explicitly labelled as discarding this tab's changes. Late review/results responses are guarded by draft identity/review epoch. Failed new generation removes the old draft card and retains input.
- Landing signup CTAs are honest; an editorial example demonstrates four expressions of one idea. Unsupported continuous-learning claims are replaced with editable saved guidance. Caption/media requirements and the testing offer are explicit. Onboarding has a direct first-draft route without mandatory voice setup.

## Evidence

Automated: **76 passed, 17 deprecation warnings**, `docs/validation/tests.txt` and `tests.xml`. Four added tests cover owner-scoped/escaped connection context, bounded history sanitisation, history persistence/ownership, and truthful onboarding voice state. Existing account, recovery, upload, request protection, concurrency, schedule, partial publication and immutable-approval tests remain passing. JavaScript syntax checks pass for all four Studio modules. No dependency changes in this increment; the preceding dependency audit remains the latest audit.

Browser: localhost, temporary SQLite/uploads, synthetic account, deterministic generation and publisher mocks; external HTTP blocked by the harness. Inspected desktop at 1280×720 and mobile at 390×844. Observed creation, direct text edit, actual-variant comparison, undo, reload restoration, exact account/text review, explicit X-only choice, mocked X publication, Instagram marked Not submitted, and continuation of Instagram as an editable separate idea. Mobile DOM width matched 390px, with no horizontal overflow; the composer was absent from the Draft view. Tab moved focus between view controls. This is not a full screen-reader or physical-device certification.

Two browser tabs reproduced an optimistic-save conflict: the first saved “Saved from the first tab.”; the second retained “Keep this conflicting local wording.” The comparison showed both without overwriting either. Simulated generation failure retained the input and left zero obsolete draft cards. Browser checks found and led to fixes for inherited composer margins, heavy textarea weight, incorrect all-platform publication labels and navigation blocked by the busy guard.

## Remaining gaps and limits

- Real model output quality, voice recognition and meaningful adaptation explanations still need evaluation on creator examples. Previews show content and format notes; they are not pixel-exact network renderers or evidence that Zova inspected media.
- Saved voice provenance is not tracked per observation. The interface presents saved guidance honestly rather than inventing an inferred/user-authored history. Inline individual-rule editing, passage-level instructions and richer revision comparison remain follow-ups.
- Signup is now labelled accurately and optional setup is shorter. Capturing an idea before signup and safely carrying it through authentication is not implemented.
- Readiness reflects connections at page load; final review rechecks current server/provider state. Additional early per-format constraints can improve this further.
- Text undo has three snapshots, not a complete version archive. It does not merge conflicts or restore attachment changes. Recovery download is a JSON safety copy, not an automatic import workflow.
- Returning-work discovery is a saved-ideas drawer plus draft search. A prioritised attention queue and personalised next action remain to be designed around real state.
- Provider/staging validation, PostgreSQL concurrency/restore drills, recovery-mail delivery, operational monitoring and the other external gates in the technical audit remain outstanding.
- Target-creator usability and comparative studies have not occurred. Industry-leading status is not established.

## Provisional expert re-score

These assess the inspected local candidate, not production or measured customer satisfaction. The original detailed review remains the baseline.

| Area | Review baseline | Local candidate | Basis / limit |
|---|---:|---:|---|
| Visual identity continuity | 7 | 7 | Z mark and palette retained; less working-product decoration |
| Brand promise in behaviour | 4 | 5 | Honest claims and visible guidance; voice quality unvalidated |
| First value / customer journey | 5 | 6 | Clear CTA and direct drafting route; pre-signup idea carryover absent |
| Navigation / task clarity | 6 | 7 | Stable idea canvas and dedicated work modes |
| Studio editing | 6 | 7 | Persistent versions, comparison and saved undo; deeper editing work remains |
| Review / publishing | 6 | 7 | Account-specific review and accurate results; live-provider gates remain |
| Mobile interaction | 5 | 7 | Focused modes and observed 390px layout; physical-device study pending |
| Distinctiveness | 4 | 5 | More purposeful workflow; customer preference is unproven |

No score reaches 8 solely because an implementation exists. Unchanged security, analytics and operations scores remain in the technical audit follow-up.

## Rollback

This increment introduces no database table or migration. `workspace_json.text_history` is additive and older code ignores it. Deploy nothing until the combined candidate passes staging gates. Revert an eventual experience-only commit as a unit, retaining the earlier security/persistence/publication candidate. Because the current tree was already dirty before this work, **do not use `git reset --hard`, restore the entire branch to main, or deploy the aggregate diff without review**.

For selective rollback before commits: remove the experience script/style includes and restore the previous Studio template/state/publish DOM placement together; revert only the Studio context addition in `app.py`, the text-history additions in `workspace.py`, and the landing/onboarding/Account copy changes. Preserve all existing authentication, upload, CAS and immutable-review code. Re-run the technical suite and create/edit/reload/review smoke checks. Do not roll back PostgreSQL or delete uploads to undo a presentation change. First separate and commit the existing technical candidate and this experience increment through selective review so each has a reliable release/revert boundary.
