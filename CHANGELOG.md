# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0-alpha.1] - 2026-10-30

### Added — monorepo foundation

- Nx integrated pnpm workspace with web, API, generated contract, and Python engine projects.
- SvelteKit/Svelte 5 dashboard with live API health/model metadata, Tailwind, and shadcn-svelte.
- FastAPI adapter with model-independent health, metadata, bounded batch inference,
  consistent errors, local CORS, and trusted server-only artifact configuration.
- OpenAPI export, generated TypeScript types, schema drift checks, API/client tests,
  CI workflow, and architecture/development/compatibility documentation.
- Read-only CLI/pipeline/SHAP artifact compatibility verification.

### Added — offline CSV traffic analysis (PR #2)

- Streamed CSV upload with bounded file size and row limits, using the existing trusted Random Forest inference pipeline.
- Analysis summary, server-side paginated/filterable Flow Explorer, single-flow inspection, prediction export, and temporary session deletion/expiry.
- Browser E2E coverage for the offline CSV workflow.

### Added — SHAP investigation (PR #3)

- On-demand per-flow DDoS-class SHAP waterfall and complete feature contribution table.
- Deterministically sampled global mean-absolute SHAP importance, limited to 100 flows per request.
- Backend validation of SHAP additivity against stored DDoS probabilities, plus concurrency and lifecycle safeguards.

### Added — model insights (PR #4)

- Read-only saved held-out evaluation API backed by existing model metrics, not uploaded predictions.
- SvelteKit Model Insights view with full-precision-aware metrics, confusion matrix, provenance, methodology, and scientific limitations.
- Saved evaluation consistency checks, generated API contracts, and scientific/API/frontend/browser regression tests.

### Release verification

- Mainline GitHub Actions verify Python/TypeScript checks, automated tests, builds, and Chromium E2E with synthetic fixtures.
- The trusted CIC-IDS2017 model artifact was checked read-only for inference and SHAP compatibility using a local artifact, not shipped with the source release.
- No retraining, model replacement, or new held-out performance claims.

### Limitations

- Offline, local-only academic prototype; no authentication, live packet capture, or public deployment hardening.
- CIC-IDS2017 metrics represent a labeled same-capture held-out split, not unseen-network generalization.
- P(DDoS) is uncalibrated; SHAP describes model behavior and is not causal attack evidence.
- Uploaded CSV prediction counts are not evaluation accuracy or ground truth.

### Compatibility

- Preserve `src` import paths, scientific dependency pins, fitted pipelines,
  existing CLIs, Streamlit, experimental evidence, and v0.1 release history.
- The original model was not retrained or replaced by the v0.2 implementation. Publication and tagging are handled separately from feature development.

## [0.1.0-alpha.1] - 2026-10-30

### Added

- Offline BENIGN-versus-DDoS training and evaluation on network-flow CSV data.
- Batch prediction with saved-schema validation and row-order preservation.
- Streamlit dashboard for local inference, metrics, downloads, and SHAP views.
- Global and local SHAP explanations with probability reconstruction checks.
- Deterministic synthetic smoke fixtures and a documented CIC-IDS2017 workflow.
- Automated tests for data validation, leakage controls, persistence, inference,
  explanations, comparison reporting, and dashboard behavior.
- Reproducibility scripts and documented real-data experiment results.

### Security

- Raw datasets, trained models, generated reports, environment files, caches,
  and local virtual environments are excluded from version control.
