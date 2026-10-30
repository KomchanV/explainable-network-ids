# Scalable traffic processing integration — PR 2

## Repository and architecture

Remote main was `c4d7b5797eab70f0379eb33ec0cd1f75b58aa46b`. PR #13 was still open;
its head `961dfa01c2ddf7781c93fa74343205c1ebde332a` had two successful GitHub
Monorepo checks. Its focused loader/test/benchmark changes were reviewed and
fast-forwarded into the isolated `feat/scalable-traffic-processing` branch. No
merge into main or changes to UI stack PRs #8–#11 were made. PR 2 depends on #13;
until #13 merges, its commits also appear in the main-targeted PR diff.

`iter_csv_chunks` reuses strict UTF-8/BOM/header/CIC duplicate-field/NUL/record-width
validation from #13. It yields at most `batch_rows` (default 10,000) without
concatenation. API preflight retains row/column/cell/physical-line/header limits.
Multiple bounded scans prioritize reliable rejection over single-pass throughput.
`read_csv` remains a whole-frame compatibility wrapper for training/CLI callers;
only the API analysis path is made memory-bounded by this integration.

Each batch calls the unchanged authoritative `predict_batch` and `validate_features`
with the trusted saved pipeline. No per-batch refitting occurs. The writer assigns
global sequential one-based row keys, aggregates class/imputation counts and
ignored-column notes, then releases the batch. Required numeric features are JSON
arrays in schema order, nonfinite/missing values stored as null; ignored values,
labels, IPs and raw payloads are not persisted. The fixed-size session registry
holds summary/schema/path/deadline only, with no prediction DataFrame or offsets.

A staging SQLite file commits one batch at a time but is never registered as a
session until processing succeeds. SQLite/OS/validation/deadline failures discard
the partial file and journal. Three indexes support both probability directions
with ascending row-number tie breaks, plus class/range counts. SQL values bind as
parameters; sort syntax derives only from enums. Matching index scans avoid
full-result temp sorts; row-key order uses a table/rowid scan. Pagination fetches
at most 100 rows. Deep offsets, sparse filters and counts can still be linear work.

Local/global SHAP reads only the requested row or seeded sample (at most 100),
with existing feature ordering, baseline, model checks and reconstruction tolerance.
An explanation snapshot remains a bounded owned copy; existing deletion/expiry
race behavior is preserved. No eager SHAP across uploads is introduced.

Export returns a StreamingResponse with 1,000-row CSV chunks. A read lease pins
the immutable result file until response completion/disconnect/error/deadline,
including deletion/expiry overlap. Deleted/expired analyses disappear from new
requests immediately, while retained files remain in disk accounting. Export
failure aborts the response, never silently declares a shortened CSV complete.
The browser still downloads a Blob and can buffer the response client-side.

## Resource behavior and security

See [operator limits](../traffic-analysis.md#session-lifecycle-and-limits) for all
positive-integer environment settings. Defaults are 100k rows, 25.6M cells, 256
columns, 200 MiB upload, 512 MiB aggregate temporary disk, five sessions, one
ingestion, two exports, one-hour TTL, 300-second upload/export and 600-second
cooperative processing deadlines. A processing deadline cannot preempt a native
model call; it is checked between scans/batches and after inference. SQLite
connections use a 2 MiB page cache, disabled mmap and matching order indexes.

Disk accounting includes the unlinked upload TemporaryFile, completed/retained
SQLite files and staging files/journals. Before database creation, the writer
limits SQLite pages to one third of remaining budget after a 64 KiB allowance,
reserving conservative rollback-journal/header space. This intentionally rejects
some jobs whose final database would fit. It is not an OS-level quota, does not
cover filesystem metadata, model artifacts, client export files, other processes
or abandoned crash directories. Graceful shutdown closes leases and deletes the
process directory. The existing temp-directory crash-cleanup limitation remains.

The application remains explicitly local-only and single-worker. CORS and opaque
IDs are not authentication. Operator-controlled trusted Joblib compatibility is
unchanged; no model upload, training, new labels, distributed services or public
deployment hardening are added. Two frontend changes update default limit text
only. OpenAPI/client contracts remain unchanged.

## Reproduce measurements

Use the existing Python environment from `requirements-api.txt`, from the repo
root. These commands fit only a new ephemeral synthetic benchmark fixture outside
measurement, never a repository model:

```bash
.venv/bin/python -m scripts.benchmark_traffic --rows 50000 --repeats 3 \
  --output /tmp/sqlite-50k.json
.venv/bin/python -m scripts.benchmark_traffic --rows 100000 --http-upload \
  --output /tmp/sqlite-100k-http.json
.venv/bin/python -m scripts.benchmark_traffic --rows 100000 --bounded-export \
  --output /tmp/sqlite-100k-bounded.json
.venv/bin/python -m scripts.benchmark_traffic --rows 500000 --bounded-export \
  --output /tmp/sqlite-500k.json
.venv/bin/python -m scripts.benchmark_traffic --rows 1000000 --bounded-export \
  --output /tmp/sqlite-1m.json
```

Rows above 100k explicitly override the row limit in the isolated benchmark store,
not server defaults. Other quotas remain at defaults. This does not establish
one-million-row HTTP/browser support or support for arbitrary wide CSVs.

The harness extends #13: fresh process per case; identical seed-42, 400-row,
100-tree/depth-12 synthetic model setup; identical six-feature invented input
with missing/infinite cells, ignored labels and duplicate flows. Timing includes
tracemalloc overhead, preflight/scans, inference/storage, queries, cold local SHAP,
sampled global SHAP and export. Every exported row/key/label/probability is checked
against authoritative batch inference after timing, with probability atol 1e-12.
Whole-frame parity is separately covered by regression fixtures. Deletion cleanup
is checked. This measures software processing, not detection accuracy or research.

`--http-upload` uses the actual POST route through TestClient, which buffers
uploaded bytes. Default export uses the real HTTP route but TestClient buffers
its response; the harness writes it to a client file. `--bounded-export` instead
consumes the same server export lease incrementally into a client file, so client
buffering cannot obscure server export memory. Large raw-store cases exclude
HTTP upload. Queries/SHAP still use HTTP routes. Client verification/export files
are outside server quota and are deleted with the benchmark temporary directory.

Memory metrics distinguish Python traced allocation peaks from native process
RSS: `ingestion_python_peak_bytes` is taken after ingestion, before lazy SHAP;
`export_additional_python_peak_bytes` is peak traced growth above the live export
baseline. `python_peak_bytes` covers all timed stages. OS RSS metrics are process
lifetime high-water marks (including startup/model loading), not interval deltas
or continuous polling. Native allocations may be absent from tracemalloc. Raw
reports retain environment, command, revisions and dirty-worktree flags. These
runs measured PR 2's working tree based on #13 before final query-integer/OS-error
edge guards, which do not affect the benchmark's valid-data path.

Environment: Apple M2 / Mac14,2, 8 logical CPUs, 8 GiB RAM, macOS 27.2 arm64,
Python 3.13.13, NumPy 2.2.6, pandas 2.2.3, scikit-learn 1.6.1, SHAP 0.48.0,
FastAPI 0.121.0, HTTPX 0.28.1. Forest `n_jobs=-1`; OMP/BLAS thread variables unset.
No other test/build workload ran concurrently with measurements.

## Measured results

50k comparison: medians of three fresh processes per implementation. The #13
post-validation baseline uses the same synthetic model/input. All new 50k CSV
export hashes exactly match all baseline hashes. Export timing now additionally
writes a client file, so it is not an identical microbenchmark.

| Architecture, 50k | Ingestion s | Rows/s | Total lifecycle s | Python total peak MiB | OS lifetime peak RSS MiB | Result bytes | Export s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PR 1 DataFrame/JSONL | 3.444 | 14,518 | 21.644 | 51.69 | 314.36 | 7,466,594 | 0.471 |
| PR 2 SQLite/batches | 2.933 | 17,045 | 21.948 | 40.40 | 220.25 | 5,898,240 | 0.300 |

Raw comparison: [PR 1](traffic-parser-validation-2026-10-30.json),
[PR 2](traffic-sqlite-50k-2026-10-30.json). These are descriptive local measurements,
not statistically established speedups; caches, scheduler and thermal state can
affect timing/RSS. Cold SHAP dominates the total for smaller cases.

Each large case below ran once. MiB = 1,048,576 bytes.

| Case | Ingestion s | Rows/s | Ingestion Python peak MiB | Export added Python peak MiB | OS lifetime peak RSS MiB | Database MiB | Export s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| [100k-http](traffic-sqlite-100k-http-2026-10-30.json) | 6.375 | 15,687 | 10.13 | 3.36 | 215.05 | 11.39 | 0.652 |
| [100k-bounded](traffic-sqlite-100k-bounded-2026-10-30.json) | 5.938 | 16,840 | 5.39 | 0.40 | 238.38 | 11.39 | 0.640 |
| [500k-bounded](traffic-sqlite-500k-bounded-2026-10-30.json) | 30.351 | 16,474 | 5.55 | 0.40 | 201.45 | 57.42 | 3.371 |
| [1m-bounded](traffic-sqlite-1m-bounded-2026-10-30.json) | 60.017 | 16,662 | 5.76 | 0.41 | 193.39 | 114.93 | 5.991 |

All seven new benchmark cases completed and verified all requested predictions,
ordered complete exports, SHAP reconstruction and cleanup. Maximum absolute
reconstruction error was 9.44e-16.

With fixed batch/cache/export sizes, the server-side 100k→1M traced ingestion peak
stays about 5.39→5.76 MiB and incremental export peak about 0.40→0.41 MiB; database
size and processing time grow with rows. Together with removal of all per-row
session collections and SQL/streaming regression coverage, this supports bounded
memory behavior for the tested narrow synthetic workloads. It is not a universal
RAM bound for arbitrary models/column widths or proof based solely on tracemalloc.
OS peaks were also recorded but are not comparable interval deltas.

The verified default is **100,000 rows through complete HTTP upload/query/SHAP/
export/delete**. **1,000,000 rows passed the backend lifecycle benchmark** with an
explicit row-limit override, six features, 512 MiB temporary quota and 10k batches;
it is not enabled by default or certified for HTTP/browser uploads. Sparse
filtered queries at large sizes scan rows and can slow down; SQLite indexes also
add disk/write overhead. Prefer the default limits unless the operator validates
actual schema, disk budget and latency. Future work may optimize counts/keyset
pagination or add jobs/progress separately; none is required or added here.
