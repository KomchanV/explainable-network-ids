# CSV Traffic Analysis implementation plan

Goal: Upload offline CIC-IDS2017 CSVs, run the unchanged trusted pipeline, explore ordered predictions, and export results.

Architecture: FastAPI streams raw CSV request bodies into bounded temporary files before invoking `read_csv(max_rows=50000)` and `predict_batch`. Raw bodies avoid multipart parsers spooling unbounded uploads before endpoint validation. A single-process, lock-protected temporary session store keeps summaries and feature-only detail files for one hour. The store caps session count and bytes; request concurrency is bounded. SvelteKit uses generated OpenAPI schemas and the shared client. No database, training, or changes to scientific preprocessing.

1. Add failing API workflow tests using synthetic fixture artifacts: parsing, limits, parity, pagination/filter/sort, details, export, deletion/expiry and cleanup.
2. Implement typed analysis schemas, bounded local sessions, raw upload endpoint and result routes. Preserve existing endpoints. Regenerate OpenAPI/TypeScript.
3. Add client tests for upload/error/filter/detail behavior; implement typed API methods and accessible upload/explorer routes using the existing dark theme. Extend dashboard/navigation.
4. Add Playwright browser tests using real fixture inference, register Nx E2E target and CI. Verify available browser tooling explicitly.
5. Run all Nx tests/checks/build, contract drift checks, compatibility checks and browser workflow. Update README, architecture/development and usage/API guide with observed limitations/results. Commit logical changes; no push or release.

Validation: fixture tests never require full CIC data. Trusted model bytes and `src/` remain unchanged. Predictions are not ground truth and P(DDoS) is an uncalibrated model output.
