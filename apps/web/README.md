# Web application

SvelteKit 3 / Svelte 5 / TypeScript 6, Tailwind 4, Node adapter, and shadcn-svelte. This is the browser UI for an **offline/local academic prototype**, not a public network IDS.

Run `pnpm dev` from the repository root to start the API and web application, or `pnpm dev:web` to start only the frontend. Open http://127.0.0.1:5173. The API runs on loopback port 8000 and must have a trusted operator-owned Joblib model for inference and evaluations; starting the servers does not retrain anything.

## Routes

- `/` — current-analysis overview, prediction distribution and API/model status.
- `/analyze` — upload an offline CSV and run batch flow predictions.
- `/explorer` — opens this browser’s current analysis or explains how to import a dataset.
- `/analyses/[id]` — inspect saved temporary flows, export predictions, and request local/global SHAP explanations.
- `/model-insights` — saved held-out evaluation, confusion matrix, provenance and methodology, plus separately labeled global SHAP for the current upload. These metrics are not measured accuracy on uploaded CSVs.

## Verification

Run from the root:

```bash
pnpm check
pnpm test
pnpm build
pnpm contract:check
pnpm nx e2e web --output-style=static
```

Frontend types come from `@ids/api-client`, generated from FastAPI; do not hand-maintain a second API schema. `components.json`, theme tokens, utility types and the checked-in Button form the shadcn foundation. SvelteKit 3 uses `#lib` aliases and explicit `.js`/`index.js` import paths.

See [development](../../docs/development.md), [documentation index](../../docs/README.md), and [security policy](../../SECURITY.md).

## Workspace behavior

Navigation groups Overview, Analyses, Traffic Explorer and Model Insights. The sidebar collapses to a keyboard-operated menu on mobile. System/light/dark themes use one shared token system; see [design system](../../DESIGN.md).

Local browser storage holds only `ids-current-analysis` and `ids-theme`; there is no durable analysis history. Directly opening valid results selects that analysis. Missing/expired sessions prompt re-import. Filters and pagination stay in place when opening or closing a flow inspector. Desktop inspection uses a nonmodal side drawer; mobile inspection uses a full-width native modal for keyboard containment. Escape or Close restores the row trigger’s focus. Deletion requires an inline confirmation; exporting still downloads all predictions regardless of filters.

File extension and size validation happen locally. The unchanged server performs schema validation and inference in one request. Busy text is indeterminate, never a fabricated progress percentage. Local explanations and sampled global importance remain on demand. The model page separates saved labeled evaluation from uploaded-sample SHAP.

See [redesign assessment and plan](../../docs/plans/v0.3-workspace.md) and [validation evidence](../../docs/ui-redesign-verification.md). Application/package release versions remain unchanged until a separate release is authorized.
