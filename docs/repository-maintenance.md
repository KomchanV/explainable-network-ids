# Repository maintenance

## Source of truth and layout

- `main` is the default integration branch. Protect it with PR review and CI rules through GitHub repository settings when available.
- `apps/web` owns browser UI and E2E tests; `apps/api` owns HTTP/session adapters; `src` and `tests` own the original Python ML engine and tests.
- `packages/api-client` contains generated API types. Regenerate from FastAPI; do not hand-edit generated schemas.
- `packages/ids-core` is a future packaging boundary, not a second Python implementation.
- `data/raw`, `models`, and `reports` contain ignored local data/artifacts. Preserve their `.gitkeep` placeholders.

## Branches

Use short-lived branches from the **latest `main`**:

- `feat/<area>` for new functionality;
- `fix/<issue>` for corrections;
- `docs/<topic>` and `chore/<topic>` for documentation and maintenance;
- `release/<version>` only for release preparation.

Always create a PR and wait for successful checks on the latest head before merge. The previously used `release/0.1-alpha` and older `feat/v0.2-*` branches are historical references; a merged branch is not an independent source of truth.

**Branch-cleanup policy:** Review whether a branch is merged and whether it is needed for reproducibility before deleting it. Do not delete `release/0.1-alpha` or a historical tag as part of ordinary housekeeping. Removing merged feature branches is optional and requires an explicit decision by the maintainer; deleting a branch is not required for a tidy codebase.

Git tags `v0.1.0-alpha.1` and `v0.2.0-alpha.1` must never be moved or overwritten. Treat published release notes and annotated tags as historical evidence.

## Release workflow

The `v0.2.0-alpha.1` release was published by a version-specific, one-shot GitHub Actions workflow. That automation is intentionally removed from the active workflow directory after publication to prevent a repeat invocation from failing on an existing tag. It remains discoverable in the tagged historical source.

Future releases should use a dedicated reviewable release PR and should:

1. Verify the current default branch, version and documentation.
2. Run `pnpm install --frozen-lockfile`, `pnpm check`, `pnpm test`, `pnpm build`, `pnpm contract:check`, and `pnpm nx e2e web`.
3. When the local **trusted** model artifact is present, run `pnpm nx run ids-core:compatibility` read-only. This cannot be assumed to run in hosted CI, which uses synthetic fixtures.
4. Merge release preparation after required reviews and passing CI; verify the resulting main commit's checks.
5. Create a **new** annotated version tag pointing to that tested main commit, and publish a pre-release with matching versioned release notes. Never replace a published tag.
6. Verify tag target, release URL, pre-release flag, and expected assets (normally source only).

Do not automatically re-use the v0.2 one-shot publishing workflow for future tags. An explicit release-publishing workflow should be proposed and reviewed separately from unrelated changes.

## Documentation lifecycle

- Keep current usage instructions in `README.md`, `docs/development.md`, `docs/architecture.md`, `docs/traffic-analysis.md`, and `docs/model-insights.md`.
- Put version-specific release notes at the repository root and record changes in `CHANGELOG.md`.
- Preserve dated verification reports and historical plans; if they become outdated, add clarifying context in current docs instead of rewriting previous test evidence.
- Update [docs/README.md](README.md) when adding important documentation.

## Safety constraints

Do not commit source datasets, trained Joblib models, generated predictions, secrets, or environment files. Loading Joblib is restricted to trusted operator-owned artifacts; pickle deserialization can execute code. Keep FastAPI and the web server local-only. CORS is not authentication. Do not imply test-fixture or same-capture held-out scores demonstrate unseen-network security performance. For policy and reporting, see [SECURITY.md](../SECURITY.md).
