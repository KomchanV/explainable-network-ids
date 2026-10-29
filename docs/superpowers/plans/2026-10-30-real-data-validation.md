# Real-data validation plan

**Goal:** Validate the existing BENIGN/DDoS MVP on the supplied Friday CIC-IDS2017 CSV and preserve reproducible academic evidence.

**Architecture:** Keep the existing loader, sklearn Pipeline, Random Forest, SHAP helpers, and Streamlit app. Add only an experiment runner and documentation; change production behavior only for a reproduced defect.

**Execution:** Inline in this session, as requested. This folder is not a Git checkout; no branch or worktree operations apply.

- [x] Inspect dataset, source, dependencies, and tests. Load the actual CSV and audit the deterministic split for identical feature overlap.
- [x] Run `.venv/bin/python -m pytest -q` and `.venv/bin/python -m pip check`, saving output under `reports/real-data/`. Run synthetic fixture tests before the real experiment only.
- [x] Add `scripts/validate_real_data.py`: call the existing `train_model` with default settings and real provenance; reconstruct the split without fitting; assert train-only feature selection and medians, disjoint indices and feature hashes, saved metrics, and model provenance.
- [x] Save complete held-out predictions, indices, dataset statistics, metrics, confusion matrix, SHAP attribution tables and figures, additivity checks, environment information, timings, and hashes under `reports/real-data/`. Use the saved held-out sample for global explanations and actual held-out TP/TN/FP/FN examples for local explanations. Do not tune on the test set.
- [x] Exercise the real artifact using Streamlit AppTest (sample, upload, prediction, metric display, global/local SHAP, and download control). Start a real server, check health, and attempt a browser visual check. Save explicit verification scope. Browser host unavailable; AppTest and HTTP health passed.
- [x] Write `docs/experiment-results.md`, update stale README validation statements, inspect generated figures, and verify report/model consistency. Clearly document unverified provenance, correlated same-capture splitting, benchmark scope, and generalization limitations. Do not retrain synthetic data after the real experiment.
