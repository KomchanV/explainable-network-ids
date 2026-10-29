# Offline CSV Traffic Analysis and Flow Explorer

Start the application with `pnpm dev` after following [development setup](development.md).
Open <http://127.0.0.1:5173/analyze>, select or drop a CSV, and choose **Analyze CSV**.
The API must have an operator-configured trusted model. Startup never trains one.
After the summary appears, choose **Open Flow Explorer**. The dashboard also links
to the last successful analysis in this browser. Only its opaque ID is saved in
browser local storage; CSV values and results are not stored there.

## Accepted data

Use offline CIC-IDS2017 flow CSVs with comma separators, a single-line header,
and UTF-8 or UTF-8-BOM encoding. `GET /model` lists every required feature; names
must match the trained schema after surrounding whitespace/BOM normalization.
Maximum upload: **200 MiB (209,715,200 bytes)**, **50,000 data rows**, **256 columns**,
and **5,000,000 cells** (data rows × header columns, including ignored columns).
Headers are limited to 64 Ki characters and physical data lines to 1 Mi characters.
An upload must finish within five minutes. These additional shape/deadline bounds
protect the local parser; remove unused extra columns or use the original CLI for
larger inputs. The browser reports “200 MB” for the binary byte limit.

Empty files, malformed records, invalid encoding, NULs, empty/ambiguous headers,
missing required columns, and nonnumeric required values are rejected. The original
engine performs CSV loading, numeric validation, preprocessing and inference.
Empty required cells and nonfinite numeric values use the fitted training medians;
a flow with every required value missing is rejected. Exactly two original
`Fwd Header Length` headers are permitted: the second becomes
`Fwd Header Length.1` and is ignored, preserving the documented CIC exception.
Other duplicate/ambiguous headers are rejected. Extra columns, including labels
and identifiers, are ignored and listed in the summary. Input ordering and
identical flow rows are preserved. Row numbers are one-based data-row ordinals,
not physical file line numbers. No ground-truth evaluation is performed.

## Exploring and exporting

The explorer shows actual predicted BENIGN/DDoS counts, DDoS share, model SHA-256
identifier/provenance, filename, and creation/expiration times. Predictions are
not verified ground truth. P(DDoS) is an **uncalibrated model output**, not a
validated confidence or threat-severity score. Existing same-dataset metrics
cannot establish real-world generalization.

Filter by predicted class, inclusive P(DDoS) range, or exact row number. Apply
filters to return to page one. Sort by row or probability, ascending/descending;
probability ties always use ascending row number. Choose 10/25/50/100 rows per
page. The browser receives one result page, never all flows. Inspect fetches one
flow's model features on demand. Values are numeric inputs before median
imputation; missing/nonfinite values appear as “Missing”. Ignored IPs, ports,
timestamps, labels and other metadata are never retained in detail files.

**Export all predictions** downloads every result in original input order,
independent of active filters/page/sort. CSV columns are `row_number`,
`prediction`, `ddos_probability`. Export excludes raw inputs, metadata and supplied
labels. It does not rerun inference. **Delete analysis** immediately removes its
results and feature-detail file; re-upload is required to recover them.

## API reference

FastAPI's `/docs` and checked-in OpenAPI are the source of truth. Errors share
`{"error":{"code":"...","message":"..."}}`; raw row values are not echoed.

- `POST /api/v1/analyses?filename=flows.csv`: raw CSV body, `Content-Type: text/csv`.
  Returns 201 with summary. Raw bodies intentionally avoid multipart buffering
  before the application can enforce the upload byte limit. Do not use FormData.
- `GET /api/v1/analyses/{id}`: analysis summary.
- `GET /api/v1/analyses/{id}/flows`: `page` (1+), `page_size` (1–100, default 25),
  optional `prediction` (`BENIGN`/`DDoS`), `probability_min`/`probability_max`
  (inclusive 0–1), `row_number` (1+), `sort` (`row_number`/`probability`),
  `direction` (`asc`/`desc`). Returns items, filtered total, page and page size.
  Pages beyond the last return empty items and the same filtered total.
- `GET /api/v1/analyses/{id}/flows/{row_number}`: one prediction plus feature values.
- `GET /api/v1/analyses/{id}/export`: `text/csv` attachment `predictions.csv`.
- `DELETE /api/v1/analyses/{id}`: 204, deletes temporary results.

Existing `GET /health`, `GET /model` and `POST /predict` remain compatible.

```bash
curl -X POST 'http://127.0.0.1:8000/api/v1/analyses?filename=flows.csv' \
  -H 'Content-Type: text/csv' --data-binary @flows.csv
curl 'http://127.0.0.1:8000/api/v1/analyses/ID/flows?page_size=10&prediction=DDoS'
curl 'http://127.0.0.1:8000/api/v1/analyses/ID/export' -o predictions.csv
```

Status codes: 404 unknown/deleted/missing flow; 408 upload deadline; 410 recently
expired session; 413 byte limit; 415 unsupported media type; 422 invalid CSV,
shape/row limits or query; 503 missing model, busy ingestion, session/storage full.
Capacity errors require retry after processing ends, deletion, or expiration.

## Session lifecycle and limits

This is **local-only, single API worker, without multi-user authentication**.
Keep both servers bound to loopback. CORS is not authentication and unpredictable
IDs do not provide user isolation on a public deployment. Anyone holding an ID
can read, export or delete that analysis. Do not expose this API publicly.

Each process uses a private OS temporary directory. At most five analyses retain
up to 250,000 predictions/offsets in memory, with at most 512 MiB total feature
JSONL files on disk. Only one upload/inference runs per process; its temporary
raw input adds at most 200 MiB disk. Shape/row/byte limits bound parser and
inference intermediates; their memory footprint depends on CSV types/content.
Results expire one hour after creation, without extension on access. Cleanup
runs every 60 seconds and on session access/creation. Recent 128 expired IDs
return 410; older or restart-lost IDs return 404. Graceful shutdown deletes the
whole process directory. Results are not recoverable after restart. An abrupt
process kill may leave OS temporary files; operators must remove abandoned
`ids-analyses-*` directories after stopping the API or rely on OS temp cleanup.
The quotas apply to the running process, not crash leftovers or multiple workers.

No background inference queue, persistent database, authentication, live packet
capture, continuous monitoring, blocking, model upload/training, or HTTP SHAP is
implemented. Large requests can take minutes and no calibrated-probability or
new scientific performance claims are made.

## Investigating a prediction with SHAP

In Flow Explorer, choose **Inspect** on a row, then **Explain Prediction**.
Explanations are requested on demand, including for BENIGN predictions; they
always explain P(DDoS), not the probability of the predicted class. The local
section shows the original row/prediction, stored P(DDoS), training-path SHAP
baseline, reconstructed output, absolute reconstruction error and model SHA-256
identifier/provenance. A provenance of synthetic identifies a software fixture,
not scientific evaluation evidence.

Orange upward contributions increase P(DDoS) from the baseline; teal downward
contributions decrease it. The waterfall follows the additive path. Choose top
12 or all features; **Other features** sums every hidden signed term. Full
contributions are always returned and the table retains original model order.
The available numeric input and post-imputation model value are separate columns.
Missing/nonfinite input is null and labeled Missing → fitted median, never zero.
Original CSV spelling and ignored identifiers are not retained.

The backend verifies `baseline + sum(all SHAP contributions) ≈ stored P(DDoS)`
with absolute tolerance 1e-6 and relative tolerance 1e-5, matching the scientific
engine. Display rounding uses six decimal places (scientific notation for tiny
nonzero contributions); rounding may prevent the printed terms from adding
exactly. Shape, finite-value or reconstruction failures reject the explanation.

In **Global Explainability**, choose 1–100 flows (default 50) and explicitly
**Generate Global Explanation**. The actual sample is limited by session size.
Sampling is uniform without replacement over the entire uploaded analysis, using
NumPy default_rng seed 42, then restoring original row order. It is reproducible
for the same analysis and sample size, but does not guarantee rare-class coverage.
Mean absolute SHAP values rank the magnitude of contributions in that sample;
they do not show direction and do not explain an entire network/population.

SHAP characterizes model behavior, not causal evidence of a network attack.
P(DDoS) remains uncalibrated, not validated confidence or threat severity. This
is an offline academic prototype.

### Explanation API and resource limits

- `GET /api/v1/analyses/{id}/flows/{row_number}/explanation` returns one full
  positive-class contribution vector, raw available/transformed numeric values,
  baseline, reconstruction/error, stored prediction and model provenance.
- `GET /api/v1/analyses/{id}/explanations/global?sample_size=50&top_n=15` returns
  mean absolute contributions sorted descending, actual sample count, sampled
  row numbers, seed/method and model provenance. Omitted top_n defaults to the
  smaller of 15 and model feature count; explicit values above that count fail.

One SHAP request runs at a time in the local single-worker process. Another
request receives 503 `explanation_busy`; wait and retry. Requests never explain
more than 100 flows and never automatically explain all 50,000 uploaded rows.
The browser allows five minutes for bounded explanation requests. A timeout or
leaving the view does **not** necessarily cancel Python computation. There is no
explanation cache; each click computes again. Existing session TTL/deletion and
resource bounds apply. Deletion/expiry during calculation rejects the result
after computation without reopening deleted files.

Errors retain the existing envelope: 503 `model_unavailable`/`explanation_busy`,
404 `analysis_not_found`/`flow_not_found`, 410 `analysis_expired`, 422 schema/query
errors, 500 `shap_failure`/`reconstruction_failure`. Errors do not echo uploaded
values, model artifacts, filesystem paths or stack traces.
