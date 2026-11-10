# Compact Campaign controls — 10 November 2026

Owner follow-up to released build 23: remove excessive spacing above campaign posts, use black menus with white text and a black overall Campaign background. This is a presentation change; no billing, API, data model, scheduling, approval or ownership change.

Native review moves out of separate Form sections into a scrolling post list. One compact panel contains All campaigns, Improve and the actions menu, then Previews/Calendar and sorting. Keep 44-point controls and allow larger text to reflow. Creation retains its form and autosave. Post editing, persisted proposals and all existing actions remain available. Campaign uses a black background, charcoal post cards, white menu text and existing platform colours; other product tabs retain their existing backgrounds.

Web mirrors the black palette and compact action/view/sort panel. Secondary actions open as a dropdown rather than pushing the posts down. Escape closes it and restores keyboard focus; clicking outside also dismisses it. Saved-campaign selection remains directly available.

Validation in progress: local phone-width visual review; existing campaign journey regression plus compact-height, black-background and dropdown keyboard checks; native normal/large-text navigation and visual evidence; required full application/PostgreSQL/native CI. Record final outcomes here before handover. No production deployment or new TestFlight build is claimed for this candidate. The 79-section commercial register remains unchanged.
