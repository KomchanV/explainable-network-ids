# PR 2 verification record — 30 October 2026

## Scope and files

The isolated feature branch includes reviewed, CI-green PR #13 as a dependency;
main was not merged or modified. Original uncommitted UI/UX work was preserved.
See [architecture, measurements and limits](scalable-traffic.md) for the design,
resource model and exact benchmark commands/raw reports.

- `src/data_loader.py`: reusable strict iterator; compatibility whole-frame wrapper.
- `apps/api/analyses.py`: batch ingestion, atomic publication, finite configuration,
  upload/disk/deadline guards, SQL query/detail routes and export response leases.
- `apps/api/result_storage.py`: bounded-cache SQLite, indexed numeric result schema,
  conservative transient disk reservation and incremental CSV export primitives.
- `apps/api/explanations.py`: bounded row/sample SQL snapshots, unchanged SHAP checks.
- `apps/api/tests/test_analyses.py`, `tests/test_data.py`: extended existing regressions.
- `scripts/benchmark_traffic.py`: reuse #13's synthetic runner; optional HTTP upload,
  bounded export consumer, stage memory metrics and verification of every prediction.
- Two Svelte route files: only default limit text changed to 100k rows/25.6M cells.
- README, traffic guide, plan and performance records: updated lifecycle/quotas/results.

No model, training/preprocessing algorithm, label mapping, saved evaluation,
Python/JS dependency, lockfile, generated API contract or unrelated UI component
changed. E2E regenerated screenshots were restored to the branch's prior versions.

## Tests and commands

The existing Python 3.13.13 virtualenv and locked pnpm 11.4.0 installation were
used. Nx projects/targets were inspected via `nx show project`. Commands used
`NX_DAEMON=false NX_ISOLATE_PLUGINS=false`; E2E had permission for local-only
127.0.0.1 test servers. No verification checks were weakened or disabled.

| Verification | Actual result |
| --- | --- |
| Iterator/integrated batch tests before implementation | 5 failed as expected (missing iterator/full-frame ingestion/no late batch failure) |
| Initial focused CSV/API integration | 65 passed; 1 old test needed to inject persisted corruption via SQLite instead of removed DataFrame |
| 100k/lifecycle/limits/concurrency/reconstruction focused tests | 8 passed |
| SQLite quota exhaustion after several successful batches | Passed; no session/DB/journal/upload reservation/ingestion-slot leak |
| Benchmark smoke/size-limit tests | 5 passed |
| `pnpm contract:check` | Passed (no OpenAPI/client drift) |
| `pnpm check` | Passed (5 targets) |
| `pnpm test --output-style=static` | Passed: core 50, API 77 + 1 optional skip, web 17 |
| `pnpm build` | Passed |
| `pnpm nx e2e web --output-style=static` | Passed: 14 browser tests |
| Final query-integer/OS failure regressions, before fixes | 2 failed as expected |
| Final focused rerun `python -m pytest -q apps/api/tests` | 79 passed, 1 optional skip |
| 50k × 3 + HTTP 100k + bounded 100k/500k/1M benchmarks | All 7 cases passed, every prediction/probability/key/export row verified |
| `git diff --check` | Passed |

Only the affected API suite was rerun after final review guards. The optional
skip is the pre-existing trusted v0.1 artifact test: the isolated worktree has no
repository model/data. Normal tests fit only existing small synthetic fixtures;
benchmarks explicitly fit only an ephemeral synthetic fixture outside timing.
Existing Starlette BlockingPortal deprecation and Node color-environment warnings
remain. The full check/test/build/e2e run was successful before the final API
edge guards; unchanged core/web checks were not repeated without new evidence.
Remote CI must also pass on the pushed branch; its status is available in the PR.

## Coverage and correctness evidence

Existing workflow/filter/ordering/privacy/lifecycle/explanation regressions remain.
New tests verify actual batch sizes, SQL file format, no retained predictions or
offsets, whole-frame parity, missing/infinite features, global row numbering,
imputation aggregation, duplicate rows, ignored-value exclusion, late failure
atomicity, upload/disk reservation, mid-write SQLITE_FULL cleanup, real concurrent
ingestion exclusion, finite environment configuration and processing deadlines.

Export tests cover full results, class/probability ties and boundaries, delete and
expiry during a live export, retained-file quota, export concurrency/deadlines,
idempotent release and ASGI disconnection. Query-plan checks reject temporary sort
B-trees for both probability directions. Huge Python integers preserve empty-page/
not-found behavior rather than overflowing SQLite int64 binds. Upload filesystem
failure produces a sanitized 503 and releases the slot/reservation.

The regular synthetic 100k integration test uploads through HTTP, asserts ten
10k inference calls, checks pagination/last-row details, deterministic seed-42
sampling, local/global SHAP reconstruction and every exported row/class/probability,
then verifies deletion. A larger benchmark additionally passed 1M rows through
backend ingestion/query/SHAP/bounded export/delete with an explicit row-limit
override; no 1M HTTP/browser support is claimed. All 50k CSV hashes match PR #13's
original result exactly. Saved medians and the authoritative predictor/SHAP engine
remain unchanged, with existing numerical reconstruction tolerances.

## AI usage, cost and remaining limitations

One primary Codex agent implemented and self-reviewed the integration. Installed
OpenCode was inspected and listed `opencode/glm-5.3-flash-free` and
`opencode/deepseek-v4.1-flash-free`. No external model was called: pricing was not
independently verified, and delegation offered no benefit for this coupled work.
No paid fallback, provider changes or new AI services were used. Primary-agent
billing is not exposed, so total monetary cost is unknown, not claimed as zero.
No private datasets, artifacts or credentials were sent to delegated models.

Default API support is 100k rows, local-only, one worker, synchronous HTTP request
processing. Larger opt-in narrow synthetic workloads do not certify all widths,
real models or browsers. The quota's conservative journal reserve can reject jobs
early; large offset/filter queries can be slow. Browser Blob buffering, manual
crash-temp cleanup and cooperative native-call deadlines remain documented.
Background jobs/progress/authentication/distributed services are outside this PR.
