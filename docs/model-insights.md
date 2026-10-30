# Model Insights

Open **Model Insights** in primary navigation or navigate directly to `/model-insights`.
No CSV upload or analysis session is required. Refresh evaluation reloads the API snapshot,
not the Joblib file. Model availability is confirmed by a successful response; absent or
invalid models and disconnected APIs show an actionable error with a retry button.

## Saved evaluation and interpretation

`GET /model/evaluation` reads `metrics` and allowlisted `metadata` from the already-loaded
trusted artifact. It never fits, predicts, runs SHAP, or deserializes a model. The model
identifier is the SHA-256 of the artifact loaded at server startup. Dataset SHA-256 is a
separate saved fingerprint of the training CSV. Neither digest independently authenticates
the dataset. Source labels are operator-supplied: `synthetic`, `cic-ids2017`, or `unspecified`.
Synthetic fixtures are explicitly disclosed as testing evidence, not security evidence.

DDoS = 1 is positive; BENIGN = 0 is negative. The semantic HTML table uses actual labels
as rows and predicted labels as columns, in scikit-learn `[0, 1]` order:

| Actual / Predicted | BENIGN | DDoS |
| --- | --- | --- |
| BENIGN | TN | FP |
| DDoS | FN | TP |

Accuracy = (TN + TP) / total; precision = TP / (TP + FP); recall = TP / (TP + FN);
F1 = 2TP / (2TP + FP + FN). Precision, recall and F1 use zero when their denominator is
zero, matching `src.evaluate.classification_metrics`. FPR = FP / (FP + TN), or null when
there are no actual BENIGN rows. Undefined FPR is displayed as **Not defined**.
Metrics near boundaries retain small errors instead of rounding an imperfect score to
100%. Extremely small residual errors are shown in scientific notation.

Validation requires nonnegative integer matrix cells, positive evaluated rows, matching
matrix/test/evaluation totals, finite bounded metrics, the fixed label mapping, and
scores consistent with the matrix (relative tolerance 1e-9, absolute tolerance 1e-12).
Inconsistency returns HTTP 500 `invalid_evaluation`; no saved values are repaired.
Unavailable models return HTTP 503 `model_unavailable`. Both use the existing error envelope.
Artifact loading and existing `/model` behavior are unchanged.

Missing optional metadata is returned as null and shown as **Not recorded**. The API
allowlist excludes training data, filesystem paths, serialized objects and unbounded
parameter dumps. Dataset filenames are stripped of directory components.

## Training methodology

The current implementation loads numeric network-flow features and excludes identifiers
and labels. Invalid/nonbinary labels and duplicate rows are removed before splitting.
A seed-controlled stratified split defaults to 80/20. Optional stratified training
subsampling happens after splitting. Numeric feature selection drops unusable training
columns; median imputation and the Random Forest are fitted only on training data.
Held-out labels produce the saved evaluation. See `src/data_loader.py`, `src/preprocess.py`,
and `src/train.py` for the authoritative implementation.

The page distinguishes this description of current code from historical evidence.
Saved test fraction, random seed, sample counts and class counts come from metadata;
missing historical settings are never filled using current defaults. Training rows before
subsampling are displayed separately from fitted training rows.

## Scientific limitations

Training and testing originate from the same capture/dataset scenario. A held-out split
does not establish generalization to unseen networks or robustness against adaptive
attacks. Distribution shift may change performance. Probabilities are not calibrated
confidence or threat-severity scores. SHAP describes model behavior, not causal evidence.
The system remains an offline academic prototype and is not production-ready.

**Current Uploaded Analysis** contains predictions on a user CSV. Those predicted labels
are not ground truth; analysis counts cannot produce measured accuracy or F1. The saved
held-out metrics must never be described as accuracy on that uploaded CSV.
