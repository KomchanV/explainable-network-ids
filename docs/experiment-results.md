# CIC-IDS2017 real-data experiment results

Experiment executed **30 October 2026, 02:14 Asia/Bangkok**. The existing offline
BENIGN (0) versus DDoS (1) Random Forest was trained on the supplied CSV and
evaluated on 44,258 held-out flows. Accuracy was **99.970627%**, with **1 false
positive and 12 false negatives**. These are measured results for this particular
same-capture split, not evidence of performance on a new network or unknown attacks.

The original experiment and saved Random Forest are preserved. Final review adds
a fixed Decision Tree comparison, precise dashboard metrics and saved error
examples. Architecture is unchanged. Tests train fixtures in temporary directories
only; they never replace the real-data model in `models/model.joblib`.

## Dataset and provenance

Input: `data/raw/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv`, **77,123,859 bytes**.
The file exists and was successfully parsed using the project's strict UTF-8 CSV
loader, including whitespace normalization and its supported redundant header.

SHA-256:

```text
6ff1580f5f81c0ae28a26f7631721018577f5f7c5e0feac28b795fcfe7b411ee
```

The source was supplied locally. Its name, schema, labels, and contents were
inspected; the hash identifies the exact input used. **Authenticity against an
independently trusted publisher checksum was not verified.** `cic-ids2017` is the
recorded provenance declaration, not automatic authentication.

CIC-IDS2017 contains labeled flows extracted from a controlled traffic capture.
The provider documents Friday afternoon DDoS traffic and provides machine-learning
CSV downloads. This experiment uses that benchmark CSV rather than the MVP's
invented smoke-test fixture; it does not inspect live production traffic.
See the [official CIC-IDS2017 dataset description](https://www.unb.ca/cic/datasets/ids-2017.html).

| Stage | BENIGN | DDoS | Total |
|---|---:|---:|---:|
| Raw CSV | 97,718 | 128,027 | 225,745 |
| Retained after cleaning | 93,274 | 128,016 | 221,290 |
| Training | 74,619 | 102,413 | 177,032 |
| Held-out test | 18,655 | 25,603 | 44,258 |

The CSV has 79 columns including `Label`. Cleaning removed 2,633 exact duplicate
records, then 1,822 additional duplicate feature/label records after exclusions
and numeric conversion. No unsupported labels were present or removed.
`Destination Port`, redundant `Fwd Header Length.1`, and `Label` were excluded,
leaving 76 candidate features. Ten training-constant/all-empty columns were
dropped, leaving **66 fitted features**. Their names and the exclusions are saved in
[dataset-statistics.json](../reports/real-data/dataset-statistics.json) and
[feature_schema.json](../reports/real-data/feature_schema.json).

Before deduplication, the candidate numeric fields contained 4 missing cells,
64 infinite cells, and no nonempty invalid numeric tokens. Infinities became
missing. After deduplication there were 52 missing cells across 26 retained rows;
the fitted training medians handled these values.

## Methodology and leakage controls

1. Use the existing loader to normalize headers, retain only BENIGN/DDoS,
   exclude identifiers/ports/targets, convert numbers pointwise, replace infinities,
   and remove duplicate records. No learned statistic is computed here.
2. Make one stratified **80/20 random split with seed 42**. Use the entire training
   split: no training subsampling, resampling, hyperparameter search, threshold
   selection, or test-driven model selection was performed.
3. Fit the existing sklearn Pipeline on training rows only: `NumericFeatures`
   selects varying numeric columns; `SimpleImputer(strategy='median')` learns
   training medians; `RandomForestClassifier` uses **100 trees, max depth 12,
   Gini criterion, sqrt feature sampling, bootstrap=True, random_state=42,
   class_weight=None, n_jobs=-1**. Prediction uses the default highest class
   probability; ties resolve to BENIGN. Probabilities are uncalibrated.
4. Reload the saved artifact, reconstruct the deterministic split without fitting,
   evaluate the full test set, and compare the metrics with the artifact. They match.
5. Independently verify disjoint split indices, zero shared hashes of retained
   feature vectors before **and after imputation**, train-only feature selection,
   and train-only imputer medians. All checks passed. SHAP uses training tree path
   counts, not test rows fitted as background. Inspecting held-out errors and
   explanations happened after fitting and did not change the model.

[leakage-audit.json](../reports/real-data/leakage-audit.json) records these checks.
[split-membership.csv](../reports/real-data/split-membership.csv) records zero-based
row IDs in the **cleaned, reset-index dataset**, not original CSV line numbers.
The row IDs are reproducible with this input hash and loader version. Exact-row
checks do not establish independence between correlated flows in the same capture.

## Held-out classification results

DDoS is the positive class. Precision = TP/(TP+FP), recall = TP/(TP+FN),
F1 = 2PR/(P+R), FPR = FP/(TN+FP), and accuracy = (TP+TN)/N.
Percentages below are rounded only for presentation; full-precision values are in
[metrics.json](../reports/real-data/metrics.json) and
[metrics.csv](../reports/real-data/metrics.csv).

| Metric | Fraction | Percentage |
|---|---:|---:|
| Accuracy | 0.9997062677933933 | 99.970627% |
| Precision | 0.9999609252891528 | 99.996093% |
| Recall | 0.9995313049252040 | 99.953130% |
| F1-score | 0.9997460689520461 | 99.974607% |
| False positive rate | 0.0000536049316537 | 0.005360% |

| Actual / predicted | BENIGN | DDoS |
|---|---:|---:|
| BENIGN | 18,654 (TN) | 1 (FP) |
| DDoS | 12 (FN) | 25,591 (TP) |

There were **13 errors among 44,258 test flows**. The single false positive and
small number of misses warrant caution: a different split or deployment
distribution may change the rates substantially. This run did not measure
uncertainty across repeated splits or independent captures.

![Held-out confusion matrix](../reports/real-data/figures/confusion-matrix.png)

Per-flow ground truth, prediction, probability, and cleaned row ID are saved in
[heldout-predictions.csv](../reports/real-data/heldout-predictions.csv).

## Fixed Decision Tree baseline — final academic review

The runner verifies the input SHA-256, recreates the saved seed-42 stratified
80/20 split, and checks exact split membership. Both classifiers use the same
177,032 training rows, 44,258 test rows, 66 retained features, and arrays from the
saved train-fitted feature selector and median imputer. The baseline is sklearn's
default `DecisionTreeClassifier(random_state=42)`: Gini, unlimited depth, no class
weighting. Settings were fixed in advance; no held-out tuning or threshold search.

| Model | Accuracy % | Precision | Recall | F1 | FPR % | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|
| Random Forest | 99.970627 | 0.99996093 | 0.99953130 | 0.99974607 | 0.0053605 | 1 | 12 |
| Decision Tree | 99.975146 | 0.99984375 | 0.99972659 | 0.99978517 | 0.0214420 | 4 | 7 |

| Model | Classifier training seconds | Full-test inference seconds |
|---|---:|---:|
| Random Forest | 6.889714 | 0.041633 |
| Decision Tree | 2.038967 | 0.002775 |

Training time is one classifier fit on already transformed training inputs. An
in-memory RF clone with the saved parameters was fitted only for timing, with
predictions verified equal to the original. The main RF artifact is unchanged.
Inference uses the saved RF and fitted Tree: warmed `predict` on all transformed
test rows, median of five runs. Both exclude parsing, preprocessing, probabilities,
loading, SHAP and UI. This differs from the original 8.705-second full workflow.
Timings are local observations without process isolation or repeated fits, not
statistically established speed guarantees. Raw samples and parameters are in
[baseline-comparison.json](../reports/real-data/baseline-comparison.json) and the
[comparison CSV](../reports/real-data/baseline-comparison.csv).

![Baseline performance](../reports/real-data/figures/baseline-performance.png)
![Classifier timings](../reports/real-data/figures/baseline-timing.png)

The score panel explicitly zooms to 99–100%; the FPR panel starts at zero.
The Tree has TN=18,651, FP=4, FN=7, TP=25,596 (11 errors). It has slightly higher
accuracy, recall and F1 here; the RF has higher precision and fewer false alarms.
The Random Forest remains the main model. No significance test or split variability
analysis establishes universal superiority of either classifier.

Both are **same-capture benchmark results**, not estimates of real-world performance
on new networks, periods, or unknown attacks. Exact deduplication and training-only
preprocessing do not remove correlations among flows from the same scenario.
The baseline controls the inputs, not independence. Future tuning requires
training-only validation and a new untouched evaluation set; this inspected
holdout must not become an iterative tuning target.

## SHAP explanations

The existing TreeExplainer uses `feature_perturbation='tree_path_dependent'`,
`model_output='raw'`, and the explicit DDoS class. For this Random Forest the
explained output is DDoS probability. The implementation checks that the baseline
plus all contributions reconstructs `predict_proba(...)[1]`.

Global importance is mean absolute SHAP over **100 deterministically sampled
held-out rows**, seed 42: 40 BENIGN and 60 DDoS. This is a sample summary, not an
attribution average over the entire test population. Maximum probability
reconstruction error was **5.55 × 10^-16**.

| Leading feature | Mean absolute SHAP, probability units |
|---|---:|
| Fwd Packet Length Mean | 0.059446 |
| Fwd Packet Length Max | 0.050506 |
| Avg Fwd Segment Size | 0.037258 |
| act_data_pkt_fwd | 0.030424 |
| Subflow Fwd Bytes | 0.030304 |

![Global SHAP importance](../reports/real-data/figures/global-shap.png)

Packet-length and forward-volume features dominate this sample's attribution.
Several features describe related quantities, so this ranking must not be read
as independent evidence or a causal explanation of attacks.

Local explanations were computed for the first example of each outcome in the
deterministic held-out order. This selection includes errors rather than choosing
only high-confidence correct predictions. All four use baseline P(DDoS)
**0.5784780153** and passed probability reconstruction checks.

| Outcome | Cleaned row ID | True label | Prediction | P(DDoS) |
|---|---:|---|---|---:|
| TN | 40,559 | BENIGN | BENIGN | 0.0000000000 |
| TP | 123,181 | DDoS | DDoS | 0.9999884029 |
| FP | 17,667 | BENIGN | DDoS | 0.8792370695 |
| FN | 169,258 | DDoS | BENIGN | 0.2887722822 |

The false positive receives positive contributions from forward packet-length
features despite being labeled BENIGN. In the false negative, `act_data_pkt_fwd`
and `Subflow Fwd Bytes` lower the DDoS output. These explain the model's errors;
they do not demonstrate incorrect dataset labels. Individual contribution tables
are saved as `local-TN.csv`, `local-TP.csv`, `local-FP.csv`, and `local-FN.csv`.

![False positive explanation](../reports/real-data/figures/local-FP.png)
![False negative explanation](../reports/real-data/figures/local-FN.png)

All four waterfall PNGs, the global plot, and the confusion matrix were opened
and visually inspected. Complete attribution tables and additivity values are in
`global-shap-values.csv`, `global-importance.csv`, `shap-additivity.csv`, and
[shap-validation.json](../reports/real-data/shap-validation.json).

## Measured runtime

Environment: Python 3.13.13, macOS 27.2 ARM64, 8 logical CPUs reported by Python;
NumPy 2.2.6, pandas 2.2.3, sklearn 1.6.1, SHAP 0.48.0, Numba 0.61.2,
Matplotlib 3.10.3, Streamlit 1.45.1, Joblib 1.5.1. Hardware brand and installed RAM
were unavailable through sandboxed `sysctl`, and peak memory was not measured.
The exact environment and timestamps are in [environment.json](../reports/real-data/environment.json).

Times use `time.perf_counter()` in one process, sequentially before UI validation.
Prediction warm-up calls are excluded. Each prediction repetition uses the same
input: the first saved held-out row or first 1,000 test rows. Each repeated SHAP
call uses the same row/sample and constructs a fresh explainer; no dashboard
cache is used. SHAP timings include validation, preprocessing, explainer setup,
attribution, and probability reconstruction, but exclude plot rendering and import.

| Operation | Repetitions | Mean ms | Median ms | p95 ms |
|---|---:|---:|---:|---:|
| Pipeline `predict`, 1 flow | 100 | 16.269 | 16.471 | 17.146 |
| `predict_batch`, 1 flow | 100 | 36.415 | 36.488 | 36.891 |
| `predict_batch`, 1,000 flows, total batch time | 20 | 35.420 | 35.526 | 36.359 |
| Local SHAP, 1 flow | 10 | 26.217 | 25.264 | 31.198 |
| Global SHAP, 100 flows, total sample time | 3 | 153.516 | 152.319 | 155.968 |

`predict_batch` includes schema checks, numeric conversion, both `predict` and
`predict_proba`, and construction of output rows. It excludes CSV parsing,
artifact loading, and UI rendering. Batch time is not single-request latency;
parallel trees and fixed per-call overhead can make batching much more efficient.

The complete training workflow took **8.705 s**, including CSV loading, splitting,
pipeline fitting, evaluation, hashing, compression, and artifact saving. Artifact
reload took **10.263 ms**. Full-test `predict` plus `predict_proba` took **93.693 ms**
in one pass each. Importing the explanation module took **487.107 ms**; the first
100-flow SHAP call took **140.931 ms**. These are single observations, not repeated
training benchmarks. Raw timing samples are in [timings.json](../reports/real-data/timings.json).
The 3-repetition global p95 is descriptive only. No load, concurrency, production
hardware, or browser interaction latency benchmark was performed.

## Original experiment validation record

The test counts below are historical evidence from the original experiment.
Current final-review validation is recorded separately at the end of this report.

- `.venv/bin/python -m pytest -q`: **37 passed in 20.39 s**, exit 0.
- `.venv/bin/python -m pip check`: **No broken requirements found**, exit 0.
- Existing tests include CSV validation, leakage safeguards, metrics, persistence,
  inference, SHAP, and Streamlit behavior. Their synthetic fixtures were run
  **before** the real-data training and used temporary artifacts. They establish
  software behavior; the independent real-data runner establishes the results above.
- `scripts.verify_real_dashboard` completed with exit 0 using the actual real-data
  artifact. Streamlit AppTest verified provenance display, 100 held-out predictions
  equal to direct inference, valid probabilities, saved metric display, a download
  control, global/local explanations, and four rendered image elements.
- A simulated upload of an unlabeled real held-out CSV with reversed feature order
  produced identical predictions and preserved saved evaluation metrics; global
  and local explanations also succeeded. An incompatible upload showed the expected
  schema error without a prediction download.
- A real Streamlit process started at `http://127.0.0.1:8503` and its
  `/_stcore/health` returned **HTTP 200, `ok`**. Starting and probing the server
  required approved escalation because the sandbox blocked local socket access.
- Browser automation returned **“The browser access host is unavailable”**.
  Consequently, full browser appearance, native file-picker interaction, and actual
  browser download behavior remain **unverified**. AppTest simulated the upload
  byte boundary; it did not exercise a native file picker.

The original dashboard rounded scores to three decimals. Final review fixes that
display: accuracy `99.9706%`, precision `0.99996093`, recall `0.99953130`, F1
`0.99974607`, FPR `0.0053605%`, FP=1 and FN=12. The matrix renders integer counts.
The synthetic warnings are absent with the real model. Matplotlib used a temporary
font cache due to restricted home-directory writes; AppTest emitted its expected
bare-mode context warning. Neither prevented successful checks or figure export.
Evidence: `pytest.txt`, `pip-check.txt`, `automated-checks.json`,
[dashboard-validation.json](../reports/real-data/dashboard-validation.json), and
[server-health.json](../reports/real-data/server-health.json).

## Reproduction and course demonstration

From the repository root, with the pinned environment installed:

```bash
# Tests use temporary artifacts; the saved real model is preserved.
.venv/bin/python -m pytest -q
.venv/bin/python -m pip check

# Fixed baseline and a temporary RF clone for timing; no main-model overwrite.
.venv/bin/python -m scripts.compare_baseline

# This reloads the real model and performs UI checks; it never trains.
.venv/bin/python -m scripts.verify_real_dashboard
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8503
```

The original `scripts.validate_real_data` is retained for historical reproduction,
but overwrites the model and is not a demo setup step. Current checks use
`final-pytest.txt` and `final-dashboard-run.txt`; original test logs are preserved.
Timing will vary. Full model parameters, package
versions, dataset hash, and row counts are in the copied `metadata.json`.

For a demonstration, enable **Use saved held-out sample**, show the confusion
matrix and full-precision report, then generate global and local explanations.
Alternatively upload [heldout-demo.csv](../reports/real-data/heldout-demo.csv), a
100-row unlabeled sample from the held-out set. Ground truth and cleaned row IDs
are in `heldout-demo-labels.csv`. Explain false positives and false negatives using
the saved waterfall figures. Do not present a prediction on this demo subset as a
new independent evaluation.

All current evidence is under `reports/real-data/`. Earlier `reports/figures/`,
`reports/review-run/`, and `reports/SYNTHETIC_predictions.csv` are historical
synthetic outputs and must not be used as real-data evidence. Generated artifacts
are ignored by the existing `.gitignore`; this directory is not a Git checkout.
Copy/archive `reports/real-data/`, `models/`, source, requirements, and this document
for submission rather than assuming the results are version-controlled. The input
CSV should be retained locally with its hash and handled under provider terms.

## Limitations and outstanding validation

This is one binary, same-capture random holdout. Near-perfect results can reflect
the fixed attack scenario and strongly correlated flow characteristics. Removing
identifiers and exact duplicates does not eliminate temporal, host, or scenario
correlations. This CSV lacks the timestamp/IP information needed to establish a
time- or host-grouped holdout with the present workflow. Other capture days,
independent networks, attack families, and time-separated validation remain
unverified. There is no multiclass or unknown-attack evaluation.

There is no cross-validation variability estimate, independent external holdout,
calibration study, adversarial robustness test, or packet-level
revalidation of labels. SHAP uses a bounded 100-row sample, correlated features
can share attribution, and explanations describe this model rather than causation.
Runtime is a local offline benchmark, not an online deployment guarantee. These
boundaries should accompany the course presentation and any reported metrics.

Dataset citation requested by the provider: Iman Sharafaldin, Arash Habibi Lashkari,
and Ali A. Ghorbani, “Toward Generating a New Intrusion Detection Dataset and Intrusion
Traffic Characterization,” ICISSP, Portugal, 2018.


## Final review validation and error analysis

All **1 FP and 12 FN** are saved in
[error-examples.csv](../reports/real-data/error-examples.csv), with actual and
predicted labels, probabilities, cleaned row IDs and all 66 input features.
The dashboard shows these rows and saved first-FP/first-FN waterfall figures only
when the report's model hash matches the loaded artifact. False alarms can cause
needless investigations; missed attack flows illustrate false-negative costs.
Flow counts are not independent attack-incident counts. SHAP explains model
behavior, not causality or label correctness; correlated features share attribution.
The original global and local interpretation and evidence above remain applicable.

Current evidence: `final-pytest.txt`, `final-dashboard-run.txt`, refreshed
`dashboard-validation.json`, and `final-review-verification.json`. AppTest checks
real-model loading, precise metrics, FP/FN counts, all error rows, BENIGN/DDoS
predictions equal to direct inference, a generated export endpoint, compatible
reversed-column CSV input, incompatible input rejection, and global/local SHAP
additivity. Uploads preserve the saved evaluation scores. Synthetic test fixtures
are software checks only; they do not contribute to the reported research results.

The documented Streamlit launch command ran and the health endpoint returned
HTTP 200, `ok`. Browser automation again returned **“The browser access host is
unavailable”**. Visual layout, the native upload picker, and an actual browser
download still require manual validation; AppTest and server health do not replace
that smoke test. Fresh-machine dependency installation was not tested. See the
[demo and submission checklists](demo-checklists.md).

Final suite: **39 passed in 20.63 s** (exit 0). `pip check`: **No broken requirements found** (exit 0). Real-artifact AppTest and 100-row CLI export both exited 0; exported rows matched direct inference. The main model SHA-256 was verified unchanged against the comparison-run fingerprint.


## Subsequent real-browser smoke test

After the user opened the dashboard in Brave at `http://127.0.0.1:8501/`, native
Computer Use succeeded. The real model provenance, precise metrics, FP/FN counts,
confusion-matrix image, saved error table and FP/FN explanation elements were
confirmed. The saved sample produced 40 BENIGN and 60 DDoS predictions. Global
SHAP displayed its chart and importance table; local SHAP displayed the waterfall,
contributions and reconstruction caption.

The native macOS file picker uploaded `heldout-demo.csv`; Analyze CSV produced
100 predictions. Download prediction CSV opened the native Save dialog, and Brave
reported the 2,354-byte download Done. The saved `browser-smoke-predictions.csv`
was read back and all 100 predictions and probabilities matched direct inference.
Evidence: [browser-smoke-test.json](../reports/real-data/browser-smoke-test.json).
Earlier browser-unavailable statements describe prior attempts and are superseded
by this successful test. No model was retrained or replaced.

Observed UI behavior: some Streamlit reruns returned to Overview; reopening the
Explainable AI tab showed the completed SHAP results. This smoke test does not
establish compatibility with every browser or a fresh-machine installation.
