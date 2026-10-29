# Nx v0.2 migration implementation plan

**Goal:** Establish the 0.2.0-alpha.1 polyglot foundation without changing scientific behavior.
**Architecture:** Keep root `src` import paths and all v0.1 workflows. Nx orchestrates a Python engine, thin FastAPI adapter, generated TypeScript contract, and SvelteKit app. No database or ML runtime dependency on Nx.
**Execution:** Inline and autonomous under the supplied task specification.

- [x] Investigate source, artifact format, CLI, documentation, Git state, and tests. Baseline: 39 passed in 21.72s; trusted real model available. Create feature branch.
- [x] Configure pnpm and Nx with explicit project dependencies; disable caching for Python tests, training, servers, and checks involving mutable local artifacts.
- [x] Add API tests first for health without a model, consistent errors, metadata, configuration, and prediction equivalence. Implement an adapter calling `src.predict`, never taking artifact paths from requests.
- [x] Export deterministic OpenAPI and generate TypeScript types; check reproducibility and drift. Commit generated contract so web checks need no running backend.
- [x] Scaffold SvelteKit using the official Svelte CLI (Nx has no first-party SvelteKit generator). Add Tailwind and shadcn-svelte foundation, reusable layout, live API status/metadata, loading and failure states. Test the API client success and failure behavior.
- [x] Verify Nx graph, task dependencies, Python/API tests, frontend checks/test/build, server startup, and live frontend/backend integration.
- [x] Compare trusted-model predictions before/after, verify SHAP reconstruction, and record artifact hashes. Exercise existing CLI help and inference without training.
- [x] Document actual structure, setup, tasks, boundaries, migration constraints, verification, and limitations. Preserve historical scientific evidence and release notes; no push, release tag, merge, or publication.

## Decisions

Keeping `src` avoids breaking Joblib's `src.preprocess.NumericFeatures` reference. Root `project.json` owns the existing engine and its source/tests/scripts so Nx affected analysis includes legacy paths; `packages/ids-core` documents future packaging only. Moving Python immediately risks serialization failure; a runtime alias layer adds complexity with no current benefit.

FastAPI is the schema authority. OpenAPI TypeScript generation prevents handwritten response-schema drift. Explicit `nx:run-commands` targets keep Python independent of Node and make SvelteKit's supported CLI authoritative. Only deterministic frontend work is cached, with runtime versions and environment inputs included. The dashboard displays real service state and metadata, not simulated traffic.
