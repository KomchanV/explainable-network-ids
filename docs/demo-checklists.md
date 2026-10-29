# Course demo and submission checklists

## Run from the project root

Use the existing pinned `.venv` and verified local model; no retraining is needed.

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pip check
.venv/bin/python -m scripts.compare_baseline
.venv/bin/python -m scripts.verify_real_dashboard
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8503
```

`compare_baseline` fits the Tree and a temporary RF clone for timing, checks the
saved model hash is unchanged, and refreshes comparison/error reports. It never
saves over the main model. Other original experiment reports stay unchanged.
The verified real-data artifact must remain in `models/model.joblib`. Tests train
small fixtures only in temporary folders. Do not run `src.synthetic`, `src.train`,
or `scripts.validate_real_data` as demo setup: the latter two can replace the model.
For a fresh machine install `requirements.txt` in a Python 3.13 virtual environment
as described in README; dependency installation on a fresh machine was not tested
in this review.

## Demo checklist

- [ ] Open http://127.0.0.1:8503 and confirm CIC-IDS2017 provenance, 66 features.
- [ ] Model performance: 44,258 held-out rows; accuracy 99.9706%; precision
      0.99996093; recall 0.99953130; F1 0.99974607; FPR 0.0053605%.
- [ ] Read actual matrix counts: TN 18,654; FP 1; FN 12; TP 25,591.
- [ ] Explain Tree tradeoff: 4 FP, 7 FN; higher accuracy here, no external validation.
- [ ] Enable **Use saved held-out sample**; show BENIGN and DDoS predictions.
- [ ] Generate global SHAP and explain mean absolute probability contributions.
- [ ] Select a flow and generate local SHAP; explain baseline plus contributions.
- [ ] Show all saved errors and first FP/FN explanations in Model performance.
- [ ] Disable sample, upload `reports/real-data/heldout-demo.csv`, click Analyze CSV.
- [ ] Download prediction CSV and open it; verify 100 rows, prediction labels,
      row_number and ddos_probability columns. This native-browser step passed in Brave; see `browser-smoke-test.json`.
- [ ] State: same-capture benchmark, not proof of new-network or unknown-attack detection.

AppTest covers the logic above. A subsequent real Brave smoke test also passed
using the native file picker and Save dialog; the downloaded 100-row CSV matched
direct inference. Evidence: `reports/real-data/browser-smoke-test.json`.

## Submission checklist

- [ ] Include source (`app.py`, `src/`, `scripts/`, `tests/`), pinned requirements,
      `.streamlit/`, README, and docs; exclude `.venv` and caches.
- [ ] Include trusted `models/model.joblib`, metadata, feature schema, metrics.
- [ ] Include `reports/real-data/` comparison tables/figures, original evaluation,
      split membership, predictions, SHAP/additivity, error examples and test logs.
- [ ] Include `docs/experiment-results.md` and this checklist.
- [ ] Preserve input dataset hash and provider citation; distribute the dataset
      according to provider terms. Keep historical synthetic reports clearly separate.
- [ ] Read `final-review-verification.json`; record manual browser validation if performed.
- [ ] Run the commands above from the submission root and retain outputs.
- [ ] Explain limitations: correlated flows, one split, no independent capture,
      no uncertainty estimate, uncalibrated probabilities, descriptive SHAP.

This workspace is not a Git checkout; ignored generated files must be explicitly
included in the submission archive. A fresh-machine installation is unverified.
