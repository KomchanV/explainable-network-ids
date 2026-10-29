"""Train and evaluate a reproducible offline Random Forest pipeline."""

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from src.data_loader import load_training_data
from src.evaluate import classification_metrics
from src.preprocess import NumericFeatures


def _class_counts(y):
    return {str(int(k)): int(v) for k, v in y.value_counts().sort_index().items()}


def train_model(data, output_dir='models', *, max_train_rows=None, n_estimators=100,
                random_state=42, provenance='unspecified'):
    if max_train_rows is not None and max_train_rows < 2:
        raise ValueError('max_train_rows must be at least 2 to retain both classes.')
    if n_estimators < 1:
        raise ValueError('n_estimators must be positive.')
    X, y, loading = load_training_data(data)
    if y.nunique() != 2:
        raise ValueError('Training requires both BENIGN and DDoS after filtering and deduplication.')
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=.2, stratify=y, random_state=random_state)
        train_rows_before = len(X_train)
        if max_train_rows is not None and max_train_rows < len(X_train):
            X_train, _, y_train, _ = train_test_split(
                X_train, y_train, train_size=max_train_rows,
                stratify=y_train, random_state=random_state)
    except ValueError as exc:
        raise ValueError(f'Insufficient rows per class for stratified splitting/subsampling: {exc}') from exc
    if y_train.nunique() != 2 or y_test.nunique() != 2:
        raise ValueError('The train and test splits must both contain BENIGN and DDoS; provide more rows.')

    pipeline = Pipeline([
        ('features', NumericFeatures()),
        ('imputer', SimpleImputer(strategy='median')),
        ('classifier', RandomForestClassifier(n_estimators=n_estimators, max_depth=12,
                                               random_state=random_state, n_jobs=-1)),
    ])
    pipeline.fit(X_train, y_train)
    metrics = classification_metrics(y_test, pipeline.predict(X_test))
    features = pipeline.named_steps['features']
    schema = features.get_feature_names_out().tolist()
    with open(data, 'rb') as stream:
        fingerprint = hashlib.file_digest(stream, 'sha256').hexdigest()
    metadata = {
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'provenance': provenance,
        'dataset_filename': Path(data).name,
        'dataset_sha256': fingerprint,
        'loading': loading,
        'random_state': random_state,
        'test_fraction': .2,
        'train_rows_before_subsampling': train_rows_before,
        'train_rows': len(X_train),
        'test_rows': len(X_test),
        'train_class_counts': _class_counts(y_train),
        'test_class_counts': _class_counts(y_test),
        'dropped_training_columns': features.dropped_columns_,
        'classifier_parameters': pipeline.named_steps['classifier'].get_params(),
        'python_version': platform.python_version(),
        'package_versions': {n: version(n) for n in
                             ['numpy', 'pandas', 'scikit-learn', 'shap', 'joblib']},
    }
    # Feature-only held-out sample; not a SHAP background and never fitted.
    sample = X_test.loc[:, schema].sample(n=min(100, len(X_test)), random_state=random_state)
    artifact = {
        'format_version': 1,
        'pipeline': pipeline,
        'feature_schema': schema,
        'label_mapping': {'BENIGN': 0, 'DDoS': 1},
        'metrics': metrics,
        'metadata': metadata,
        'explanation_sample': sample.reset_index(drop=True),
    }
    folder = Path(output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    # Compression keeps the local demonstration artifact reasonably small.
    joblib.dump(artifact, folder / 'model.joblib', compress=3)
    for name, content in [('metrics', metrics), ('feature_schema', schema), ('metadata', metadata)]:
        (folder / f'{name}.json').write_text(json.dumps(content, indent=2, allow_nan=False) + '\n')
    return artifact


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True, type=Path)
    parser.add_argument('--output-dir', default='models', type=Path)
    parser.add_argument('--max-train-rows', type=int, default=None)
    parser.add_argument('--n-estimators', type=int, default=100)
    parser.add_argument('--provenance', choices=['cic-ids2017', 'synthetic', 'unspecified'],
                        default='unspecified', help='Recorded source type; does not verify dataset authenticity.')
    args = parser.parse_args()
    try:
        artifact = train_model(args.data, args.output_dir, max_train_rows=args.max_train_rows,
                               n_estimators=args.n_estimators, provenance=args.provenance)
    except (OSError, ValueError) as exc:
        parser.exit(2, f'Training failed: {exc}\n')
    print(f"Provenance: {artifact['metadata']['provenance']} | Labeled held-out evaluation")
    print(json.dumps(artifact['metrics'], indent=2))
    print(f'Saved model and reports to {args.output_dir}')


if __name__ == '__main__':
    main()
