# Synthetic offline traffic processing baseline

This milestone supplies the measurement harness and scientific regression foundations
for scalable traffic processing. It **does not implement streaming ingestion or
increase supported API capacity**. A regression found and fixed silent pandas field truncation at a chunk boundary
(see below). The API retains the 50,000 row ceiling until
inference, stored results, queries, export and SHAP can all operate with bounded
memory in a single integrated follow-up change.

## Reproduce

Use the supported Python environment installed from `requirements-api.txt`:

```bash
.venv/bin/python -m scripts.benchmark_traffic \
  --rows 1000 10000 50000 --repeats 3 \
  --output /tmp/traffic-baseline.json
```

Run from the repository root. This is opt-in and is not an Nx build/test target.
The command explicitly fits one ephemeral synthetic model (400 invented training
rows, seed 42, 100 trees, max depth 12, existing preprocessing, `n_jobs=-1`) outside
the measured interval. It never reads uploaded data, repository model artifacts,
or real network captures. The repository model is never modified. Temporary model,
CSV and analysis files are cleaned on success or exception.

Each size/repeat launches a fresh Python process. CSV generation writes one row at
a time: six numeric features, ignored `Label`, recurring empty/infinite values,
and repeated flows. Numeric values repeat with period 97 and missingness with
periods 31/47; synthetic feature distributions deliberately do not model real
traffic. File row count does not affect input-generation memory. These results
measure software behavior, not scientific accuracy or production capacity.

The measured path is:

1. `AnalysisStore.create`: actual preflight, CSV loading, validation, inference,
   feature storage and summary creation, using the saved model.
2. Existing HTTP routes through in-process TestClient: sorted/filtered pagination,
   exact row lookup, last-row feature detail, local SHAP and global SHAP (50 rows).
3. Full CSV export through its existing route.

Every case checks total rows, all exported row numbers/order/completeness, successful
SHAP reconstruction through the production safeguards, and deletion cleanup.
The full export digest is recorded for later same-environment parity checks.

HTTP upload buffering, byte-limit checks and socket transport are **excluded**:
input is opened directly and passed to the store. TestClient does not simulate
real client/network backpressure. The harness is a backend lifecycle baseline,
not a full HTTP upload or streamed-export memory benchmark. Existing API tests
cover upload rejection, ingestion exclusion, expiry, deletion and error cleanup.

## Reading the metrics

- `stage_seconds.ingestion`: includes preflight and feature-file writes.
- `rows_per_second`: rows / ingestion time. `total_seconds` additionally includes
  queries, local/global SHAP, export and small correctness assertions.
- Timing includes `tracemalloc` overhead. First local SHAP includes lazy SHAP
  imports/JIT; global SHAP follows local and benefits from initialization.
  Startup imports, model fitting/loading and CSV generation precede the timer.
- `python_peak_bytes`: peak Python traced allocations across all timed stages,
  starting after setup and garbage collection. It is not total process memory;
  native libraries, allocator retention and worker threads can be invisible.
- `process_peak_rss_bytes`: OS **lifetime** process high-water RSS from `resource`,
  in bytes (macOS reports bytes; Linux reports KiB, converted). It includes model
  loading and startup before timing. `process_peak_rss_before_bytes` is the
  lifetime high-water mark just before timing. Their difference is **not** peak
  incremental memory. The worker is fresh for every case; RSS is not polled.
- `storage_bytes`: completed analysis files only. Input CSV/model bytes and
  in-memory predictions/offsets are excluded. `export_bytes` measures response size.
- `input_bytes`: actual generated CSV size. Environment/package versions, revision,
  dirty-worktree flag and thread-related environment variables are recorded.

The harness currently supports macOS/Linux (`resource` is Unix-specific). Do not
compare timing as an optimization claim without rerunning both revisions under
the same hardware, dependencies, model, data generator and tracing settings.

## Current production constraints and bottlenecks

Revalidated at `c4d7b5797eab70f0379eb33ec0cd1f75b58aa46b`:

| Stage | Current behavior | Scaling implication |
| --- | --- | --- |
| Upload/preflight | 200 MiB upload, 50,000 rows, 256 columns, 5,000,000 cells; one ingestion lock | Limits protect the existing memory-heavy implementation |
| CSV reader | NUL scan, pandas 50,000-row chunks collected into a list, concatenated DataFrame (before the new record-width validation) | Full dataset stays in memory; chunking alone does not bound memory |
| Inference | Authoritative `predict_batch` validates, then model probability/class inference; row numbering restarts at 1 per call | Future chunks must offset rows globally and sum imputation counts |
| Feature storage | Required numeric features validated again, JSONL file plus Python offset per row | Disk data bounded by quota, offsets still grow in RAM |
| Predictions | Per-session DataFrame | Memory grows with rows and retained sessions |
| Queries | DataFrame masks and sorting before pagination | Work/temporary memory depends on full result count |
| Export | Whole DataFrame serialized to a CSV string | Full export materialized in memory |
| SHAP | Seeded bounded sample or one row, snapshot copies under lock | Explanation calculation is bounded, but relies on full offsets/prediction store |

Five sessions, 512 MiB aggregate **feature-file** budget and one-hour TTL remain.
The 512 MiB budget does not cover upload temporary files (up to another 200 MiB),
RAM, artifacts, export strings or filesystem overhead. Sessions are process-local,
ephemeral and removed on expiry/delete/shutdown. No new limits or authentication
are introduced. Bind locally (`127.0.0.1`), use one worker and trusted operator-owned
artifacts; this milestone does not authorize public deployment.

## Regression foundations

Added tests compare whole-frame and manually partitioned `predict_batch` outputs
exactly, including probabilities, row offsets, ignored-column notes, imputation
counts, duplicate rows, missing/infinite cells, and unchanged learned medians.
They describe the oracle for future chunk integration; they do not assert that
the current API streams. Additional tests cover deterministic probability ties
across pages, inclusive probability boundaries, sanitized inference failures,
atomic cleanup and reuse of the ingestion slot. Narrow parser fixtures cross the
existing 50,000-row chunk boundary and reject a malformed final record/over-limit
input without returning a partial DataFrame.

The late-malformed-record test exposed a pre-existing pandas 2.2.3 C-parser defect:
`x,y` followed by 50,000 valid records then `3,4,5` silently drops the third field
in the final record even with `on_bad_lines='error'`, `index_col=False`, and parser
warnings promoted to errors. The loader now scans record widths using standard
`csv.reader` before pandas, retaining one record at a time and rejecting extra
fields before inference. This adds a complete structural scan; model/float parsing
still uses the existing pandas settings. Quoted commas/newlines and short rows
retain their existing behavior and are covered by tests.

Compatibility note: the shared reader now applies Python's `csv.field_size_limit()`
to data fields too (default 131,072 characters), matching the API's existing
preflight field limit. CLI files with larger individual fields that were previously
accepted by pandas now fail explicitly. The API's supported field sizes do not
change. This finite parser bound is intentional; the follow-up iterator should
preserve or explicitly configure it rather than silently changing a global csv
setting. No classifier, preprocessing or artifact changes are made.

Small benchmark smoke tests use the existing fitted test fixture and nine rows;
large benchmark cases are never part of ordinary CI. Existing synthetic unit-test
fixtures still fit small models as before; no main model is retrained.

## Next integrated PR

Introduce a reusable strict chunk iterator while retaining `read_csv` compatibility
for training/CLI callers. Keep feature normalization, known duplicate-header
exception, nonnumeric rejection, order, duplicate rows, frozen imputation and
probability/class semantics. Preserve late-error atomicity and cumulative metadata.

Use standard-library SQLite for numeric features and predictions, global one-based
row keys, SQL filtering/count/sorting with the existing row-number tie break,
bounded detail/sample retrieval and incremental export. Remove in-memory offsets
and prediction accumulation together. Publish a session only after the complete
transaction succeeds; budget database/index/journal and upload temporary bytes,
retain session count/TTL/concurrency limits and clean partial failures.

Only then reconfigure row/cell limits with a documented bounded batch size and
resource quotas, verify >50,000 rows end to end including upload and export,
reconstruct stored probabilities via SHAP, and rerun the baseline. Add opt-in
100k/500k/1M checkpoints. No capacity claim at those sizes is made here. Preserve
OpenAPI and frontend behavior wherever possible; regenerate the contract only
when necessary. Redis, Celery and distributed infrastructure remain out of scope.

## Recorded results (30 October 2026)

Environment: Apple M2 (Mac14,2), 8 logical CPUs, 8 GiB physical RAM, macOS 27.2 arm64, Python 3.13.13. NumPy 2.2.6, pandas 2.2.3, scikit-learn 1.6.1, SHAP 0.48.0, FastAPI 0.121.0, HTTPX 0.28.1. Thread environment variables were unset; the existing forest uses `n_jobs=-1`. Hardware details came from local `sysctl`.

[Raw measurements](traffic-baseline-2026-10-30.json) contain all nine cases. These are pre-fix baseline measurements: production code was at the revision above, before record-width validation; the harness/tests/docs were uncommitted while measured (`working_tree_dirty=true`). No other tests/builds ran concurrently with the benchmark. Values below are medians of three fresh-process cases per size; MiB means 1,048,576 bytes.

| Rows | Ingestion s | Total lifecycle s | Ingestion rows/s | Python traced peak MiB | OS lifetime peak RSS MiB |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1,000 | 0.150 | 19.036 | 6,666 | 39.79 | 218.66 |
| 10,000 | 0.705 | 19.853 | 14,190 | 42.20 | 226.72 |
| 50,000 | 3.277 | 23.666 | 15,256 | 51.69 | 236.30 |

| Rows | Input bytes | Stored feature bytes | Export bytes |
| ---: | ---: | ---: | ---: |
| 1,000 | 49,200 | 149,245 | 14,365 |
| 10,000 | 491,890 | 1,493,286 | 153,105 |
| 50,000 | 2,459,187 | 7,466,594 | 809,702 |

All nine cases completed, exported the requested row count in order, passed production SHAP reconstruction (maximum absolute error 9.99e-16) and deleted their analyses. Cold local SHAP dominates total time at these sizes. The six-feature synthetic CSV is much narrower and smaller than many CIC-IDS2017 uploads. These results establish a baseline only; they demonstrate neither an optimization nor bounded-memory scaling beyond current limits. Byte-level export hashes are supplemental diagnostics; future multi-threaded forest aggregation should be compared with the existing numerical tolerances, not hash equality alone.

### After record-width validation

[Post-fix raw measurements](traffic-parser-validation-2026-10-30.json) repeat the
50,000-row case three times on the same environment and synthetic model settings,
with no other tests/builds running concurrently. Median ingestion was 3.444 s
(14,518 rows/s), total lifecycle 21.644 s,
Python traced peak 51.69 MiB and OS lifetime peak
RSS 314.36 MiB. Input/storage/export sizes
remain unchanged. All three cases passed row-count/order, SHAP and deletion checks.

The added validation scan prioritizes rejecting malformed inputs. These short
local runs are descriptive; scheduler/cache/thermal variation prevents attributing
all timing differences to the scan. No performance improvement is claimed.
