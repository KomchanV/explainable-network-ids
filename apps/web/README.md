# Web application

SvelteKit 3 / Svelte 5 / TypeScript 6, Tailwind 4, Node adapter, and shadcn-svelte. This is the browser UI for an **offline/local academic prototype**, not a public network IDS.

Run `pnpm dev` from the repository root to start the API and web application, or `pnpm dev:web` to start only the frontend. Open http://127.0.0.1:5173. The API runs on loopback port 8000 and must have a trusted operator-owned Joblib model for inference and evaluations; starting the servers does not retrain anything.

## Routes

- `/` — dashboard with live API/model status.
- `/analyze` — upload an offline CSV and run batch flow predictions.
- `/analyses/[id]` — inspect saved temporary flows, export predictions, and request local/global SHAP explanations.
- `/model-insights` — saved held-out evaluation, confusion matrix, provenance and methodology. These metrics are not measured accuracy on uploaded CSVs.

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
