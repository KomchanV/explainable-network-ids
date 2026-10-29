"""Run the existing real-data experiment and preserve its measurement evidence.

Run from the project root: .venv/bin/python -m scripts.validate_real_data
This intentionally trains only on the supplied real CSV, never on a fixture.
"""

from datetime import datetime
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import time
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import ConfusionMatrixDisplay
from sklearn.model_selection import train_test_split

from src.data_loader import load_training_data, read_csv
from src.evaluate import classification_metrics
from src.predict import load_artifact, predict_batch
from src.train import train_model


DATA = Path('data/raw/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv')
OUT = Path('reports/real-data')


def save_json(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def counts(y):
    return {str(int(k)): int(v) for k, v in y.value_counts().sort_index().items()}


def measure(call, repetitions):
    samples = []
    for _ in range(repetitions):
        start = time.perf_counter()
        call()
        samples.append((time.perf_counter() - start) * 1000)
    return {'repetitions': repetitions, 'mean_ms': float(np.mean(samples)),
            'median_ms': float(np.median(samples)),
            'p95_ms': float(np.percentile(samples, 95)),
            'min_ms': float(np.min(samples)), 'max_ms': float(np.max(samples)),
            'samples_ms': samples}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'figures').mkdir(exist_ok=True)
    if not DATA.is_file():
        raise FileNotFoundError(f'Required real dataset missing: {DATA}')
    started = datetime.now(ZoneInfo('Asia/Bangkok')).isoformat()
    raw = read_csv(DATA)
    candidate = raw.drop(columns=['Label', 'Destination Port', 'Fwd Header Length.1'])
    converted = candidate.apply(pd.to_numeric, errors='coerce')
    stats = {
        'file': str(DATA), 'file_bytes': DATA.stat().st_size,
        'raw_rows': len(raw), 'raw_columns': len(raw.columns),
        'raw_label_counts': {str(k): int(v) for k, v in raw.Label.value_counts(dropna=False).items()},
        'candidate_numeric_invalid_tokens': int((candidate.notna() & converted.isna()).sum().sum()),
        'candidate_missing_cells_raw': int(converted.isna().sum().sum()),
        'candidate_infinite_cells_raw': int(np.isinf(converted).sum().sum()),
    }
    del raw, candidate, converted
    print('Training default 100-tree Random Forest on the real CSV...', flush=True)
    start = time.perf_counter()
    train_model(DATA, 'models', provenance='cic-ids2017')
    timings = {'training_workflow_seconds': time.perf_counter() - start}
    start = time.perf_counter()
    artifact = load_artifact()
    timings['artifact_reload_seconds'] = time.perf_counter() - start
    assert artifact['metadata']['provenance'] == 'cic-ids2017'
    assert artifact['metadata']['dataset_filename'] == DATA.name
    with DATA.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    assert digest == artifact['metadata']['dataset_sha256']
    for name in ['metadata.json', 'metrics.json', 'feature_schema.json']:
        shutil.copy2(Path('models') / name, OUT / name)

    # Reconstruct the untouched deterministic split; do not fit another model.
    X, y, loading = load_training_data(DATA)
    train, test, y_train, y_test = train_test_split(
        X, y, test_size=.2, stratify=y, random_state=42)
    pipeline = artifact['pipeline']
    schema = artifact['feature_schema']
    np.testing.assert_array_equal(
        schema, train.columns[train.nunique(dropna=True) > 1].tolist())
    np.testing.assert_allclose(pipeline.named_steps['imputer'].statistics_,
                               train[schema].median().to_numpy())
    assert set(train.index).isdisjoint(test.index)
    train_hashes = set(pd.util.hash_pandas_object(train[schema], index=False))
    test_hashes = set(pd.util.hash_pandas_object(test[schema], index=False))
    assert not train_hashes.intersection(test_hashes)
    transformed_train = pipeline[:-1].transform(train)
    transformed_test = pipeline[:-1].transform(test)
    imputed_train_hashes = set(pd.util.hash_pandas_object(pd.DataFrame(transformed_train), index=False))
    imputed_test_hashes = set(pd.util.hash_pandas_object(pd.DataFrame(transformed_test), index=False))
    assert not imputed_train_hashes.intersection(imputed_test_hashes)
    del transformed_train, transformed_test
    start = time.perf_counter()
    prediction = pipeline.predict(test)
    probability = pipeline.predict_proba(test)[:, 1]
    timings['full_test_predict_and_predict_proba_seconds'] = time.perf_counter() - start
    metrics = classification_metrics(y_test, prediction)
    assert metrics == artifact['metrics']
    assert artifact['metadata']['train_rows'] == len(train)
    assert artifact['metadata']['test_rows'] == len(test)
    assert loading == artifact['metadata']['loading']
    save_json('leakage-audit.json', {
        'split_indices_disjoint': True, 'shared_feature_hashes_before_imputation': 0,
        'shared_feature_hashes_after_imputation': 0,
        'selection_matches_training_only_variation': True,
        'imputer_matches_training_only_medians': True,
        'reloaded_model_metrics_match_independent_evaluation': True,
        'dataset_sha256_matches_artifact': True,
        'caveat': 'Exact-row and fitting checks do not remove correlated flows from the same capture.'})
    stats.update({'cleaning': loading, 'retained_class_counts': counts(y),
                  'train_class_counts': counts(y_train), 'test_class_counts': counts(y_test),
                  'train_rows': len(train), 'test_rows': len(test),
                  'candidate_features': X.shape[1], 'selected_features': len(schema),
                  'cleaned_missing_cells': int(X.isna().sum().sum()),
                  'cleaned_rows_with_missing': int(X.isna().any(axis=1).sum()),
                  'dropped_train_constant_or_empty': pipeline.named_steps['features'].dropped_columns_})
    save_json('dataset-statistics.json', stats)
    pd.DataFrame([metrics]).drop(columns='confusion_matrix').to_csv(OUT / 'metrics.csv', index=False)
    matrix = np.asarray(metrics['confusion_matrix'])
    pd.DataFrame(matrix, index=['actual_BENIGN', 'actual_DDoS'],
                 columns=['predicted_BENIGN', 'predicted_DDoS']).to_csv(OUT / 'confusion-matrix.csv')
    fig, ax = plt.subplots(figsize=(6, 5))
    ConfusionMatrixDisplay(matrix, display_labels=['BENIGN', 'DDoS']).plot(
        ax=ax, cmap='Blues', colorbar=False, values_format='d')
    ax.set_title(f'Real Friday holdout · {len(test):,} flows')
    fig.tight_layout()
    fig.savefig(OUT / 'figures/confusion-matrix.png', dpi=160)
    plt.close(fig)
    results = pd.DataFrame({'retained_row_id': test.index, 'true_label': y_test.to_numpy(),
                            'predicted_label': prediction, 'ddos_probability': probability})
    results.to_csv(OUT / 'heldout-predictions.csv', index=False)
    pd.DataFrame({'retained_row_id': X.index,
                  'split': np.where(X.index.isin(test.index), 'test', 'train')}).to_csv(
                      OUT / 'split-membership.csv', index=False)
    sample = test.loc[:, schema].sample(n=min(100, len(test)), random_state=42)
    pd.testing.assert_frame_equal(sample.reset_index(drop=True), artifact['explanation_sample'])
    sample.to_csv(OUT / 'heldout-demo.csv', index=False)
    pd.DataFrame({'sample_row_1based': np.arange(1, len(sample) + 1),
                  'retained_row_id': sample.index, 'true_label': y.loc[sample.index].to_numpy()}).to_csv(
                      OUT / 'heldout-demo-labels.csv', index=False)

    print('Independent evaluation:', json.dumps(metrics), flush=True)
    one = sample.iloc[[0]]
    batch = test.iloc[:1000]
    # Exclude warm-up and parsing/model deserialization from steady-state latency.
    pipeline.predict(one)
    predict_batch(artifact, one)
    timings['pipeline_predict_one'] = measure(lambda: pipeline.predict(one), 100)
    timings['predict_batch_one'] = measure(lambda: predict_batch(artifact, one), 100)
    timings['predict_batch_1000'] = measure(lambda: predict_batch(artifact, batch), 20)
    start = time.perf_counter()
    from src.explain import explain_flows, global_importance, importance_figure, waterfall_figure
    timings['explanation_module_import_seconds'] = time.perf_counter() - start
    start = time.perf_counter()
    explanation = explain_flows(artifact, sample)
    timings['first_global_shap_100_seconds'] = time.perf_counter() - start
    timings['local_shap_one'] = measure(lambda: explain_flows(artifact, one, max_samples=1), 10)
    timings['global_shap_100'] = measure(lambda: explain_flows(artifact, sample), 3)
    global_importance(explanation).to_csv(OUT / 'global-importance.csv', index=False)
    pd.DataFrame(explanation.values, columns=schema, index=sample.index).rename_axis(
        'retained_row_id').to_csv(OUT / 'global-shap-values.csv')
    fig = importance_figure(explanation)
    fig.savefig(OUT / 'figures/global-shap.png', dpi=160, bbox_inches='tight')
    plt.close(fig)
    reconstructed = explanation.base_values + explanation.values.sum(axis=1)
    sample_probs = pipeline.predict_proba(sample)[:, 1]
    max_error = float(np.max(np.abs(reconstructed - sample_probs)))
    np.testing.assert_allclose(reconstructed, sample_probs, atol=1e-6, rtol=1e-5)
    pd.DataFrame({'retained_row_id': sample.index,
                  'base_value': explanation.base_values,
                  'shap_sum': explanation.values.sum(axis=1),
                  'reconstructed_probability': reconstructed,
                  'model_ddos_probability': sample_probs}).to_csv(OUT / 'shap-additivity.csv', index=False)
    local_rows = []
    for outcome, actual, predicted in [('TN', 0, 0), ('TP', 1, 1), ('FP', 0, 1), ('FN', 1, 0)]:
        candidates = results.loc[(results.true_label == actual) & (results.predicted_label == predicted)]
        if candidates.empty:
            continue
        # First row in deterministic held-out order, no cherry-picking by probability.
        row_id = int(candidates.iloc[0].retained_row_id)
        local = explain_flows(artifact, test.loc[[row_id]], max_samples=1)[0]
        p = float(candidates.iloc[0].ddos_probability)
        reconstructed_p = float(local.base_values + local.values.sum())
        assert np.isclose(reconstructed_p, p, atol=1e-6)
        fig = waterfall_figure(local)
        fig.savefig(OUT / f'figures/local-{outcome}.png', dpi=160, bbox_inches='tight')
        plt.close(fig)
        pd.DataFrame({'feature': schema, 'model_input_value': local.data,
                      'shap_ddos_probability_units': local.values}).sort_values(
                          'shap_ddos_probability_units', key=abs, ascending=False).to_csv(
                              OUT / f'local-{outcome}.csv', index=False)
        local_rows.append({'outcome': outcome, 'retained_row_id': row_id,
                           'actual': actual, 'predicted': predicted, 'ddos_probability': p,
                           'base_value': float(local.base_values),
                           'reconstructed_probability': reconstructed_p})
    save_json('shap-validation.json', {'global_sample_rows': len(sample),
              'sample_policy': '100 held-out rows sampled without replacement, seed 42',
              'global_sample_class_counts': counts(y.loc[sample.index]),
              'global_max_probability_reconstruction_error': max_error,
              'local_examples': local_rows, 'units': 'DDoS probability',
              'feature_perturbation': 'tree_path_dependent', 'background': 'training tree path counts'})
    save_json('timings.json', timings)
    hardware = {}
    for key in ['machdep.cpu.brand_string', 'hw.memsize', 'hw.logicalcpu']:
        r = subprocess.run(['sysctl', '-n', key], capture_output=True, text=True)
        hardware[key] = r.stdout.strip() if r.returncode == 0 else 'unavailable'
    save_json('environment.json', {'started_at_bangkok': started,
              'finished_at_bangkok': datetime.now(ZoneInfo('Asia/Bangkok')).isoformat(),
              'platform': platform.platform(), 'machine': platform.machine(),
              'python': platform.python_version(), 'logical_cpu_count': os.cpu_count(),
              'hardware': hardware,
              'packages': {p: version(p) for p in ['numpy', 'pandas', 'scikit-learn', 'shap',
                                                  'numba', 'matplotlib', 'streamlit', 'joblib', 'pytest']}})
    with Path('models/model.joblib').open('rb') as stream:
        model_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    save_json('run-summary.json', {'status': 'training_evaluation_explanations_completed',
              'dataset_sha256': digest, 'model_sha256': model_hash,
              'model_path': 'models/model.joblib', 'metrics': metrics,
              'dashboard_verification': 'recorded separately in dashboard-validation.json',
              'no_hyperparameter_search': True, 'no_training_subsample': True})
    print('Experiment saved to', OUT, flush=True)


if __name__ == '__main__':
    main()
