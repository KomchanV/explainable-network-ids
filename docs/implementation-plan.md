# Implementation plan

Goal: a reproducible offline BENIGN/DDoS CSV classifier with a Streamlit dashboard.
Use one sklearn pipeline and one local Joblib bundle; no services or database.
The supplied specification authorizes implementation without intermediate approvals.

- [x] Test CSV parsing, normalized headers, target filtering, deduplication, and identifiers.
  Implement in `src/data_loader.py`; reject ambiguous headers and malformed files.
- [x] Test train-only feature selection, medians, schema errors, and column order.
  Implement numeric conversion, infinity handling, constant/all-missing removal in
  `src/preprocess.py`, inside the fitted pipeline.
- [x] Test stratified splitting, post-split subsampling, persistence, and metrics.
  Implement `src/train.py`, `src/evaluate.py`, and `src/predict.py`.
- [x] Test SHAP class extraction and probability additivity on fitted predictions.
  Implement bounded global/local explanations in `src/explain.py`.
- [x] Test dashboard with Streamlit AppTest; implement `app.py` using native components.
- [x] Run pytest, synthetic training and prediction CLIs, and a real Streamlit startup.
  Record actual results and dataset limitations in `README.md` and `reports/`.

Validation data: deterministic synthetic fixture only unless CIC-IDS2017 is supplied.
Do not use synthetic scores as evidence of intrusion detection effectiveness.
Initial implementation: 28 tests passed; synthetic CLI workflow and local server health verified.
Independent review found the documented duplicate CIC header issue; a regression
fixture and narrowly scoped parser compatibility rule now cover that case.
Follow-up requirements review: 37 tests passed. Fixed NUL truncation, suffixed
target/identifier leakage, and incomplete artifact loading; repeated the synthetic
training, reloading, unlabeled inference, SHAP, and Streamlit health checks.
