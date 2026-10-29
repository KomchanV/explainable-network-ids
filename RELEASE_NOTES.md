# v0.1.0-alpha.1 release notes

## Overview

This first alpha packages the repository as a reproducible academic prototype for
offline binary classification of network-flow CSVs as BENIGN or DDoS. It includes
training, evaluation, saved-model inference, SHAP explanations, and a local
Streamlit dashboard. It is not a live intrusion-detection or production system.

## Included capabilities

- Strict CSV loading, label normalization, identifier exclusion, deduplication,
  and training-only preprocessing.
- Deterministic 80/20 stratified evaluation and a saved Random Forest pipeline.
- Schema-checked CLI prediction and downloadable dashboard results.
- Global and local positive-class SHAP explanations with additivity validation.
- Synthetic smoke-data generation and real-data validation/comparison scripts.
- Pytest coverage of core workflows and Streamlit application behavior.

## Verified experimental evidence

The documented 30 October 2026 CIC-IDS2017 run evaluated 44,258 held-out rows and
recorded 99.970627% accuracy, 99.996093% DDoS precision, 99.953130% recall, and
99.974607% F1. These results are from a same-capture random holdout and do not
establish performance on other networks, time periods, or attack types. See
`docs/experiment-results.md` for the methodology, exact dataset hash, confusion
matrix, baseline comparison, timings, and validation scope.

## Install and run

Use Python 3.11 through 3.13 and run from the repository root:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
streamlit run app.py
```

The dashboard requires a trusted local `models/model.joblib`. Create one with the
documented CIC-IDS2017 workflow or use the isolated synthetic smoke workflow in
`README.md`. Raw datasets and generated model/report artifacts are intentionally
not included in Git.

## Known limitations

- Binary closed-set, offline classification only; no packet capture or monitoring.
- Same-capture random-split evidence does not demonstrate external generalization.
- Model probabilities are uncalibrated and SHAP values are descriptive, not causal.
- CSV loading and cleaned datasets must fit in memory.
- Native browser appearance and file-picker/download behavior are not covered by
  the automated Streamlit AppTest suite.
- Joblib artifacts must only be loaded from trusted sources.
