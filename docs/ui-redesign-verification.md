# v0.3 UI redesign verification

Date: 2026-10-30 (Asia/Bangkok). Base: `main` at `9840364` after fetching origin.
No release, deployment, auto-merge, backend or model change is included.

## Implemented

The [assessment/plan](plans/v0.3-workspace.md) records verified capabilities and the
original UX issues. [DESIGN.md](../DESIGN.md) defines the token/component decisions.

| Navigation | Route | Behavior |
| --- | --- | --- |
| Overview | `/` | Real current-analysis counts and prediction distribution; import guidance, service/model status and expiry recovery |
| Analyses | `/analyze` | CSV select/drop, file checks, optional actual feature schema, server validation/inference, results and investigation link |
| Traffic Explorer | `/explorer`, `/analyses/[id]` | Resolve current session; filter/sort/page, inspect drawer, local/global SHAP, CSV export and confirmed deletion |
| Model Insights | `/model-insights` | Saved evaluation/matrix/provenance; separate uploaded-sample global importance, generated on demand |

No durable history exists. The browser remembers one ID; the service remains a
bounded temporary store. No prediction statistic is labeled evaluation accuracy.
Native controls, shared surfaces, theme-aware semantic badges and consistent actions
replace the inconsistent styling. Technical metadata/contribution tables use
progressive disclosure; actual values and feature order are preserved.

## Checks

- Baseline: 16 frontend unit tests, no Svelte diagnostics, 10 original browser scenarios passed.
- `NX_DAEMON=false pnpm nx run-many -t check,test,build --parallel=2 --output-style=static`: passed for all four projects, including the OpenAPI dependency check. 43 engine tests, 57 API tests, 17 frontend tests. Svelte check: 0 errors / 0 warnings. Production Node build passed. OpenAPI and generated TypeScript match.
- Browser suite uses its existing local synthetic training/CSV fixture and actual FastAPI inference/SHAP, not production mock values. Coverage includes server errors, schema rejection, export, deletion, expiry, stale explanations, client navigation, saved metrics, theme persistence, mobile navigation, preserved filters, drawer focus, overview distribution and Model Insights sampled SHAP.
- Final `NX_DAEMON=false pnpm nx e2e web --output-style=static`: **14 passed** (21.6s). The mobile modal assertion permits native focus moving into browser chrome, but rejects focus on underlying page controls. Both themes pass WCAG AA text-pair checks (>=4.5:1) and input-boundary checks (>=3:1).
- Final `NX_DAEMON=false pnpm nx affected -t check,test,build --base=origin/main --parallel=2 --output-style=static`: **passed**, all four projects plus the contract dependency, 0/9 cache hits. Uses an explicit current base because the repository's historical defaultBase still points to a release branch.
- `git diff --check`: passed. The repository defines no ESLint or formatter targets/configuration; neither is claimed to have run. No tool was installed solely to create another gate.
- Existing API pytest emits one Starlette/httpx deprecation warning. Node emits inherited NO_COLOR/FORCE_COLOR notices. They do not fail checks.

## Visual evidence

All screenshots depict synthetic browser-test data, **not research performance**.

| Before | After |
| --- | --- |
| [Overview](screenshots/v0.3-before-overview.png) | [Light overview](screenshots/v0.3-overview-light.png), [dark overview](screenshots/v0.3-overview-dark.png) |
| [Mobile import](screenshots/v0.3-before-mobile.png) | [Mobile import](screenshots/v0.3-import-mobile-light.png) |
| Existing details were below the table | [Desktop drawer](screenshots/v0.3-explorer-drawer-dark.png), [mobile drawer](screenshots/v0.3-drawer-mobile-dark.png) |
| Saved evaluation only | [Model Insights and separately labeled upload SHAP](screenshots/v0.3-model-insights-dark.png) |

Screenshots are reproducible through `workspace.spec.ts` and were visually inspected.
A separate read-only Codex review found no additional material issue in the original
four implementation commits/screenshots; the known full-width mobile nonmodal issue
was then fixed using native modal focus containment and a browser assertion. A follow-up independent review of that fix found no concrete issue.

## OpenCode delegation and cost

Installed OpenCode: **2.1.4**. `opencode models` listed Big Pickle and free variants of
GLM-5.3-Flash, DeepSeek V4.1 Flash, Beam, Flint 40B, MiMo-V2.6-Flash, Nemotron 3.5
Lightning and Nemotron 3.5 Super VL. Availability and cost are time-sensitive.
The local `/provider` request returned HTML; `/api/provider` returned an empty list,
so pricing was verified against the [official live pricing table](https://opencode.ai/v2/docs/console/models/)
before delegation. GLM-5.3-Flash Free was advertised as Free for input/output/cache.

Successfully delegated one bounded generic accessibility/race-condition checklist to
`opencode/glm-5.3-flash-free` using an isolated `/tmp` directory. The prompt prohibited
tools/file reads and contained no source files, secrets, credentials or datasets.
Its useful recommendations informed stale-result invalidation, expiry handling,
focus restoration and mobile scrolling checks. Codex rejected its blanket advice
against moving focus to a nonmodal inspector and unsupported gesture assumptions;
intentional user inspection moves focus to the close control. Codex retained all
implementation, architecture, model semantics, integration and acceptance work.
No paid fallback, tool installation, account or billing setting was used. Pricing
was advertised zero; no separate billing receipt was produced by the CLI.

## Limitations and follow-up

- No incremental job-progress API exists: validation/inference and SHAP show honest indeterminate states.
- No persistent history, general metadata search, calibrated probabilities, confirmed incidents or live traffic capture was added. Search remains supported row-number lookup plus existing class/probability filters because ignored metadata is not retained.
- Chromium desktop/mobile emulation was used; Safari/Firefox, physical devices and manual screen-reader verification remain useful follow-ups. Keyboard and semantic checks are not a formal accessibility certification.
- Trusted real research artifacts were not needed for this UI-only change. Existing synthetic compatibility/inference tests passed; screenshots must not be cited as model benchmarks.
- Package versions remain 0.2.0-alpha.1 pending an explicitly authorized release.
- Initial development exposed a theme event-order issue and icon barrel SSR error; explicit event values and direct per-icon imports fixed them. One initial trace hit local disk limits; later complete runs succeeded. No unrelated files were deleted.

## Review sequence

Five focused stacked branches are prepared, each based on its predecessor:
`feat/v0.3-workspace-shell` -> `feat/v0.3-overview-analysis` ->
`feat/v0.3-traffic-explorer` -> `feat/v0.3-model-explainability` ->
`feat/v0.3-ux-quality`. Review and integrate in that order. Final aggregate validation
above covers the complete stack; no claim is made that every intermediate commit was
independently run through the final test matrix. The quality phase includes the
hydration-readiness and mobile focus refinements found during browser review.
No API contract migration, new dependency or release version bump is required.
