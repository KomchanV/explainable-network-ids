# Scalable traffic integration implementation plan

**Goal:** Integrate strict chunks, frozen-model inference, SQLite results, bounded queries/SHAP/export and quotas; verify 100k end to end before enabling the new default limit.

**Architecture:** A temporary SQLite file per completed analysis. Batch transactions remain invisible until publication in the process-local session registry. Store only numeric feature arrays and prediction rows. Export leases keep deleted/expired files quota-accounted until their last reader closes. One ingestion, bounded SQLite cache and export batches; no workers/services added.

**Execution:** Main agent, sequential implementation using existing PR #13 foundations (CI green, still open). The feature branch contains #13, targets main and explicitly depends on it. No merge into main is authorized or needed.

- [x] Add failing iterator and integrated disk lifecycle/batch tests; run focused pytest.
- [x] Extract `iter_csv_chunks` in `src/data_loader.py`; keep `read_csv` compatibility wrapper and strict pre-scan rules.
- [x] Add SQLite connection/export primitives in `apps/api/result_storage.py`; bound cache, journal/disk growth, row retrieval and export chunks.
- [x] Update `apps/api/analyses.py` for atomic batch creation, cumulative metadata, SQL pagination/detail, configurable finite quotas/deadlines and export leases.
- [x] Update `apps/api/explanations.py` to fetch only bounded deterministic sample row keys; preserve reconstruction checks.
- [x] Run regression suite including failure, concurrent ingestion, quota, expiry/export overlap and exact parity. Verify >50k with test overrides before changing defaults.
- [x] Extend existing benchmark for optional HTTP upload, ingestion allocation peak and bounded export consumption. Run 50k comparison, 100k end to end, then 500k/1M only if quota/time permits.
- [x] Enable verified 100k default rows/cell limits and update only necessary frontend limit text and technical docs.
- [x] Run contract/check/test/build/e2e; self-review diff, document actual results, commit/push and create PR targeting main. No auto-merge, release or tag.
