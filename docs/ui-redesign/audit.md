# Repository and UX audit (read-only)

## Verified product truth
- Nx workspace: SvelteKit 5 frontend `apps/web`, FastAPI `apps/api`, Python engine at root / `src`, generated API contract `packages/api-client`.
- Real routes only: `/` overview, `/analyze` CSV import/inference, `/explorer` current-analysis redirect/empty state, `/analyses/[id]` flow exploration, `/model-insights` saved evaluation plus uploaded-dataset global explanations.
- No live monitoring, persistent analysis history, alert/event management, severity levels, settings service, or incident disposition workflow. Do not expose these as functional features.
- Only BENIGN and DDoS predictions. P(DDoS) is uncalibrated class-1 model probability, not confidence or threat severity. SHAP local/global outputs must remain class-1 explanations with actual numeric contributions and reconstruction checks.
- Analyses are temporary; browser remembers a single ID. Expired/missing analysis status 404/410 requires reimport. Metadata is not retained, only numeric inputs. CSV limits: 200MB, 50k data rows, 256 columns, 5m cells.
- APIs support upload, summary, filter/paginate/sort flows, flow detail, local/global explanation, export all predictions, delete analysis. Global sample size is 1–100 and deterministic. Model evaluation independent of uploaded data.

## Concise UX audit
- P1 hierarchy: Overview no-current state is a large prose panel; import is the core first action but first viewport gives similar weight to service detail and workflow instructions. Reframe around a clear first-use launch area plus compact actual service status.
- P2 IA: Analyses is an import screen rather than a history. Keep route compatibility but label import capability clearly in page title/help. Current analysis is a single ephemeral workspace, not history.
- P2 density: Explorer repeats four metric cards, distribution card, filename, provenance, scientific caveat, 9-control filter grid, export/delete controls before the results. This delays the primary investigation table. Compact summary, group filters by task, separate destructive action from export.
- P2 explainability order: Model Insights puts saved model metadata and long evaluation/provenance sections before current-data SHAP. Distinguish uploaded-data explanation from saved evaluation prominently, with useful section navigation/disclosure.
- P2 visual structure: Generic equal bordered cards flatten priority. Introduce coherent shell, stronger page-level hierarchy, compact metric strip, readable section boundaries, and tailored upload/inspection surfaces.
- P2 missing edge action: Empty filter result says no matches but does not offer inline clear-filters action. Error retry exists on explorer and evaluation refresh, but import service failure only raw error text.
- P2 accessible scrolling: Horizontally scrolling tables use overflow containers without keyboard tabindex/accessible region names in some locations. Ensure keyboard users can scroll table/waterfall overflow.
- P3 semantic destructive action: Confirm deletion currently primary blue; use destructive token for confirmed deletion, retaining explicit confirmation.
- Positive baseline: Native form controls, explicit labels, focus outlines, skip link, current navigation state, responsive disclosure menu, native dialog with focus restoration and mobile modality, request-version handling, honest scientific limitations, robust upload error feedback and real loading states already exist.

## Verification
- `pnpm exec nx show project web --json` for resolved targets.
- `pnpm nx check web` Svelte/TS.
- `pnpm nx test web` frontend unit tests.
- `pnpm nx build web` production build.
- `pnpm nx e2e web` workflow suite (launches synthetic FastAPI server on 8001 and Vite on 5174, deterministic CSV fixture; explicitly test data only).
- Existing e2e checks theme persistence, semantic color token contrast >=4.5, input boundaries >=3, mobile overflow, keyboard nav, drawer focus/Escape, import, filter/sort, export/delete, SHAP additive data, global sample size, evaluation metrics, and expiration.
- Existing e2e screenshot paths overwrite `docs/screenshots/v0.3-*`; preserve before captures elsewhere before running suite if required.
- No lint/formatter script is declared in root or web package. Report this rather than inventing passed lint check.
- Frontend tests select several exact user-facing labels: navigation Analyses, Start with a saved flow dataset, Drop a flow CSV, API connected · Trusted model available, Current analysis, etc. Update selectors deliberately if changing wording.
