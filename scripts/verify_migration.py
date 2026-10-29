"""Read-only trusted-artifact checks. Never fits a model or changes an artifact."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np
import pandas as pd

from src.predict import load_artifact, predict_batch
from src.explain import explain_flows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, default=Path('models/model.joblib'))
    parser.add_argument('--baseline', type=Path, help='Optional pre-migration JSON predictions and SHA-256')
    args = parser.parse_args()
    if not args.model.is_file():
        parser.exit(2, 'Trusted model is unavailable; compatibility check requires a local artifact.\n')
    before = hashlib.sha256(args.model.read_bytes()).hexdigest()
    artifact = load_artifact(args.model)
    assert type(artifact['pipeline'].named_steps['features']).__module__ == 'src.preprocess'
    sample = artifact['explanation_sample']
    predictions, _ = predict_batch(artifact, sample)
    pipeline = artifact['pipeline']
    np.testing.assert_array_equal(predictions.prediction,
                                  np.where(pipeline.predict(sample) == 1, 'DDoS', 'BENIGN'))
    np.testing.assert_allclose(predictions.ddos_probability,
                               pipeline.predict_proba(sample)[:, 1], atol=1e-12, rtol=0)
    baseline_checked = False
    if args.baseline:
        baseline = json.loads(args.baseline.read_text())
        assert baseline['sha256'] == before, 'Artifact bytes changed since baseline'
        expected = pd.DataFrame(baseline['predictions'])
        np.testing.assert_array_equal(predictions.prediction, expected.prediction)
        np.testing.assert_array_equal(predictions.row_number, expected.row_number)
        np.testing.assert_allclose(predictions.ddos_probability, expected.ddos_probability, atol=1e-12, rtol=0)
        baseline_checked = True
    explanation = explain_flows(artifact, sample, max_samples=100)
    reconstructed = explanation.base_values + explanation.values.sum(axis=1)
    np.testing.assert_allclose(reconstructed, predictions.ddos_probability, atol=1e-6, rtol=1e-5)
    with tempfile.TemporaryDirectory(prefix='ids-migration-') as folder:
        csv = Path(folder) / 'flows.csv'
        output = Path(folder) / 'predictions.csv'
        sample.to_csv(csv, index=False)
        subprocess.run([sys.executable, '-m', 'src.predict', '--model', str(args.model.resolve()),
                        '--data', str(csv), '--output', str(output)], check=True, capture_output=True)
        cli = pd.read_csv(output)
        np.testing.assert_array_equal(cli.prediction, predictions.prediction)
        np.testing.assert_allclose(cli.ddos_probability, predictions.ddos_probability, atol=1e-12, rtol=0)
    assert before == hashlib.sha256(args.model.read_bytes()).hexdigest(), 'Artifact changed'
    print(json.dumps({'artifact_sha256': before, 'provenance': artifact['metadata']['provenance'],
                      'rows': len(sample), 'pre_migration_baseline_compared': baseline_checked,
                      'cli_parity': True, 'pipeline_parity': True, 'shap_reconstruction': True,
                      'max_shap_reconstruction_error': float(np.max(np.abs(reconstructed - predictions.ddos_probability))),
                      'artifact_unchanged': True}, indent=2))


if __name__ == '__main__':
    main()
