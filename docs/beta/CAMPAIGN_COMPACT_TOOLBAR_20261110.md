# Compact Campaign controls — 10 November 2026

Owner follow-up to released build 23: remove excessive spacing above campaign posts, use black menus with white text. The owner subsequently clarified that the overall backdrop must be white, with a subtle purple fade on the black toolbar. This is a presentation change; no billing, API, data model, scheduling, approval or ownership change.

Native review moves out of separate Form sections into a scrolling post list. One compact panel contains All campaigns, Improve and the actions menu, then Previews/Calendar and sorting. Keep 44-point controls and allow larger text to reflow. Creation retains its form and autosave. Post editing, persisted proposals and all existing actions remain available. Campaign uses a white background and white post cards, with a black toolbar fading subtly into deep violet, white menu text and existing platform colours; other product tabs retain their existing backgrounds.

Web mirrors the white backdrop and black/violet toolbar and compact action/view/sort panel. Secondary actions open as a dropdown rather than pushing the posts down. Escape closes it and restores keyboard focus; clicking outside also dismisses it. Saved-campaign selection remains directly available.

Validation:

- Local UI inspection at 320px, 390px and 1366px: compact panel and black background initially, then corrected to the owner’s white backdrop and black/violet toolbar, readable platform headers/calendar marks, dropdown containment, sort/calendar switching and action cancellation. No horizontal overflow. Small-phone panel measured 133px; desktop measured 81px. Screenshots are in workspace `outputs/campaign-compact-toolbar`.
- 24 focused campaign-control tests passed. Initial application run 42809685913 and PR run 42809877372 passed 815 SQLite / 816 PostgreSQL tests, full browser journeys, recovery/audits and the exact-scope guard. Native-only refinements below require fresh exact-candidate checks.
- The first native simulator run exposed inherited accessibility identifiers on the new container, overriding individual button identifiers. Remove container/post identifiers rather than weakening test selectors. Its accessibility tree also showed text-only hit areas after removing Form; a scoped button style now preserves 44-point targets. Largest accessibility text gets a stacked first row. Superseded runs were cancelled after diagnosis.
- The white-background candidate passed normal native layout, calendar/sort/navigation and campaign actions. The largest-text return test initially scrolled away from the toolbar after cancelling an expanded form; its accessibility tree confirmed the control was above the viewport. The test now scrolls back up before selecting All campaigns; assertions remain intact.
- Screenshot review also found hyphenated view labels at the largest accessibility text size. Previews/Calendar now stack at accessibility sizes, retaining full-sized text and selected-state semantics; normal sizes keep the compact horizontal control.
- Final-candidate validation and screenshots are recorded with PR48 and workspace `outputs/campaign-compact-toolbar/validation.json`; this report does not substitute for those results. Earlier validation predates the owner’s white-background clarification.

No production deployment or new TestFlight build is claimed for this candidate. The 79-section commercial register remains unchanged.
