# Explainable AI-Based Network Intrusion Detection System Using Machine Learning

A university Network Security course MVP: classify offline network flow CSVs as
BENIGN (0) or DDoS (1), evaluate a Random Forest on labeled held-out data, and
explain its predictions with SHAP. Version 0.2 adds an Nx workspace, a SvelteKit web frontend, and a local FastAPI
adapter. The original Streamlit workflow remains available. No packet capture,
live monitoring, database, or external inference service is included.

**Development version:** `0.2.0-alpha.1`. See the [v0.2 alpha release notes](RELEASE_NOTES_v0.2.0-alpha.1.md) and [changelog](CHANGELOG.md) for release scope and limitations. The existing `0.1.0-alpha.1` release and
its scientific implementation are preserved. The training, batch inference,
evaluation, SHAP explanation, and local dashboard workflows are implemented and
tested, but the project is an academic prototype and is not production-ready.

Inspired by *E-XAI: Evaluating Black-Box Explainable AI Frameworks for Network
Intrusion Detection*, IEEE Access (2024),
[DOI 10.1109/ACCESS.2024.3365140](https://doi.org/10.1109/ACCESS.2024.3365140).
This is a simplified course implementation, **not a reproduction of the paper's
experiments, methodology, or results**. The IEEE page required a JavaScript/robot
check during development; no claim is made to have reviewed its full text.

## Monorepo quick start (v0.2)

Use **Node 22.17+**, **pnpm 11.4.0**, and **Python 3.11–3.13**. Run from the root:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-api.txt
npm install --global pnpm@11.4.0
pnpm install --frozen-lockfile
pnpm dev
```

Open <http://127.0.0.1:5173> for the web dashboard and
<http://127.0.0.1:8000/docs> for FastAPI. The dashboard reads actual service health
and saved model metadata. Use **Traffic Analysis** to upload a CSV, run real batch
inference, explore paginated predictions, inspect feature values, and export results.
See the [CSV usage and API guide](docs/traffic-analysis.md) for requirements and
local session limits. Both services start without a dataset or model;
model-dependent requests return a clear 503 until a trusted artifact is configured.
No model training is part of installation, development startup, or build.

```bash
pnpm dev:web                  # Nx: SvelteKit only
pnpm dev:api                  # Nx: FastAPI only
pnpm test                     # Python engine, API, frontend tests
pnpm check                    # Python checks, schema drift, Svelte/TypeScript
pnpm build                    # SvelteKit Node build
pnpm contract:generate        # FastAPI -> OpenAPI -> TypeScript
pnpm nx e2e web               # Chromium workflow (install browser first; see development docs)
pnpm graph                    # Nx dependency graph
pnpm nx run ids-core:compatibility  # trusted model CLI + SHAP checks (if available)
```

```text
apps/
  web/                    SvelteKit 3, Svelte 5, Tailwind 4, shadcn-svelte
  api/                    FastAPI adapter and API tests
packages/
  api-client/             checked-in OpenAPI and generated TypeScript contract
  ids-core/               future packaging boundary documentation
src/                      unchanged Python ML engine (Nx project: ids-core)
project.json              root engine registration, including Python tests/scripts
scripts/                  Python launcher, contract export, compatibility checks
nx.json                   Nx graph/task/cache configuration
package.json              pnpm workflows; version 0.2.0-alpha.1
pnpm-workspace.yaml
pnpm-lock.yaml
data/ models/ reports/     existing ignored local data and scientific artifacts
docs/                     architecture, development, migration, research evidence
```

The graph is `web -> api-client -> api -> ids-core`. Python stays in `src` because
existing Joblib bundles reference `src.preprocess.NumericFeatures`. Nx orchestrates
commands and is not an ML runtime dependency. Original `python -m src.*` and
`streamlit run app.py` entry points remain valid. Only trusted operator-controlled
model paths are accepted; models cannot be uploaded through the API.

Configuration, Nx targets, schema generation, and clean-clone setup are explained
in [development workflow](docs/development.md). See [architecture](docs/architecture.md)
for boundaries and caching decisions, and [migration verification](docs/migration-v0.2.md)
for measured compatibility results. The [Traffic Analysis verification record](docs/traffic-analysis-verification.md)
lists changed files, tests and remaining limits for this milestone.

## Existing Python and scientific workflows

The sections below retain the v0.1 scientific behavior and reproduction commands.
Use `requirements-api.txt` for the complete v0.2 environment, or the original
`requirements.txt` when running only Python/Streamlit. Training commands are
explicit experiments and are not required to start either UI.

### Python setup

Use **Python 3.11–3.13**. The pinned SHAP/Numba versions do not support Python 3.14.
Run every command from this repository root. Python 3.13 is used in the examples.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Direct dependencies are pinned in `requirements.txt`: NumPy 2.2.6, Pandas 2.2.3,
scikit-learn 1.6.1, SHAP 0.48.0, Numba 0.61.2, Matplotlib 3.10.3, Streamlit 1.45.1,
Joblib 1.5.1, and Pytest 8.3.5. Use the same environment to train and reload models.
Plotting compatibility pins: Pyparsing 3.2.3 and Altair 5.5.0 (a Streamlit dependency).

## Dataset and real-data workflow

1. Visit the official [CIC-IDS2017 dataset page](https://www.unb.ca/cic/datasets/ids-2017.html).
2. Follow its download process, obtain the labeled machine-learning CSV archive,
   and extract **Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv**.
3. Put the extracted CSV in `data/raw/`. Do not rename or manually reorder features.
   Review the dataset provider's usage and citation requirements.

```bash
python -m pytest -q
python -m src.train --data "data/raw/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv" --provenance cic-ids2017
streamlit run app.py
```

Training writes `models/model.joblib`, `models/metrics.json`,
`models/feature_schema.json`, and `models/metadata.json`. The bundle contains the
fitted sklearn Pipeline and a small held-out feature sample for demonstrations.
No retraining is needed to start the app. Optional `--output-dir` changes the
artifact directory; set `IDS_MODEL_PATH` to its `model.joblib` for the dashboard.
Only load trusted local Joblib artifacts: deserialization can execute Python code.

## Synthetic smoke test without CIC-IDS2017

The real CIC-IDS2017 experiment is complete; see
[experiment-results.md](docs/experiment-results.md). The commands in this optional
section use a separate `--output-dir` for fixture training to preserve the real artifact. A deterministic
fixture generator makes small, invented flow-like data with overlapping classes.
Its features are not an emulation of the dataset. Scores from this fixture validate
software behavior only and **are not research results or evidence of real-world
intrusion detection performance**.

```bash
python -m src.synthetic --output data/raw/SYNTHETIC_flows.csv
python -m src.train --data data/raw/SYNTHETIC_flows.csv --provenance synthetic --output-dir models/synthetic-smoke
python -m src.predict --model models/synthetic-smoke/model.joblib --data data/raw/SYNTHETIC_flows.csv --output reports/SYNTHETIC_predictions.csv
python -m src.explain --model models/synthetic-smoke/model.joblib --output-dir reports/synthetic-smoke/figures
IDS_MODEL_PATH=models/synthetic-smoke/model.joblib streamlit run app.py
```

In the app, enable **Use saved held-out sample** to exercise the dashboard without
uploading a file. Upload the synthetic CSV to test the complete upload path. Train
again on the real CSV before using a real-data schema. The UI displays the saved
provenance for both metrics and inference.

## Data handling and evaluation

- UTF-8/UTF-8-BOM comma-separated CSVs only; malformed files, empty inputs,
  duplicate/ambiguous normalized headers, and empty headers are rejected. One
  documented CIC-IDS2017 exception is supported: a second `Fwd Header Length`
  header becomes `Fwd Header Length.1` and is excluded from model features. An
  already suffixed copy is also excluded. No other duplicate headers are accepted.
  See the [CIC-IDS2017 troubleshooting study](https://intrusion-detection.distrinet-research.be/WTMC2021/extended_doc.html).
- Trim column names. Find `Label` case-insensitively; trim/case-normalize labels;
  retain only BENIGN and DDoS. Label is never a feature.
- Remove exact duplicate records before splitting. Also remove duplicate
  feature/label records after known identifiers are excluded.
- Conservatively exclude flow IDs, source/destination IPs and ports, timestamps,
  unnamed index columns, and known target/prediction fields, including Pandas
  suffixed copies such as `Label.1` and `Source IP.1`. Ports are excluded
  because they can encode the fixed attack scenario. Protocol may remain a feature.
  Do not add custom ground-truth annotations as features.
- Convert feature values to numbers; invalid training tokens and ±infinity become
  missing. This conversion is pointwise and does not learn from the test set.
- Stratified **80/20** train/test split with seed 42. Optional `--max-train-rows`
  performs stratified subsampling **after** splitting; every held-out row is kept
  for final evaluation. Very small or single-class datasets fail explicitly.
- The Pipeline selects nonconstant, nonempty columns from training data only,
  then fits a median `SimpleImputer` on training data only. The same fitted
  transformations are used at prediction and explanation time.
- Random Forest defaults: 100 trees, max depth 12, seed 42, `n_jobs=-1`.
  No tuning against the test set. Class prediction uses sklearn's default highest
  class probability (ties resolve to BENIGN); probabilities are uncalibrated.
- Saved metrics: accuracy, precision, recall, F1, confusion matrix, false positive
  rate. DDoS is the positive class. Matrix rows are true classes and columns are
  predicted classes, both in `[BENIGN, DDoS]` order: `[[TN, FP], [FN, TP]]`.
  FPR is `FP / (TN + FP)`; undefined FPR is JSON `null`. Zero-division precision,
  recall, and F1 use zero. Metrics are from labeled held-out data, never inferred
  from an unlabeled upload.
- Saved metadata records provenance, dataset SHA-256, random seed, row counts,
  class counts, dropped columns, model parameters, and package versions.

The parser reads chunks, but the cleaned dataset and split still fit in RAM.
This is not an out-of-core trainer. Subsampling reduces fitting cost, not CSV
loading or test-set memory. Use the single Friday CSV rather than all capture days.

## Batch prediction and schema

```bash
python -m src.predict --model models/model.joblib --data path/to/flows.csv --output reports/predictions.csv
```

Inputs must contain every retained feature named in `models/feature_schema.json`.
Whitespace around headers is accepted and column order is restored automatically.
Missing required columns and non-numeric nonempty inference tokens cause clear
errors. Extra columns, including labels/identifiers, are ignored and explicitly
reported; they cannot change predictions. Missing numeric cells and infinities
use the saved training medians. Rows with no usable feature values are rejected.
One output row per input row, including duplicates, preserves original row order.
Outputs contain `row_number` (1-based data row), `prediction`, and
`ddos_probability`. Prediction CSVs are exported without the uploaded raw fields.

The dashboard caps uploads at 50,000 rows and 200 MB, previews up to 1,000 results,
and downloads all accepted rows. The CLI has no upload row cap. Files are parsed
locally and are not submitted to an external service.

## SHAP interpretation

TreeExplainer uses `feature_perturbation="tree_path_dependent"` and
`model_output="raw"`. For this sklearn Random Forest classifier, raw tree outputs
are class probabilities. The implementation selects class **1 (DDoS)**, supports
the older list-of-class-arrays and newer `(rows, features, classes)` return formats,
and checks that `base_value + sum(SHAP values)` equals `predict_proba(...)[1]`.
Unexpected formats or a failed reconstruction raise an error instead of displaying
an explanation with a mislabeled scale.

- Global importance ranks `mean(abs(SHAP))` on at most 100 deterministically sampled
  flows. It describes that sample, not the entire population.
- A local waterfall starts at the model's expected DDoS probability. Positive
  contributions raise the output; negative contributions lower it. Contributions
  are in probability units, **not percentages or causal effects**. For example,
  `+0.08` adds 0.08 to the model output; it is not an 8% relative risk increase.
- The feature-value table shows the model's numeric values after imputation.
  Correlated flow features can redistribute attribution. Explanations describe the
  fitted model, not proof of an attack. First SHAP import can take a few seconds.
- Global and local explanations run on demand. Model resources and repeated global
  computations are cached; raw upload predictions are session-local.

## Repository

```text
app.py                  Streamlit upload, predictions, metrics, SHAP
scripts/
  validate_real_data.py  real-data training, independent evaluation, SHAP, timings
  verify_real_dashboard.py  real-artifact Streamlit checks without training
src/
  data_loader.py        CSV validation, labels, exclusions, deduplication
  preprocess.py         train-only numeric feature selection
  train.py              split, Pipeline fitting, artifact/report persistence
  evaluate.py           labeled classification metrics
  predict.py            artifact loading, schema validation, inference CLI
  explain.py            positive-class SHAP, plots, explanation CLI
  synthetic.py          clearly labeled smoke-fixture generator
tests/                  loader, leakage, metrics, inference, SHAP, UI tests
data/raw/               user-supplied input (ignored)
data/processed/         optional local outputs (ignored)
models/                 local trained bundle and reports (ignored)
reports/figures/        generated plots (ignored)
docs/implementation-plan.md
requirements.txt
CHANGELOG.md
RELEASE_NOTES.md
```

## Limitations and academic use

The supplied Friday CSV has been validated, trained, evaluated, and explained;
measured results and verification limits are in
[docs/experiment-results.md](docs/experiment-results.md). Peak memory consumption
was not measured. A random split from one capture day may retain temporal
or host-related correlations even after obvious identifier removal; it does not
establish generalization to other days, networks, or new attack types. This is a
binary closed-set demonstration, not an anomaly detector or production defense.
No claims are made about unknown attacks, causality, fairness, or robustness.

To extend the academic evaluation, keep a separate day/network holdout, record
data provenance, compare baselines using training-only validation, evaluate
calibration and imbalance, and only then report untouched held-out results.

## Executed real-data validation

On **30 October 2026 (Asia/Bangkok)**, the supplied Friday CIC-IDS2017 CSV loaded
successfully: **225,745 raw rows**, **221,290 retained rows**, **66 fitted features**.
The unchanged default Random Forest trained on **177,032** rows and was evaluated
on **44,258** held-out rows. No synthetic training followed the real experiment.

| Metric | Held-out result |
|---|---:|
| Accuracy | 99.970627% |
| DDoS precision | 99.996093% |
| DDoS recall | 99.953130% |
| DDoS F1 | 99.974607% |
| False positive rate | 0.005360% |

Confusion matrix: `[[18654, 1], [12, 25591]]`, with actual classes in rows and
predicted classes in columns, ordered BENIGN/DDoS. These results describe one
same-capture random holdout; they do not establish external generalization.
The dashboard rounds to three decimals, so its `1.000` scores and `0.000` FPR
must be read alongside the full-precision report and the 13 classification errors.

- All **37 automated tests passed in 20.39 s**, before real-data training.
  `pip check` reported no broken requirements.
- Independent real-data checks verified disjoint split indices, zero shared
  feature-vector hashes before and after imputation, training-only feature
  selection/medians, and held-out metrics matching the reloaded model.
- Global SHAP on 100 real held-out flows and local TP/TN/FP/FN explanations passed
  probability reconstruction checks. Six exported figures were visually inspected.
- Streamlit AppTest loaded the real artifact, checked predictions, uploaded real
  held-out CSV bytes, downloaded-result controls, metrics, and global/local SHAP.
  The server at `http://127.0.0.1:8503` returned health **HTTP 200, `ok`**.
- Browser automation was unavailable. Browser appearance, native file-picker
  interaction, and browser download execution remain unverified.
- Median times: pipeline prediction **16.47 ms/flow**, validation plus prediction
  and probability wrapper **36.49 ms/flow**, local SHAP **25.26 ms**, global SHAP
  **152.32 ms/100 flows**. These exclude UI rendering and are local measurements.

Read **[docs/experiment-results.md](docs/experiment-results.md)** for methodology,
dataset hash/statistics, full metrics, timings, explanation observations,
reproduction commands, and limitations. Current evidence is in
**`reports/real-data/`**. Earlier `reports/figures/` and `reports/review-run/` are
historical synthetic outputs. Generated reports and models remain ignored by the
existing `.gitignore`; archive them explicitly for course submission.

The experiment and real-model UI checks can be repeated without changing the
architecture:

```bash
# Full suite first: it uses isolated synthetic fixtures.
.venv/bin/python -m pytest -q
.venv/bin/python -m pip check
# Train the final real model and export evaluation/SHAP/timing evidence.
.venv/bin/python -m scripts.validate_real_data
# Reload and validate the dashboard; no training.
.venv/bin/python -m scripts.verify_real_dashboard
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8503
```

Use **Use saved held-out sample** or upload `reports/real-data/heldout-demo.csv`
for a demonstration. Both use the real held-out feature sample. The locally
supplied dataset's publisher authenticity was not independently verified; its
exact SHA-256 is recorded in the report and model metadata.

## Final academic review and demonstration

The verified Random Forest remains the main model. For the fixed Decision Tree
comparison, precise dashboard metrics, all held-out errors, and safe commands
that preserve this model, see [experiment results](docs/experiment-results.md)
and [demo/submission checklists](docs/demo-checklists.md).
Run `.venv/bin/python -m scripts.compare_baseline` before
`.venv/bin/python -m scripts.verify_real_dashboard`; neither overwrites the main model.
The comparison includes a temporary RF clone for classifier training timing only.
Do not rerun the original training workflow as demo setup. A subsequent real Brave smoke test passed, including native CSV upload/download
and global/local SHAP; see `reports/real-data/browser-smoke-test.json`.

### Model Insights

The [Model Insights guide](docs/model-insights.md) describes `/model-insights`, available
from primary navigation without uploading traffic. It shows saved held-out metrics,
actual/predicted confusion-matrix counts, artifact identity and dataset provenance through
`GET /model/evaluation`. Missing optional metadata stays missing; inconsistent snapshots
are rejected rather than corrected. Synthetic artifacts are clearly disclosed. These
same-scenario evaluation results do not measure accuracy on newly uploaded traffic or
establish performance on unseen networks.

See the [milestone verification and release-readiness report](docs/model-insights-verification.md).
