# Explainable Network IDS — UI/UX redesign

The redesign uses a restrained graphite/mineral-teal operational workspace. It preserves offline CSV inference, temporary analyses, flow filtering/export/deletion, local/global SHAP, and saved model evaluation. No live status, alerts, confidence scores, severity levels or permanent history were invented.

## Audit and design decisions
The [audit](audit.md) identified flattened hierarchy, a history-like import label, repeated summaries delaying the table, late access to uploaded explanations, and keyboard/error accessibility gaps. Navigation now reads Overview → Import & analyze → Traffic Explorer → Model Insights. Existing URLs remain compatible.

The [product context](../../PRODUCT.md), [design system](../../DESIGN.md), [Impeccable record](impeccable-workflow.md) and [direction contract](../../apps/web/.impeccable/surfaces/apps-web-src-routes-page-svelte.md) capture truth, rationale, and implementation standards. No new runtime dependency was added.

## Implemented experience
- Graphite navigation rail, persistent light/dark/system themes, consistent controls and semantic status colors.
- Task-first overview empty state and a unified actual-data metric strip.
- Import workflow, styled native file input/drop region, schema disclosure and associated errors.
- Compact explorer summary, grouped filtering/ordering, inline empty-results reset and destructive confirmation styling.
- Clear model explanation hierarchy, keyboard-scrollable contribution tables and section links separating uploaded-data SHAP from saved evaluation.
- Mobile navigation contrast, short-window sidebar scrolling, bounded live announcements, visible focus and reduced motion.

## Visual evidence
Captures use the isolated synthetic model and actual inference/SHAP outputs; they are test evidence, not production traffic.

| Surface | Before | After |
| --- | --- | --- |
| Overview, dark | [Before](before-overview-dark.png) | [After](after-overview-dark.png) |
| Import, mobile light | [Before](before-import-mobile.png) | [After](after-import-mobile-light.png) |
| First use | — | [Desktop](after-first-use-desktop-light.png), [mobile](after-first-use-mobile-light.png) |
| Explorer | — | [Desktop](after-explorer-desktop-dark.png), [tablet](after-explorer-tablet-dark.png) |
| Flow explanation drawer | — | [Desktop](after-explorer-drawer-dark.png), [mobile](after-drawer-mobile-dark.png) |
| Model Insights | — | [Full page](after-model-insights-dark.png) |

Historical before captures come from committed v0.3 screenshots matching the inspected incumbent. The current-run before-desktop-loading.png shows startup loading only.

## Verification and limitations
[Verification](verification.md): Svelte0 errors/warnings,17 frontend unit tests,14 Chromium E2E tests, production build, root Nx check5/5 and test3/3 tasks, API contract2/2 tasks, and zero source detector findings. [Independent Impeccable finish review](finish-review.md): disposition **ship**, no material fixes within sampled code and supplied views.

No standalone lint/formatter target exists. Chromium emulation is not physical-device or screen-reader certification. Desktop inspector remains intentionally nonmodal for comparison; mobile is modal. Automatic Impeccable project config is enabled, but no provider manifest was installed; the manual scan ran. The underlying application remains an offline academic prototype with temporary data, not a production live IDS.

Branch: `codex/ui-ux-redesign`. The checkout began on `feat/v0.3-ux-quality`; PR should target that branch to keep prior work out of this diff. No default branch merge is performed.

PR: https://github.com/KomchanV/explainable-network-ids/pull/12. Implementation commit: `efef378`. Design/evidence documentation follows in a separate commit.
