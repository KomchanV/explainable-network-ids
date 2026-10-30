# Documentation index

This directory contains both **current v0.2 guidance** and **historical research/implementation records**. Start with the [repository README](../README.md) for requirements and a quick start.

## Current application (v0.2.0-alpha.1)

| Document | Purpose |
| --- | --- |
| [Security analysis UI redesign](ui-redesign/README.md) | Impeccable audit, design direction, before/after screenshots and final verification |
| [Workspace redesign](ui-redesign-verification.md) | v0.3 UI behavior, screenshots, validation and limitations |
| [Architecture](architecture.md) | Current Nx, SvelteKit, FastAPI, and Python engine boundaries |
| [Development workflow](development.md) | Setup, local commands, tests, CI, API schema generation |
| [CSV traffic analysis](traffic-analysis.md) | Upload limits, Flow Explorer, prediction export, temporary sessions |
| [Model Insights](model-insights.md) | Saved labeled evaluation, confusion matrix, provenance and interpretation |
| [Repository maintenance](repository-maintenance.md) | Branch strategy, release handling, document lifecycle |

For the shipped version, read the [v0.2 release notes](../RELEASE_NOTES_v0.2.0-alpha.1.md) and [changelog](../CHANGELOG.md). The historical [v0.1 release notes](../RELEASE_NOTES.md) remain unchanged.

## Scientific evidence and verification records

These are **time-stamped records**, not continuously updated assertions about the current HEAD.

| Document | Purpose |
| --- | --- |
| [Experiment results](experiment-results.md) | CIC-IDS2017 Friday DDoS evaluation and limitations |
| [Migration verification](migration-v0.2.md) | Python/Joblib compatibility during Nx migration |
| [Traffic Analysis verification](traffic-analysis-verification.md) | PR #2 validation |
| [SHAP verification](shap-verification.md) | PR #3 additivity, browser and fixture evidence |
| [Model Insights verification](model-insights-verification.md) | PR #4 saved metrics and UI validation |
| [v0.2 release verification](release-verification-v0.2.0-alpha.1.md) | CI, publication gates and release evidence |

Only the checked-in source and generated API contract define the current application behavior. Do not present synthetic test fixtures as research benchmarks. The held-out evaluation comes from the trusted model artifact and does not imply accuracy for newly uploaded, unlabeled CSVs.

## Historical design notes and course materials

- [Original v0.1 implementation plan](implementation-plan.md) — historical Streamlit/Python milestone.
- [Model Insights development plan](plans/model-insights.md) — implementation planning snapshot.
- [Agent implementation plans](superpowers/plans/) — dated decision records for earlier features.
- [Course demo and submission checklist](demo-checklists.md) — primarily the legacy v0.1 Streamlit demo; see the v0.2 development guide for current web commands.

Keep historical plans in place for traceability; they are not new tasks or claims that a shipped capability is still pending.

## Repository map

```text
apps/api/                 FastAPI adapter and API tests
apps/web/                 SvelteKit UI, browser and frontend tests
packages/api-client/      generated OpenAPI/TypeScript contract
packages/ids-core/        future packaging boundary documentation only
src/                      authoritative Python ML engine
tests/                    Python engine tests
scripts/                  verification and CLI helper scripts
docs/                     this documentation, historical plans and evidence
data/ models/ reports/    ignored local inputs, model artifacts and outputs
```

Do **not** relocate `src.preprocess.NumericFeatures` without an explicit legacy Joblib migration plan. The v0.1 and v0.2 release tags identify immutable historical source revisions. See [contributing](../CONTRIBUTING.md) and [security boundaries](../SECURITY.md).
