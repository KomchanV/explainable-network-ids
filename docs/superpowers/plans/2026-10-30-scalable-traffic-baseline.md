# Scalable traffic baseline implementation plan

**Goal:** Complete the first independently useful milestone: reproducible synthetic lifecycle measurements and regression foundations before changing production storage.

**Architecture:** Keep inference semantics, API contracts and limits unchanged; fix any demonstrated silent CSV truncation exposed by the regressions. Run each benchmark case in a fresh subprocess with one trusted, temporary synthetic model. Generate input incrementally, then measure production ingestion, queries, SHAP and export. The follow-up PR must introduce streaming inference and SQLite atomically across the entire lifecycle before lifting row/cell limits.

**Tech stack:** Existing Python virtualenv, pandas, scikit-learn, FastAPI TestClient, standard-library timing, tracemalloc and resource; existing Nx verification.

- [x] Add scientific baseline tests comparing whole-frame inference against manually partitioned inference, including missing/infinite values, duplicate rows and global row numbering. Do not add a second production inference implementation.
- [x] Add API regressions for probability ties, inclusive boundaries and failure after inference begins; assert atomic cleanup and subsequent ingestion succeeds.
- [x] Fix the demonstrated late-record truncation with an independent standard-library record-width scan, preserve quoting/short rows and document the shared CLI/API field-size bound.
- [x] Add `scripts/benchmark_traffic.py`: deterministic synthetic-only fixture, fresh process per case, fixed synthetic model trained once outside measurement, version/environment reporting, time/throughput/input/storage/export sizes, Python traced peak and separately labeled OS process peak RSS. Check export order/completeness and SHAP reconstruction.
- [x] Test benchmark output and invalid row counts with small fixtures; keep large runs opt-in.
- [x] Run 1,000, 10,000 and 50,000 row baseline cases without raising current quotas. Record raw results and methodology under `docs/performance/`.
- [x] Run contract, check, test, build and web e2e; record actual results and environmental failures.
- [ ] Inspect the focused diff, commit and open PR 1 against main without touching the existing UI stack. Describe PR 2's atomic streaming/storage requirements and remaining acceptance criteria explicitly.

User instructions authorize sequential execution without design approval pauses or additional agents. No delegated model is required for this milestone.
