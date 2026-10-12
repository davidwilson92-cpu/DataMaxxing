# Studio design benchmark and iteration review — 12 October 2026

Scope: Studio and Next Move cosmetics/interaction hierarchy, against the six areas in the preceding critique. This is a heuristic design assessment, not customer research, independent certification or commercial/security readiness. Production remains1998cec until separately released. All79 commercial/security register entries retained.

## Benchmark principles

Official product references consulted12October2026:
- ChatGPT Canvas: https://openai.com/index/introducing-canvas/ — working content and direct refinement controls. Apply stronger draft hierarchy while preserving the owner's requested simple chat layout; do not add a split canvas.
- Claude Artifacts: https://claude.com/features/artifacts and https://www.anthropic.com/news/projects — make the output a usable working object. Apply an identifiable draft and its primary next action, not a visual imitation.
- Perplexity Spaces: https://www.perplexity.ai/enterprise/videos/how-to-use-create-spaces — organised threads and source context. Preserve account-owned history and inspectable recommendation evidence.
These are selected leading reference products, not an exhaustive market ranking or a hands-on comparative usability trial. Our recommendations are design inferences from their documented patterns.

## Recommendations fulfilled

1. Promote Review & publish to the first, filled primary draft action; preserve the exact confirmation handler and immutable-approval flow.
2. Group destination logos and conditional Post/Story in the same composer row; keep attachment/settings/send in one utility row. Hide redundant single-platform scope only; retain multi-platform and read-only explanations.
3. Show the large Z only on the welcome screen. Remove the duplicated desktop header mark where the navigation mark is already visible. Retain mobile branding and reduce card watermark prominence.
4. Use a shared24px geometry/1.75stroke SVG navigation family. Keep real platform marks separate and accessible names intact. Use downward chevrons for disclosure and right arrows for internal progression.
5. Tighten recommendation shell/card spacing; retain just Details and Change this idea. Increase supporting text to14–15px, maintain44px targets for primary controls.
6. Request plain-language one-sentence recommendation benefits without parenthetical strategy jargon. Non-destructively omit explicitly labelled legacy '(strategy:...)' parentheticals from displayed rationale; preserve stored text and source disclosures. This does not guarantee live-model copy quality.

## Review, revise, review

Pass1: hierarchy, grouping, typography, navigation and watermark changes. Mobile composer still too tall; inherited form-label margins added20px and the single-platform status duplicated visible destination state. Scores: brand8, consistency7.5, hierarchy8, simplicity7.5, typography8, polish7.5.
Pass2: remove label margins and redundant status; retain accessible scope when important. Detect and resolve inherited48px icon minimum width preventing compact grouping. At390x844, composer170px; conversation region approximately479px; no document horizontal overflow. Draft edit persisted after reload. Primary action operated with Enter and returned honest connection readiness rather than publishing.
Pass3:320x740 exposed header overlap. Replace New Chat text with a44px plus control only at that breakpoint; retain explicit accessible label/title. Recheck: no header overlap, no horizontal overflow. Composer220px with sensible wrapping, conversation325px independently scrollable. Narrow screens require scrolling for long content; no content removed.

## Final scores

Rubric:8 means a clear hierarchy, coherent colour/type/icon treatment, readable tested states, functional primary paths and no blocking layout problem in tested viewports;9–10 would require broader independent review and customer task evidence. Scores are rounded heuristic assessments, not measured performance.

| Area | Prior | Final | Evidence |
|---|---:|---:|---|
| Brand character |7|8|Restrained plum/violet identity, less repeated Z decoration, branded action colour|
| Visual consistency |5.5|8|Shared navigation icons, consistent disclosure direction and44px targets|
| Visual hierarchy |6|8|Draft heading, primary Review & publish, subordinate Edit/Copy/More|
| Simplicity |7|8|One destination group, one utility row, two Next Move disclosures; no new default panel|
| Typography/legibility |6|8|16px body,14px actions,14–15px details; checked contrast and narrow layouts|
| Perceived commercial polish |6.5|8|Desktop/mobile consistency and working edit/reload/keyboard paths; not commercial readiness|

Computed solid-colour contrast: white on primary#7137bd7.04:1; muted#65596f on#fcfbfd6.34:1; disclosure#574563 on white8.62:1; white on recommendation CTA#8040df5.65:1. These sample checks are not a full WCAG audit.

## Validation and limits

Full local SQLite suite272passed/1skipped. Node journey/onboarding/schedule/Studio harnesses passed, including failed-save/late-response coverage. Synthetic browser: desktop1280x720,390x844,320x740; edit/save/reload, keyboard review readiness, plan confirmation, recommendation disclosure via Enter. No browser console errors observed. Test providers mocked; no real social publication, grants or charges. Latest post-test changes are CSS/template narrow-header correction only; beta scope tests rerun. Hosted PR CI38240968536 and push CI38240961652 passed synthetic-tests, postgres-release and Production guardrails for the implementation candidate. PR25 is ready for release review; not merged or deployed.

Screenshots (synthetic/local): docs/validation/studio-design-desktop.jpg, studio-design-mobile.jpg, studio-design-next-move.jpg.

Follow-ups: customer tests for time-to-first-draft, first-click publishing comprehension and platform selection; real-model copy sampling; broader screen-reader/zoom/high-contrast review. Security, privacy, billing and operational readiness remain governed by docs/beta/KNOWN_GAPS.md. Rollback: redeploy1998cec with data/sessions/uploads/ledgers preserved; no schema migration.
