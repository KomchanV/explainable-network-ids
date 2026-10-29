# v0.2 migration and compatibility record

Verified on 30 October 2026 (Asia/Bangkok) on branch `feat/v0.2-nx-monorepo`,
starting from v0.1 commit `c2b4165` (`release/0.1-alpha`). No release tag,
remote push, merge, publication, or real-model retraining is part of this work.

## Investigation and strategy

The initial tree contained root `src`, `app.py`, Python tests, experiment scripts,
local data/model/report directories, and scientific documentation. The working
tree was clean. The baseline suite passed **39 tests in 21.72 s**. This count
includes follow-up v0.1 tests beyond the older 37-test release documentation.

The sklearn pipeline contains `NumericFeatures`, a median imputer, and the existing
Random Forest. The format-1 Joblib bundle stores the pipeline, schema, labels,
metrics, metadata/provenance, and held-out explanation sample. SHAP uses the
existing positive-class extraction and explicit probability reconstruction check.
These contracts and CLI entry points were preserved without edits to root `src`,
`app.py`, or `requirements.txt`. Historical release notes and experiment results
were preserved.

The migration adds orchestration and adapters around this implementation. The
engine is a root Nx project so affected analysis covers Python source, tests,
and experiment scripts. Moving all ML code to `packages/ids-core` was rejected
because it would break serialized custom-class module references without a
separate compatibility mechanism. That directory currently documents the future
packaging boundary only.

## Verification

| Check | Observed result |
| --- | --- |
| Baseline `.venv/bin/python -m pytest -q` | 39 passed |
| Existing suite through Nx | 39 passed |
| API suite through Nx | 7 passed, including optional trusted-artifact parity |
| Frontend Vitest suite | 4 passed: configured URL, structured errors, proxy/network errors, invalid URL |
| Svelte/TypeScript check | 0 errors, 0 warnings |
| Frontend build | Passed; SvelteKit Node adapter output in `apps/web/build` |
| OpenAPI snapshot and TypeScript drift checks | Passed against FastAPI source |
| `pnpm peers check` | No peer dependency issues |
| Python `pip check` | No broken requirements |
| Fresh dependency-tree `pnpm install --frozen-lockfile` | Passed from lockfile |
| Nx frontend cache | Repeated `web:test` returned a verified cache hit |
| Nx project listing | `ids-core`, `api`, `api-client`, `web` |
| Nx affected source/test checks | `src/preprocess.py` and `tests/test_workflow.py` each affect all four projects |
| Concurrent Nx serve | Uvicorn on 8000 and SvelteKit on 5173 both started |
| Native Brave smoke check | Real API connected, trusted metadata rendered, refresh worked; layout inspected |
| Legacy CLI help and argument forwarding | Training, prediction, explanation help passed; Nx prediction forwarding checked |
| Trusted-model prediction CLI | Passed on saved held-out sample without fitting |
| Trusted-model SHAP | 100 flows passed probability reconstruction |

Commands for repeating checks are in [development.md](development.md).
The local browser smoke check observed `cic-ids2017` provenance, 66 retained
features, 177,032 training rows, and 44,258 held-out rows, matching the loaded
bundle. These are existing model metadata, not newly generated experiment results.

The in-app browser host was unavailable, so the actual browser smoke test used
native Brave through Computer Use. Desktop rendering/refresh was inspected;
automated browser regression coverage and a mobile-browser matrix remain future work.
The new GitHub Actions workflow is checked in but has not been executed remotely.

## Artifact parity evidence

Trusted `models/model.joblib` SHA-256 before and after:

```text
28574587cb16f236b86c874c30251b13772abe3eba013c8adaa14aba65744972
```

A pre-migration baseline captured the existing engine's predictions on all 100
saved held-out flows. Labels and row numbering matched exactly after migration.
Probabilities matched at absolute tolerance `1e-12` (zero relative tolerance).
This tolerance accommodates the original `n_jobs=-1` Random Forest's parallel
floating-point summation; an initial exact-equality API assertion found a roughly
`2e-16` difference between repeated inference calls. The classifier, scientific
configuration, and results were not changed to satisfy this test.

The read-only verification script compared wrapper output to the fitted pipeline,
ran the original prediction CLI on the same saved sample, reloaded the trusted
bundle, verified the custom transformer's module remains `src.preprocess`, and
checked global/local-compatible SHAP additivity on the 100-row sample. Maximum
observed reconstruction error was **5.551115123125783e-16**. The artifact bytes
were unchanged. The local pre-migration baseline is temporary verification data,
not a committed dataset or new scientific result.

```bash
pnpm nx run ids-core:compatibility
# Optional comparison when a separately saved baseline is available:
python -m scripts.verify_migration --baseline /path/to/pre-migration-baseline.json
```

The default compatibility command validates the current trusted bundle, CLI parity,
and SHAP without retraining; it cannot reconstruct an unavailable historical
baseline. Existing fixture tests still train tiny models in temporary directories.
No production artifact or real dataset was overwritten.

## Resolved migration issues

- Root engine project registration fixed Nx affected analysis for files left at
  legacy paths. A project configuration under a placeholder package directory
  did not attribute root source changes to the engine.
- SvelteKit 3's environment exports and explicit package import paths were used,
  rather than deprecated v2 patterns. Its TypeScript 6 requirement is isolated
  from `openapi-typescript`'s TypeScript 5 requirement. Peer checks pass.
- A stale initial sandbox-blocked package installation retried after an approved
  install and left broken generated package links. It was allowed to end, the
  generated dependency directories were preserved in a temporary backup, and a
  fresh frozen-lockfile installation restored them. No source workaround was added.
- Nx worker sockets and local network checks required sandbox execution permission;
  no global security settings were modified.

## Limits and next UI work

This is an offline academic foundation. The new web application exposes health
and model metadata. Prediction is available as bounded JSON inference through
the API; CSV upload, traffic/flow pages, charts, and HTTP SHAP endpoints are not
implemented in this migration. The existing CLI and Streamlit retain these
scientific workflows. The API loads a model once per worker; operators must
restart it after replacing a trusted artifact.

No external-generalization experiments, scientific result updates, full-dataset
retraining, or new performance benchmarks were run. All migration fixture tests
and the available trusted-model checks ran locally; none were blocked by missing
local datasets or model artifacts. On clean clones the optional trusted-model
parity test skips explicitly, while fixture-based API prediction remains tested.
One upstream Starlette/AnyIO test-client deprecation warning remains; it does not
change results. Nx may also print environment color-variable warnings.

For the next v0.2 increment, implement CSV upload/schema feedback and Flow Explorer
against the existing inference semantics, then build selected-flow/global SHAP
views with probability units and provenance intact. Add automated browser tests
for connected/offline/model-unavailable states and responsive layouts as these
user flows expand. Define bounded explanation requests before exposing SHAP over
HTTP. Keep the academic limitations visible and retain the original artifact
loading contract until a separately verified packaging migration is justified.
