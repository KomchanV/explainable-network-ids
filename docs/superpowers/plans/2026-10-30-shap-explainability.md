# SHAP explainability implementation plan

Goal: explain current uploaded flows without altering the fitted pipeline or scientific engine.

Architecture: a focused HTTP adapter snapshots stored numeric features and predictions under the existing store lock, computes with the authoritative engine outside that lock, and rechecks session validity before returning. One process-local nonblocking lock bounds SHAP work; no cache is needed. Use seed 42 uniform sampling without replacement over all session rows. Preserve all local contributions in schema order and validate finite shapes and stored-probability reconstruction with atol=1e-6, rtol=1e-5.

- [x] Add failing API tests for local parity, imputation, deterministic global ranking, bounds, lifecycle, busy and numerical failures.
- [x] Implement typed explanation responses and routes in apps/api/explanations.py, with snapshot support and computation lock on AnalysisStore.
- [x] Regenerate OpenAPI and TypeScript schemas; extend typed client with a five-minute SHAP timeout.
- [x] Add tested waterfall geometry/aggregation helpers and reusable Svelte local/global components. Keep existing explorer and use row-keyed explanation state to discard stale responses.
- [x] Extend real synthetic-model browser workflow and error-state tests, including response switching.
- [x] Update architecture, development and traffic-analysis documentation with sample scope, imputation, precision and lifecycle constraints.
- [x] Run frozen install, check, test, build, contract check, E2E and trusted artifact compatibility if available; review changes, commit, push and prepare PR.

The user supplied the detailed design and explicitly authorized autonomous inline implementation. No model/provider switch or external provider use is required. The runtime model cannot be selected through these tools; OpenCode model discovery failed because its log directory is outside writable roots.

Verification evidence is recorded in [SHAP verification](../../shap-verification.md).
