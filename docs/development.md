# Development workflow

Run commands from the repository root. Requirements: Python 3.11–3.13, Node
22.17+ (Node 22 LTS recommended), pnpm 11.4.0. Python 3.14 is unsupported by the
retained scientific dependency pins. Use the pinned environment to reload artifacts.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-api.txt
npm install --global pnpm@11.4.0
pnpm install --frozen-lockfile
pnpm dev
```

Web: <http://127.0.0.1:5173>. API docs: <http://127.0.0.1:8000/docs>.
The web and API start without a model or dataset. Health reports `model_available:
false`; the dashboard explains the unavailable model. Do not train merely to
start services if a trusted artifact already exists. Use the original README
scientific workflow only when training is intended.

The Nx Python launcher uses `.venv/bin/python` (`Scripts/python.exe` on Windows),
then `python` on PATH. Set `IDS_PYTHON` to use another managed environment. Direct
Python workflows have no Node dependency. API dependencies are an additive
`requirements-api.txt`; `requirements.txt` remains the v0.1 scientific environment.

## Tasks

| Command | Purpose |
| --- | --- |
| `pnpm dev` | Nx starts API and web concurrently; Ctrl-C stops both |
| `pnpm dev:web` / `pnpm nx serve web` | SvelteKit development server, strict port 5173 |
| `pnpm dev:api` / `pnpm nx serve api` | FastAPI reload server, loopback port 8000 |
| `pnpm test` | Existing Python tests, API tests, frontend client unit tests |
| `pnpm check` | Python compile checks and OpenAPI/type drift checks; Svelte diagnostics |
| `pnpm build` | SvelteKit production build with Node adapter |
| `pnpm nx run-many -t check,test,build --output-style=static` | Full verification |
| `pnpm contract:generate` | Export FastAPI OpenAPI then generate TypeScript |
| `pnpm contract:check` | Detect stale OpenAPI snapshot or generated types |
| `pnpm graph` | Interactive Nx dependency graph |
| `pnpm nx show projects` | List the four registered projects |
| `pnpm nx graph --file=/tmp/ids-graph.json` | Export graph without a browser |
| `pnpm nx run ids-core:compatibility` | Read-only trusted-model CLI/pipeline/SHAP checks |
| `pnpm nx run ids-core:dashboard` | Original Streamlit application |
| `pnpm nx run ids-core:predict -- --model models/model.joblib --data path/to/flows.csv --output reports/predictions.csv` | Existing batch prediction through Nx |
| `pnpm nx run ids-core:explain -- --model models/model.joblib` | Existing SHAP CLI through Nx |
| `pnpm nx run ids-core:train -- --data path/to/flows.csv --provenance cic-ids2017 --output-dir models/new-experiment` | Explicit training; never cached |

`ids-core` is the root project; `api`, `web`, and `api-client` use their respective
app/package directories. Web targets use pnpm workspace filters. Direct commands
such as `python -m src.predict --help` still work. Training always requires explicit
arguments; no build/check/startup task depends on training.

## Configuration

Defaults work without copying any environment files. For an alternative browser
API URL, copy `apps/web/.env.example` to `apps/web/.env` and edit
`PUBLIC_API_BASE_URL`. This URL is public, browser reachable, and accepts HTTP(S).
SvelteKit 3 declares it in `apps/web/src/env.ts` and reads it at runtime; restart
the dev server after changing environment files. In production, export it to the
Node process. The generated build can start with
`HOST=127.0.0.1 PORT=3000 node apps/web/build/index.js` (after `pnpm build`).

For the API, export variables in the launching shell:

```bash
IDS_MODEL_PATH=models/model.joblib pnpm dev:api
IDS_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173 pnpm dev:api
```

Root `.env.example` documents the settings; FastAPI does **not** automatically
load a `.env` file. Relative `IDS_MODEL_PATH` resolves from the repository root.
Use trusted server-owned Joblib files only: deserialization executes Python.
No browser flow or endpoint accepts model uploads. Never place secrets in a
`PUBLIC_*` variable. CORS is an origin allowlist, not authentication.

## Changing the API contract

1. Change Pydantic schemas/routes in `apps/api/main.py` and add API tests.
2. Run `pnpm contract:generate`; this never needs a running API or model file.
3. Update typed frontend usage and run `pnpm check`, `pnpm test`, `pnpm build`.
4. Commit both `packages/api-client/openapi.json` and `src/schema.d.ts`.

Use `/docs` for request examples. A prediction request has shape
`{"rows":[{"Flow Duration":123,"Total Fwd Packets":8}]}`; actual required
features come from `GET /model`. Every retained feature is required. JSON null
uses saved training medians. Response rows retain input order and contain only
row number, class, and DDoS probability, plus validation notes.

## Validation and troubleshooting

A clean clone runs every fixture test without CIC-IDS2017 or a saved real model.
The optional trusted-model API parity test explicitly skips when the artifact
is absent. Fixture training stays in pytest temporary directories. Never confuse
fixture scores with research results. `ids-core:compatibility` instead exits with
a clear error when its explicitly requested local model is missing.

If contract checks fail, regenerate and review the changed schema. If an API is
reachable but no model is available, inspect server logs and restore the trusted
artifact/pinned Python environment; do not upload a model through the browser.
If port 5173 is in use, stop the occupying development process or run the frontend
manually on another port and update the CORS allowlist.

Nx worker sockets and loopback servers may need permission in restricted agent
sandboxes. This is an environment restriction, not a reason to disable tests or
alter global user settings. Request the narrow required execution permission.

The full CI workflow runs on PRs/pushes with Python 3.13 and Node 22. It installs
with the pnpm lockfile and verifies all four projects without external datasets.
