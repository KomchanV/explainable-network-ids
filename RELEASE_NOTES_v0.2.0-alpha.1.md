# v0.2.0-alpha.1 — Explainable Network IDS

## Release status

Pre-release candidate for the **offline academic prototype**. This document records the contents of the proposed GitHub release. The source repository does not include the CIC-IDS2017 dataset, trusted Joblib model, or generated experimental reports.

## What's new since v0.1.0-alpha.1

- **Nx/pnpm monorepo:** SvelteKit web frontend, FastAPI backend, generated OpenAPI TypeScript contracts, and the original Python ML engine.
- **Traffic Analysis:** Bounded offline CSV upload, batch classification, analysis summaries, paginated/filterable Flow Explorer, flow inspection, prediction CSV export, and expiring temporary sessions.
- **Explainability:** On-demand local DDoS-class SHAP waterfall, signed contribution tables, and deterministic sampled global feature importance (up to 100 flows), with additivity checks against stored predictions.
- **Model Insights:** Read-only model evaluation endpoint, confusion matrix, accuracy/precision/recall/F1/FPR, training methodology, metadata/provenance, and explicit interpretation limits.

The original Python CLI and Streamlit workflow remain available. Existing trusted model import paths, pinned scientific dependencies, and trained model semantics are preserved.

## Requirements and quick start

Python 3.11–3.13, Node.js 22.17+, pnpm 11.4.0. From the repository root:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-api.txt
npm install --global pnpm@11.4.0
pnpm install --frozen-lockfile
pnpm dev
```

Open http://127.0.0.1:5173 for the web app and http://127.0.0.1:8000/docs for the API. A trusted local Joblib model must be configured for model-dependent routes (default `models/model.joblib`; optionally set `IDS_MODEL_PATH`). Startup does **not** retrain or download a model. Never load untrusted Joblib files.

See [development setup](docs/development.md), [traffic analysis](docs/traffic-analysis.md), [model insights](docs/model-insights.md), and [SHAP verification](docs/shap-verification.md).

## Verification evidence

At feature integration, GitHub Actions `Monorepo checks` succeeded on main commit `bba4c9fa6102303f9b4d9ff4463c375b6c5ed1fa` (run [40979780792](https://github.com/KomchanV/explainable-network-ids/actions/runs/40979780792)), including dependency installation, Nx check/test/build, and Playwright Chromium E2E.

The PR #4 implementation reported 57 API tests, 43 scientific engine tests, 16 frontend unit tests, and 10 Playwright tests; these counts are agent-reported and should not be confused with separate release-branch test execution.

Read-only local trusted-artifact compatibility was reported for 100 rows, with prediction parity, unchanged artifact SHA-256 `28574587cb16f236b86c874c30251b13772abe3eba013c8adaa14aba65744972`, and maximum SHAP reconstruction error `5.551115123125783e-16`. No historical pre-migration prediction baseline was available. CI E2E uses isolated synthetic fixtures, not the trusted real model.

## Scientific scope and limitations

The recorded CIC-IDS2017 Friday DDoS experiment used 44,258 labeled held-out rows from the same capture scenario. Its saved confusion matrix is `[[18654, 1], [12, 25591]]`; these are **existing** evaluation results, not newly measured release results. A same-capture random holdout does not establish generalization to other capture days, networks, novel attacks, or adaptive adversaries. Uploaded unlabeled CSV predictions cannot establish accuracy. Model probabilities are uncalibrated; SHAP explanations are not causal evidence.

This is an **offline, local-only academic demonstration**. It has no authentication, no live packet capture, no monitoring/blocking, no persistent analysis database, and no public-deployment security hardening. Keep API and web on loopback; CORS is not authorization. Analysis sessions are temporary and process-local.

## Release notes and upgrade considerations

- This is an **alpha pre-release**, not a stable/production deployment.
- A new SvelteKit/FastAPI workflow supplements, rather than replaces, the original Python/Streamlit CLI.
- No model or dataset binary is attached. Users supply their own trusted artifact and permitted source CSV.
- Lockfile and generated OpenAPI contracts are committed for reproducible installation.
- The old `v0.1.0-alpha.1` annotated tag and release history remain unchanged.

For detailed changes see [CHANGELOG.md](CHANGELOG.md).
