# v0.2 architecture

The system remains an offline academic BENIGN/DDoS classifier. The migration
adds a web application and an HTTP adapter around the existing fitted pipeline.
No database, packet capture, streaming service, or model retraining is introduced.

```text
apps/web (SvelteKit 3, Svelte 5, Tailwind 4, shadcn-svelte)
    | imports generated TypeScript contract
packages/api-client (OpenAPI JSON + generated schema.d.ts)
    | generated from
apps/api (FastAPI + Pydantic)
    | calls existing Python functions
src (ids-core: preprocessing, training, prediction, evaluation, SHAP)
    | loads trusted operator-owned artifacts
models/ (format version 1 Joblib bundle; ignored)
```

Nx project dependencies are `web -> api-client -> api -> ids-core`. The
`api-client -> api` edge is a schema-generation dependency, not a Node runtime
import of Python. Runtime HTTP requests go directly from the browser to FastAPI.
Nx has no role inside Python inference or SHAP computation.

## Engine boundary and serialization

`ids-core` is registered in root `project.json`, with `sourceRoot: src`. It owns
root Python source, tests, scripts, and the legacy Streamlit entry point. Its
root location ensures Nx affected analysis attributes changes in these files to
the engine. `packages/ids-core/README.md` documents the future packaging boundary;
it is not a second Python distribution or a copy of the implementation.

The Python package remains `src`, including `src.preprocess.NumericFeatures`.
Joblib/Pickle resolves class module names during deserialization. Moving this
class would break trusted v0.1 artifacts even if its implementation stayed the
same. No aliases, wrappers, pipeline changes, new feature transforms, or model
conversions are needed for this migration. Packaging the engine later requires
an explicit artifact compatibility plan and fixture-based verification first.

The format-1 bundle retains the fitted pipeline, feature schema, label mapping,
metrics, provenance metadata, and held-out explanation sample. The original
Python dependency pins remain unchanged. Existing CLI and Streamlit workflows
continue to run from the repository root without pnpm or Nx installed.

## HTTP adapter

`apps/api/main.py` owns configuration, Pydantic schemas, lifespan loading, CORS,
logging, and route/error adapters. At startup each worker loads the configured
trusted artifact using `src.predict.load_artifact`. Missing or invalid models
leave the service live; dependent endpoints return 503. Restart the service to
load a different model. Health is liveness and reports model availability
separately; it is not evidence of scientific model quality.

- `GET /health`: service version and model availability, always independent of model readiness.
- `GET /model`: saved schema, label mapping, classifier, training row counts, seed, dataset identity/provenance.
- `POST /predict`: 1–1,000 JSON feature rows; delegates schema validation,
  median imputation, class prediction, probabilities, row numbering, and notes
  to `src.predict.predict_batch`.
- `/openapi.json`, `/docs`, `/redoc`: generated contract and interactive documentation.

Flow values may be numeric, numeric strings, or JSON null. JSON nonfinite numbers
are invalid; numeric strings follow existing engine validation. Extra columns
are ignored and reported by the engine. No request can set a model path or upload
a Joblib file. Artifact paths are trusted operator configuration only. Request
validation uses a generic error without echoing raw flow values; expected feature
errors retain the engine's actionable message. Error bodies use
`{"error":{"code":"...","message":"..."}}`. Unexpected exceptions are logged
server-side and return a generic 500. JSON `/predict` flows are not persisted. CSV analysis retains bounded temporary
model features and predictions as described below; raw flow values are not logged.

CPU-bound inference uses synchronous FastAPI routes and its worker thread pool.
Training and explanations remain existing CLI/Streamlit capabilities; exposing
long-running ML jobs over HTTP is deferred. The API does not implement authentication,
rate limiting, deployment hardening, or a production ingestion system. Local
servers bind to loopback and CORS allows only the two documented development origins.

## Web and contract

The SvelteKit dashboard fetches health and saved-model metadata after mounting.
It has connection/loading errors, an unavailable-model state, and a refresh action.
Traffic Analysis links to `/analyze`; successful uploads link to `/analyses/[id]`.
SHAP and Model Insights remain planned labels.
The reusable layout and checked-in shadcn Button support subsequent UI work.
No fabricated traffic counters or new experimental metrics are displayed.

Pydantic models generate OpenAPI, exported without starting the API lifespan.
`openapi-typescript` generates the checked-in types consumed through the pnpm
`@ids/api-client` workspace dependency. `pnpm contract:check` detects drift in
both the OpenAPI snapshot and generated TypeScript. There is no duplicate
hand-maintained response interface. The small HTTP wrapper handles transport,
timeouts, and the generated error envelope; generated types provide compile-time
checks, not runtime validation of an arbitrary external server.

The official Svelte CLI scaffold currently uses SvelteKit 3, Vite 8, and TypeScript 6.
The OpenAPI generator supports TypeScript 5, isolated in its own package. Both
versions are intentional and `pnpm peers check` verifies compatibility. SvelteKit
uses `#lib` imports and explicit `src/env.ts` public environment configuration.

## Orchestration and cache policy

Nx uses explicit native `nx:run-commands` targets around each ecosystem's supported
commands. No community Python/Svelte plugin is required. Package-manager workspace
links expose the generated contract; explicit dependencies describe the Python and
schema boundaries. This provides predictable orchestration without coupling the
ML runtime to JavaScript tooling.

Web check/test/build targets are cacheable with project/dependency inputs, the
lockfile, root configuration, runtime Node/pnpm versions, and the public URL shell
variable. SvelteKit's URL is a dynamic runtime variable, not a baked-in secret.
Python checks/tests, API tests, OpenAPI generation/drift checks, inference,
compatibility checks, training, and servers are uncached. Tests may inspect ignored
local artifacts; training and prediction depend on mutable datasets and models.
Do not enable caching for these tasks without declaring every external input,
environment version, and generated output. There is no remote cache configured.


## CSV analysis resources

`apps/api/analyses.py` owns the resource schemas, router and process-local store.
A raw `text/csv` upload is streamed to an anonymous temporary file with a 200 MiB
byte limit and five-minute deadline. A nonblocking ingestion lock bounds parsing
and inference to one batch; `run_in_threadpool` keeps CPU work off the event loop.
A bounded shape preflight checks columns/cells/record size, then the unchanged
engine `read_csv(max_rows=50000)`, `predict_batch` and `validate_features` provide
all scientific semantics. There is no preprocessing implementation in the adapter.

Result dataframes stay in memory. Only validated numeric model features are
serialized to JSONL on disk with offsets for single-row reads; ignored values
are discarded. A store lock coordinates retrieval/deletion/expiry and stable
filtering/sorting/pagination. No retrieval or export runs inference again. Model
identity is the SHA-256 of the trusted configured artifact. Five-session, disk,
row/cell and TTL limits bound the local lifecycle. An async sweeper performs
periodic expiry; graceful lifespan shutdown removes the process directory.
See [API and lifecycle details](traffic-analysis.md), including crash leftovers
and the single-worker/no-auth limitations. No database or job infrastructure was
introduced.

SvelteKit `/analyze` handles file selection/drop, validation, availability and
busy/error/success feedback. `/analyses/[id]` fetches a summary, one result page,
and selected-flow details separately. The shared `createApi` handles structured
errors, longer upload timeouts, Blob export and generated-schema types.
`AnalysisSummary.svelte` is shared by upload, explorer and dashboard; browser local
storage contains only the current analysis ID. OpenAPI includes raw CSV upload
and CSV export formats and remains synchronized through the original Nx targets.
