# Model Insights verification and v0.2 alpha readiness

Observed locally on 2026-10-30 (Asia/Bangkok), based on main commit `0d92ae6`
(PR #3 merge). No trusted model training or artifact changes were performed.

## Verification evidence

| Check | Observed result |
| --- | --- |
| `pnpm install --frozen-lockfile` | Passed, lockfile already current |
| Baseline `pnpm test` | All 3 Nx test targets passed before endpoint implementation |
| `pnpm check --output-style=static` | Passed; Svelte check 0 errors, 0 warnings; Python compile and contract checks passed |
| `pnpm test --output-style=static` | Passed: API 57 tests, ML engine 43 tests, frontend 16 tests |
| `pnpm build` | Passed, SvelteKit production build |
| `pnpm contract:check` | Passed: FastAPI/OpenAPI and generated TypeScript synchronized |
| `pnpm nx e2e web --output-style=static` | Passed: browser regression suite including CSV analysis, local/global SHAP and Model Insights |
| `pnpm nx run ids-core:compatibility --output-style=static` | Passed on local CIC-IDS2017-labeled artifact; details below |
| `git diff --check` | Passed |

Nx commands were run with `NX_DAEMON=false NX_ISOLATE_PLUGINS=false` after the initial
baseline emitted restricted-socket warnings and fell back successfully. Browser checks
needed permission to start local servers/Chromium. Initial new API tests failed with 404
before implementation; the first web check caught missing `.js` import suffixes, corrected
before the passing run. Starlette emits an existing BlockingPortal deprecation warning;
Node emits existing NO_COLOR/FORCE_COLOR warnings. These were not suppressed by test changes.

New API tests exercise saved snapshot parity, matrix orientation with unequal FP/FN,
zero division, undefined FPR, invalid scores/counts/class mappings/class counts, missing
metadata, synthetic provenance, filename sanitization, unavailable models, compatibility
of `/model`, and retrieval with fitting/predicting/deserialization forbidden. Browser
checks compare displayed scores and matrix cells with the actual synthetic backend response,
exercise navigation/refresh/mobile, and cover loading, API/model errors and missing fields.
No production component contains fixture metrics.

## Trusted artifact compatibility

Artifact SHA-256: `28574587cb16f236b86c874c30251b13772abe3eba013c8adaa14aba65744972`.
The compatibility verifier compared 100 rows and reported CLI parity, pipeline parity,
SHAP reconstruction and `artifact_unchanged: true`. Maximum SHAP reconstruction error:
`5.551115123125783e-16`. It explicitly reported `pre_migration_baseline_compared: false`;
this is parity against the current engine, not a historical baseline proof.

A read-only TestClient call against the trusted local model returned HTTP 200 with saved
matrix `[[18654, 1], [12, 25591]]`, evaluated rows 44,258, accuracy
`0.9997062677933933`, precision `0.9999609252891528`, recall `0.999531304925204`,
F1 `0.9997460689520461`, and FPR `0.00005360493165371214`. TN/FP/FN/TP therefore
sum to 44,258. These are observations from the artifact, not newly computed experimental
results or evidence for generalization. Saved source label: `cic-ids2017`.

## Release assessment

The implementation appears suitable for **v0.2.0-alpha.1 review**, subject to passing remote
CI and maintainer review. Model Insights, traffic analysis, Flow Explorer and SHAP are
functional; generated contracts and development/architecture/usage documentation are
updated. Versions already read `0.2.0-alpha.1` on main and were not bumped. No tag, release,
merge, or release-history modification is part of this milestone.

Deployment assumes pinned dependencies, an operator-provided trusted local Joblib artifact,
a reachable configured API URL and controlled offline/local academic use. Joblib may
execute code: untrusted model artifacts must never be loaded. The evaluation endpoint is
read-only and independent of analysis sessions; metadata is allowlisted and paths stripped.
The prototype does not add authentication, live network capture, calibrated probabilities,
or production security hardening. Uploaded data handling retains existing bounded temporary
session behavior. Do not deploy this as an internet-facing security product.

Scientific limitations remain same-capture evaluation, unproven external generalization,
distribution shift, adaptive-attack robustness, uncalibrated probabilities and noncausal
SHAP explanations. Provenance labels are creator-supplied assertions, not authenticated
source attestations. Missing historical metadata stays null. These limits are visible in
the UI and [usage guide](model-insights.md).

Remaining publication gates: PR review and remote GitHub Actions success. Release
publication requires a separate explicit task; this report does not authorize publication.

## Runtime and cost

Implementation used the already-authorized Codex runtime, with one code-review subagent
required by the review skill. No OpenCode inference or provider/model switch occurred.
`opencode models` succeeded after permission to write its log and listed free-named models,
but the CLI exposes no pricing metadata. The inspected OpenCode config had no explicit
provider section. Free pricing and provider authorization were therefore **not verified**;
a free suffix was not treated as evidence of zero cost. No claim of free-of-charge model
usage is made, and no private source was sent to a newly selected provider.
