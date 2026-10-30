# v0.2.0-alpha.1 — release verification record

Date: 2026-10-30 (Asia/Bangkok). Release preparation is based on GitHub main commit `bba4c9fa6102303f9b4d9ff4463c375b6c5ed1fa`, after PR #4 merged.

## Confirmed remotely before release preparation

- GitHub repo default branch: `main`; private repository.
- PRs #1, #2, #3 and #4 merged to main.
- GitHub Actions main push run [40979780792](https://github.com/KomchanV/explainable-network-ids/actions/runs/40979780792): completed successfully on the above main SHA. Workflow includes pinned Python 3.13, Node 22, pnpm 11.4.0, frozen dependency install, Nx check/test/build and Playwright Chromium E2E.
- Root package version and API/Web UI version: `0.2.0-alpha.1`.
- Existing `refs/tags/v0.1.0-alpha.1` is an annotated tag and must not be modified.
- Before release preparation, there was no `v0.2.0-alpha.1` GitHub release or tag reference.
- The Git tree did not include actual model.joblib or source datasets.

## Evidence from existing milestone verification

- [Model Insights verification](docs/model-insights-verification.md) reports 57 API, 43 ML engine, 16 frontend and 10 browser tests passed, saved held-out metrics backed by the trusted artifact, and read-only model compatibility.
- [SHAP verification](docs/shap-verification.md) records numerical reconstruction limits and synthetic browser testing.
- These milestone runs and the already-completed mainline CI are the verification evidence. A separate clean-clone release candidate matrix across operating systems has **not** been executed in this preparation.

## Publication gates

Before tagging/publishing, verify the release-preparation PR is merged and the resulting main SHA has passed CI. Confirm changelog/release notes match that SHA. Tag **that exact verified commit** as `v0.2.0-alpha.1` (prefer an annotated signed tag when possible), with no tag rewrite. Publish a GitHub **pre-release** using `RELEASE_NOTES_v0.2.0-alpha.1.md`. Verify tag target, published release URL, prerelease flag, and attached assets (none expected). Do not change v0.1 tags, models, or experiment results.

## Safety and scope

Source-only academic prototype; no live capture, authentication, calibrated confidence, out-of-distribution validation or real-world production hardening. The only permitted runtime model is trusted operator-owned Joblib. No release metrics are newly recomputed.
