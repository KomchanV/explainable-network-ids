"""Schema-checked batch inference and trusted local artifact loading."""

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from src.data_loader import normalize_columns, numeric_frame, read_csv


def load_artifact(path='models/model.joblib'):
    """Only call on trusted files: Joblib/Pickle can execute arbitrary code."""
    try:
        artifact = joblib.load(path)
    except OSError:
        raise
    except Exception as exc:
        raise ValueError('Could not read model artifact. Use the pinned dependencies or retrain using src.train.') from exc
    required = {'pipeline', 'feature_schema', 'metrics', 'metadata', 'explanation_sample', 'label_mapping'}
    if not isinstance(artifact, dict) or artifact.get('format_version') != 1 or not required <= artifact.keys():
        raise ValueError('Unsupported or incomplete model artifact. Retrain using src.train.')
    try:
        pipeline, schema = artifact['pipeline'], artifact['feature_schema']
        metadata, metrics = artifact['metadata'], artifact['metrics']
        metadata_keys = {'provenance', 'dataset_filename', 'train_rows', 'test_rows', 'random_state'}
        score_keys = {'accuracy', 'precision', 'recall', 'f1'}
        metrics_keys = score_keys | {'false_positive_rate', 'confusion_matrix', 'evaluated_rows'}
        if (not isinstance(pipeline, Pipeline)
                or not isinstance(schema, list) or not schema
                or not all(isinstance(c, str) for c in schema) or len(set(schema)) != len(schema)
                or not isinstance(metadata, dict) or not metadata_keys <= metadata.keys()
                or not isinstance(metrics, dict) or not metrics_keys <= metrics.keys()
                or artifact['label_mapping'] != {'BENIGN': 0, 'DDoS': 1}):
            raise ValueError('Incomplete bundle structure.')
        if (pipeline.named_steps['features'].get_feature_names_out().tolist() != schema
                or pipeline.named_steps['classifier'].classes_.tolist() != [0, 1]
                or len(pipeline.named_steps['imputer'].statistics_) != len(schema)
                or pipeline.named_steps['classifier'].n_features_in_ != len(schema)):
            raise ValueError('Inconsistent fitted feature schema or class mapping.')
        if (metadata['provenance'] not in {'synthetic', 'cic-ids2017', 'unspecified'}
                or not isinstance(metadata['dataset_filename'], str)
                or not isinstance(metadata['random_state'], (int, np.integer))
                or any(not isinstance(metadata[k], (int, np.integer)) or metadata[k] <= 0
                       for k in ['train_rows', 'test_rows'])
                or metrics['evaluated_rows'] != metadata['test_rows']):
            raise ValueError('Invalid evaluation provenance or row counts.')
        scores = [metrics[k] for k in score_keys]
        if metrics['false_positive_rate'] is not None:
            scores.append(metrics['false_positive_rate'])
        if any(not isinstance(s, (int, float)) or not np.isfinite(s) or not 0 <= s <= 1 for s in scores):
            raise ValueError('Invalid classification scores.')
        matrix = np.asarray(metrics['confusion_matrix'], dtype=float)
        if (matrix.shape != (2, 2) or not np.isfinite(matrix).all()
                or (matrix < 0).any() or (matrix != np.floor(matrix)).any()
                or matrix.sum() != metadata['test_rows']):
            raise ValueError('Invalid confusion matrix.')
        sample = artifact['explanation_sample']
        if not isinstance(sample, pd.DataFrame) or sample.empty or sample.columns.tolist() != schema:
            raise ValueError('Invalid saved explanation sample.')
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(f'Invalid model artifact: {exc} Retrain using src.train.') from exc
    return artifact


def validate_features(artifact, frame):
    frame = normalize_columns(frame)
    if frame.empty:
        raise ValueError('No network flow rows to predict.')
    schema = artifact['feature_schema']
    missing = [c for c in schema if c not in frame]
    if missing:
        raise ValueError(f'Missing required feature columns: {", ".join(missing)}')
    selected = frame.loc[:, schema]
    converted = selected.apply(pd.to_numeric, errors='coerce')
    invalid = selected.notna() & converted.isna()
    if invalid.any().any():
        bad = invalid.columns[invalid.any()].tolist()
        raise ValueError(f'Non-numeric values in required feature columns: {", ".join(bad)}. '
                         'Use numeric values or empty cells for missing data.')
    converted = numeric_frame(converted)
    if converted.isna().all(axis=1).any():
        raise ValueError('At least one flow has no usable feature values; all required features are missing.')
    notes = {
        'ignored_columns': [c for c in frame if c not in schema],
        'imputed_cells': int(converted.isna().sum().sum()),
    }
    return converted, notes


def predict_batch(artifact, frame):
    features, notes = validate_features(artifact, frame)
    model = artifact['pipeline']
    probability = model.predict_proba(features)
    prediction = model.predict(features)
    return pd.DataFrame({
        'row_number': np.arange(1, len(features) + 1),
        'prediction': np.where(prediction == 1, 'DDoS', 'BENIGN'),
        'ddos_probability': probability[:, 1],
    }), notes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', default='models/model.joblib', type=Path)
    parser.add_argument('--data', required=True, type=Path)
    parser.add_argument('--output', default='reports/predictions.csv', type=Path)
    args = parser.parse_args()
    try:
        artifact = load_artifact(args.model)
        result, notes = predict_batch(artifact, read_csv(args.data))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(args.output, index=False)
    except (OSError, ValueError, EOFError) as exc:
        parser.exit(2, f'Prediction failed: {exc}\n')
    print(f"Provenance: {artifact['metadata']['provenance']}")
    print(f'Saved {len(result):,} predictions to {args.output}')
    print(f"Ignored columns: {notes['ignored_columns']}; imputed cells: {notes['imputed_cells']}")


if __name__ == '__main__':
    main()
