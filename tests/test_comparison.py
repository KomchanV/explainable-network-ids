import hashlib
from pathlib import Path

import pandas as pd

from src.train import train_model


def test_comparison_reuses_split_and_preserves_model(flow_csv, tmp_path):
    from scripts.compare_baseline import compare
    model = tmp_path / 'model'
    artifact = train_model(flow_csv, model, n_estimators=5, provenance='synthetic')
    path = model / 'model.joblib'
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    output = tmp_path / 'comparison'
    result = compare(flow_csv, path, output)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    assert result['models']['Random Forest']['metrics'] == artifact['metrics']
    assert result['models']['Decision Tree']['metrics']['evaluated_rows'] == artifact['metadata']['test_rows']
    assert all(row['fit_seconds'] > 0 and row['inference_seconds'] > 0 for row in result['models'].values())
    table = pd.read_csv(output / 'baseline-comparison.csv')
    assert len(table) == 2
    assert (output / 'figures/baseline-performance.png').is_file()
    assert (output / 'error-examples.csv').is_file()
