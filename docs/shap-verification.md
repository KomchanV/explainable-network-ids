# SHAP milestone verification — 30 October 2026

The feature branch starts at `7d73178` (latest origin/main at implementation,
including merged PR #2). The scientific SHAP engine, preprocessing pipeline,
Random Forest configuration and trusted artifacts are unchanged.

## Local commands and observed results

Nx commands used `NX_DAEMON=false NX_ISOLATE_PLUGINS=false` to avoid sandbox-denied
plugin sockets. Playwright required loopback/browser execution permission.

| Command | Observed result |
| --- | --- |
| `pnpm install --frozen-lockfile` | Passed; lockfile unchanged |
| `pnpm check --output-style=static` | Passed; Python compile, synchronized contracts, Svelte diagnostics |
| `pnpm test --output-style=static` | Passed: 43 scientific, 41 API, 14 frontend tests |
| `pnpm build --output-style=static` | Passed; Node adapter production build |
| `pnpm contract:generate` | Regenerated OpenAPI and TypeScript from FastAPI |
| `pnpm contract:check --output-style=static` | Passed; both generated files synchronized |
| `pnpm nx e2e web --output-style=static` | Passed: 7 Chromium tests, including existing explorer/export behavior |
| `pnpm nx run ids-core:compatibility --output-style=static` | Passed; trusted CIC-IDS2017 artifact unchanged |
| `git diff --check` | Passed |

The trusted compatibility run checked 100 held-out flows for read-only regression
verification (the HTTP explanations separately use current uploaded data). Maximum
absolute SHAP reconstruction error was **6.661338147750939e-16**, against existing
`atol=1e-6, rtol=1e-5`. CLI and pipeline parity passed. No pre-migration prediction
baseline file was supplied. SHA-256 remained
`28574587cb16f236b86c874c30251b13772abe3eba013c8adaa14aba65744972`.

Synthetic fixtures cover stored-probability parity for BENIGN and DDoS, median
imputation, feature ordering, mean absolute ranking, deterministic sampling,
100-row limits, busy requests, shape/finite/reconstruction rejection, deletion
and expiration overlapping both local/global computations. Browser tests use
actual API numerical responses and test late local responses plus client-side
navigation between analyses. An independent review found the navigation issue;
the regression failed before the keyed route boundary fix and passed afterward.

Screenshots are generated in ignored `apps/web/test-results/`:
`shap-local-desktop.png`, `shap-local-mobile.png`, `shap-global-desktop.png`.
They show the isolated synthetic model, not research results. These were visually
inspected for chart geometry, labeling, mobile layout and the table alternative.

## Limits and model/runtime disclosure

Single local worker; one SHAP computation at a time; at most 100 sampled flows;
no explanation cache. HTTP timeout/navigation does not guarantee Python work
stops. Uniform sampling can miss rare patterns. SHAP is model behavior, not causal
attack evidence; probabilities remain uncalibrated. Fixtures do not establish
scientific generalization. Server latency is not guaranteed by a sample bound.

Work used the authorized Codex runtime, including one inherited-runtime review
agent. No OpenCode model was used or provider/model switch performed. The local
`opencode models` discovery command failed because its log directory was outside
sandbox write permissions. Available free OpenCode models and their current free
status therefore were not verified. No repository content was sent to a new
external model provider.

A suitable next milestone is model insights and evaluation provenance, including
explicit calibration and generalization studies before stronger probability claims.
