# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added — v0.2.0-alpha.1 foundation

- Nx integrated pnpm workspace with web, API, generated contract, and Python engine projects.
- SvelteKit/Svelte 5 dashboard with live API health/model metadata, Tailwind, and shadcn-svelte.
- FastAPI adapter with model-independent health, metadata, bounded batch inference,
  consistent errors, local CORS, and trusted server-only artifact configuration.
- OpenAPI export, generated TypeScript types, schema drift checks, API/client tests,
  CI workflow, and architecture/development/compatibility documentation.
- Read-only CLI/pipeline/SHAP artifact compatibility verification.

### Compatibility

- Preserve `src` import paths, scientific dependency pins, fitted pipelines,
  existing CLIs, Streamlit, experimental evidence, and v0.1 release history.
- No model retraining or release tag is part of the migration.

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
