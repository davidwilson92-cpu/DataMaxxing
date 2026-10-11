# Next move design review — 11 October 2026

The owner screenshot showed a generic lavender panel, an expanded wall of text, duplicate approval copy and an optional feedback form that interrupted idea selection.

The implementation uses the existing Zova Z as a translucent background on an ink/plum card, strong white headlines, a clear purple Draft/Open action and an adjacent Skip. Context sits outside the card. Refresh is a labelled header icon; sources and settings remain available. No reason is requested. Skip records dismissal and reveals the next idea; after exhaustion it requests another batch. Failed feedback preserves the visible card. Saved-source text no longer implies a linked draft is blocked from opening.

Review iterations: first desktop review found a legacy flex rule interfering with the card layout; corrected it. Darkened the primary button for contrast. Reviewed desktop, 390x844 mobile, 320x640 mobile and expanded context. Keyboard Skip revealed the next saved recommendation; Draft post opened a generated synthetic draft and reload retained it. Reopening showed Open draft. No browser console errors observed. Mock providers, disposable local database, no real social publication.

Node onboarding and journey checks passed, including questionnaire absence, Skip advance, exhausted-list generation and failed-feedback preservation. Required hosted validation run38174288031 is queued before any jobs have started. PR21 is open, not merged or deployed. Do not bypass required checks. Runtime candidate15bd98e. Rollback to4d86fe7 preserves database/drafts; no schema migration. Broader beta/security gaps remain open.

Full local suite: 271 passed, one skipped. Existing dependency deprecation warnings remain.
