"""Compare a fixed Decision Tree with the preserved model; never overwrite it.

Run: .venv/bin/python -m scripts.compare_baseline
"""
import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier

from src.data_loader import load_training_data
from src.evaluate import classification_metrics
from src.predict import load_artifact


def compare(data, model, output):
    data, model, output = Path(data), Path(model), Path(output)
    artifact = load_artifact(model)
    metadata = artifact['metadata']
    digest = hashlib.sha256(data.read_bytes()).hexdigest()
    if digest != metadata['dataset_sha256']:
        raise ValueError('Dataset hash differs from the verified training input.')
    X, y, loading = load_training_data(data)
    train, test, y_train, y_test = train_test_split(
        X, y, test_size=metadata['test_fraction'], stratify=y,
        random_state=metadata['random_state'])
    if metadata['train_rows'] < len(train):
        train, _, y_train, _ = train_test_split(
            train, y_train, train_size=metadata['train_rows'], stratify=y_train,
            random_state=metadata['random_state'])
    assert len(test) == metadata['test_rows'] and loading == metadata['loading']
    pipeline = artifact['pipeline']
    schema = artifact['feature_schema']
    assert schema == train.columns[train.nunique(dropna=True) > 1].tolist()
    np.testing.assert_allclose(pipeline.named_steps['imputer'].statistics_, train[schema].median())
    # Reuse the already fitted train-only selectors and medians for both classifiers.
    train_values = pipeline[:-1].transform(train)
    test_values = pipeline[:-1].transform(test)
    saved_prediction = pipeline.predict(test)
    assert classification_metrics(y_test, saved_prediction) == artifact['metrics']
    membership = output / 'split-membership.csv'
    if membership.exists():
        saved = pd.read_csv(membership)
        assert set(saved.loc[saved.split == 'test', 'retained_row_id']) == set(test.index)
        assert set(saved.loc[saved.split == 'train', 'retained_row_id']) == set(train.index)
    # Fixed in advance; no validation/test-driven parameter search.
    estimators = {'Random Forest': clone(pipeline.named_steps['classifier']),
                  'Decision Tree': DecisionTreeClassifier(random_state=metadata['random_state'])}
    report = {'dataset_sha256': digest, 'model_sha256': hashlib.sha256(model.read_bytes()).hexdigest(),
              'train_rows': len(train), 'test_rows': len(test), 'features': schema,
              'policy': 'Same-capture stratified random split; fixed default Decision Tree, no tuning. '
                        'RF clone fitted only to measure classifier fit time and verify reproducibility; '
                        'saved RF remains main model. Fit excludes preprocessing. Inference is warmed '
                        'classifier predict on the full transformed holdout, median of 5 runs; '
                        'excludes parsing, preprocessing, probabilities and UI. Single fit per model.',
              'models': {}}
    rows = []
    for name, estimator in estimators.items():
        start = perf_counter()
        estimator.fit(train_values, y_train)
        fit_seconds = perf_counter() - start
        classifier = pipeline.named_steps['classifier'] if name == 'Random Forest' else estimator
        prediction = classifier.predict(test_values)  # warm-up
        if name == 'Random Forest':
            np.testing.assert_array_equal(estimator.predict(test_values), saved_prediction)
            np.testing.assert_array_equal(prediction, saved_prediction)
        timings = []
        for _ in range(5):
            start = perf_counter()
            classifier.predict(test_values)
            timings.append(perf_counter() - start)
        metrics = classification_metrics(y_test, prediction)
        entry = {'metrics': metrics, 'fit_seconds': fit_seconds,
                 'inference_seconds': float(np.median(timings)), 'inference_samples_seconds': timings,
                 'parameters': estimator.get_params()}
        report['models'][name] = entry
        tn, fp, fn, tp = np.array(metrics['confusion_matrix']).ravel()
        rows.append({'model': name, **{k: v for k, v in metrics.items() if k != 'confusion_matrix'},
                     'TN': tn, 'FP': fp, 'FN': fn, 'TP': tp,
                     'fit_seconds': fit_seconds, 'inference_seconds': entry['inference_seconds']})
    output.mkdir(parents=True, exist_ok=True)
    (output / 'figures').mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(output / 'baseline-comparison.csv', index=False)
    (output / 'baseline-comparison.json').write_text(json.dumps(report, indent=2) + '\n')
    errors = test.loc[np.asarray(y_test) != saved_prediction, schema].copy()
    errors.insert(0, 'retained_row_id', errors.index)
    errors['actual'] = y_test.loc[errors.index].map({0: 'BENIGN', 1: 'DDoS'})
    errors['predicted'] = np.where(saved_prediction[np.asarray(y_test) != saved_prediction] == 1, 'DDoS', 'BENIGN')
    errors['outcome'] = np.where(errors.actual == 'BENIGN', 'FP', 'FN')
    errors['ddos_probability'] = pipeline.predict_proba(test.loc[errors.index])[:, 1] if len(errors) else []
    errors.to_csv(output / 'error-examples.csv', index=False)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    table = pd.DataFrame(rows).set_index('model')
    (table[['accuracy', 'precision', 'recall', 'f1']] * 100).T.plot.bar(ax=axes[0])
    axes[0].set_ylabel('Percent'); axes[0].set_ylim(99, 100)
    axes[0].set_title('Same-capture holdout (axis truncated to 99–100%)')
    (table[['false_positive_rate']] * 100).T.plot.bar(ax=axes[1])
    axes[1].set_ylabel('FPR (%)'); axes[1].set_title('False alarms among actual BENIGN flows')
    for ax in axes:
        ax.tick_params(axis='x', rotation=0)
    fig.tight_layout(); fig.savefig(output / 'figures/baseline-performance.png', dpi=160); plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 4))
    table[['fit_seconds', 'inference_seconds']].T.plot.bar(ax=ax, logy=True)
    ax.set_ylabel('Seconds (log scale)'); ax.tick_params(axis='x', rotation=0)
    ax.set_title('Classifier fit and full-holdout prediction; shared transformed inputs')
    fig.tight_layout(); fig.savefig(output / 'figures/baseline-timing.png', dpi=160); plt.close(fig)
    assert hashlib.sha256(model.read_bytes()).hexdigest() == report['model_sha256']
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('data/raw/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv'))
    parser.add_argument('--model', type=Path, default=Path('models/model.joblib'))
    parser.add_argument('--output', type=Path, default=Path('reports/real-data'))
    args = parser.parse_args()
    report = compare(args.data, args.model, args.output)
    print(json.dumps(report['models'], indent=2))


if __name__ == '__main__':
    main()
