# Contributing

This repository is an **offline academic network-intrusion detection prototype**, not an internet-facing production security service.

## Before changing anything

Read [architecture](docs/architecture.md), [development workflow](docs/development.md), and the [documentation index](docs/README.md). Start a topic branch from the current `main` and open a pull request rather than editing `main` directly.

Keep changes focused. Prefer small PRs that preserve the existing Python ML engine, SHAP semantics, and checked-in generated API contract.

## Environment

The documented environment uses Python 3.11–3.13, Node.js 22.17+ and pnpm 11.4.0.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-api.txt
npm install --global pnpm@11.4.0
pnpm install --frozen-lockfile
```

See [development](docs/development.md) for platform-specific adjustments and local server configuration.

## Verification before submitting a PR

```bash
pnpm check
pnpm test
pnpm build
pnpm contract:check
pnpm nx e2e web --output-style=static
```

The browser suite needs Chromium installed; see the development guide. Tests use synthetic fixtures and do not require the CIC-IDS2017 dataset. If you have the existing trusted model locally, run `pnpm nx run ids-core:compatibility` read-only; do not retrain merely to run the application.

Include actual test results, commands, known limitations and any skipped checks in the PR description. GitHub Actions checks the Python, API, frontend, build and browser suites on PRs and pushes.

## Important compatibility rules

- Do not relocate `src.preprocess.NumericFeatures` or rename the `src` Python module without planning a migration for serialized Joblib artifacts.
- Preserve DDoS as class `1` for `predict_proba`, SHAP, saved metrics and confusion matrix orientation (`[[TN, FP], [FN, TP]]`).
- Saved held-out performance must not be presented as measured accuracy on user-uploaded CSV predictions.
- Do not treat SHAP attribution as causality, nor uncalibrated probability as confidence or severity.
- After API schema edits, run `pnpm contract:generate` and commit both generated contract files.
- Avoid new background services, external providers, authentication claims, or live-capture capabilities unless specifically scoped and reviewed.

## Repository hygiene

Do not commit `data/raw`, `models`, `reports`, `.env`, local caches, test recordings, or credentials. Those locations are intentionally gitignored. Keep a separate, approved process for course artifact submission if datasets/models/reports must be included.

Treat original releases, tags, dated experiment reports and historical plans as immutable evidence. Branch deletion, release publication and tag creation are separate, explicit maintainer decisions. See [repository maintenance](docs/repository-maintenance.md).

## Vulnerabilities and sensitive reports

Do not create a public issue containing exploitable details or private datasets. See [SECURITY.md](SECURITY.md) for the reporting path and local-only threat model.
