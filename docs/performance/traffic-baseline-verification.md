# Traffic baseline milestone verification — 30 October 2026

## Scope and repository safety

Base: `main` at `c4d7b5797eab70f0379eb33ec0cd1f75b58aa46b`, verified against
remote HEAD before implementation. Work is isolated on
`feat/scalable-traffic-baseline` in `/private/tmp/ids-scalable-baseline`.
The original checkout's uncommitted UI/UX changes were preserved. Open UI stack
PRs #8–#11 target their own feature branches; this PR targets `main` and changes
no frontend components or generated API contracts. E2E regenerated two screenshots
inside the isolated worktree; those generated changes were discarded.

This is the explicitly allowed earliest independently useful milestone (PR 1),
not completion of streaming/storage phases B–E. It adds reproducible baseline
measurements, scientific regression foundations, and fixes a demonstrated silent
CSV truncation defect. See [methodology, results and next PR](traffic-baseline.md).

## Verification

Commands use the existing repository Python 3.13.13 environment and locked pnpm
11.4.0 dependencies in the isolated worktree. Nx targets were inspected with
`nx show projects` and `nx show project`. Resolved projects are `ids-core`, `api`,
`api-client`, `web`. `NX_DAEMON=false NX_ISOLATE_PLUGINS=false` avoids sandbox-denied
plugin sockets; no Nx/project configuration was changed.

| Check | Actual result |
| --- | --- |
| Initial focused API/CSV baseline | 48 passed |
| New inference/API/benchmark cases, focused run | 9 passed |
| CSV regressions after parser fix | 18 passed |
| `pnpm contract:check` | Passed; no schema/client drift |
| `pnpm check` | Passed (5 Nx targets) |
| `pnpm test --output-style=static` | Passed: core 47, API 65 + 1 skipped, web 17 |
| `pnpm build` | Passed |
| `pnpm nx e2e web --output-style=static` | Passed: 14 browser tests |
| Original benchmark, 1k/10k/50k × 3 | All 9 lifecycle cases completed and verified |
| Post-fix benchmark, 50k × 3 | All 3 lifecycle cases completed and verified |
| `git diff --check` | Passed |

The API skip is the existing optional trusted v0.1 artifact test; the isolated
worktree intentionally has no repository model/data. Existing synthetic test
fixtures fit tiny ephemeral models as before. Benchmarks explicitly fit one
synthetic 100-tree model outside timing and do not retrain repository artifacts.

The first full test run exposed the new late-record regression (1 failed, 44
passed in core); it was fixed and the full suite rerun successfully, with no
xfail, suppression or weakened assertion. A minimal reproduction confirmed pandas
silently dropped the third field at a later chunk boundary. Standard `csv.reader`
record-width validation now rejects it before inference. Tests also preserve
quoted commas/newlines, short rows and a valid 100,000-character metadata cell.
Oversized fields fail explicitly; the CLI compatibility change is documented.

The first E2E attempt was blocked before any browser tests because the sandbox
denied binding `127.0.0.1:8001`. The same command was rerun successfully with local
server permissions. Initial pnpm offline installation lacked some locked tarballs;
locked dependencies were fetched without lockfile changes. Existing Starlette
BlockingPortal deprecation and Node color-environment warnings remain; no checks
were disabled because of them.

## Cost and data handling

One primary Codex agent implemented and reviewed this work. OpenCode CLI was found
at `/Users/komchanv/.opencode/bin/opencode`; `opencode models` listed
`opencode/glm-5.3-flash-free` and `opencode/deepseek-v4.1-flash-free` among available
identifiers. A name/listing is not pricing evidence: pricing was not independently
verified and neither candidate was invoked. There were **no delegated model
calls** or extra AI service installations/configuration. The primary agent's
billing/cost is not exposed here; total AI spending cannot be claimed as zero.
No datasets, model artifacts, credentials or uploaded traffic were sent to other
models. Benchmarks use only newly generated synthetic data.

## Remaining work

Results and input frames remain in memory; offsets still scale by row. The API
still rejects >50,000 rows and is local-only, single-worker, ephemeral storage.
No claim is made for 100k, 500k or one million rows. PR 2 must integrate a strict
chunk iterator, frozen-model batch inference, transactional SQLite results,
bounded SQL queries/details/SHAP samples and streaming export, quota accounting,
cleanup and >50k end-to-end tests together before relaxing the row/cell ceilings.
