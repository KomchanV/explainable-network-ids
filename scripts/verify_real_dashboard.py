"""Verify the existing dashboard against the real artifact without any fitting."""

from io import BytesIO
import json
import os
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest

from src.predict import load_artifact, predict_batch


def healthy(app):
    assert not app.exception, [item.message for item in app.exception]
    assert not app.error, [item.value for item in app.error]


def main():
    model = Path('models/model.joblib').resolve()
    os.environ['IDS_MODEL_PATH'] = str(model)
    artifact = load_artifact(model)
    assert artifact['metadata']['provenance'] == 'cic-ids2017'
    app_file = str(Path('app.py').resolve())
    app = AppTest.from_file(app_file).run(timeout=60)
    healthy(app)
    assert not app.warning
    assert any('CIC-IDS2017' in item.value for item in app.info)
    app.checkbox[0].check().run(timeout=60)
    healthy(app)
    frame, result, _ = app.session_state['analyzed']
    pd.testing.assert_frame_equal(frame, artifact['explanation_sample'])
    expected, _ = predict_batch(artifact, frame)
    pd.testing.assert_frame_equal(result, expected)
    assert result.ddos_probability.between(0, 1).all()
    scores = {item.label: item.value for item in app.metric}
    assert scores['Analyzed flows'] == '100'
    for label, key in [('Accuracy', 'accuracy'), ('DDoS precision', 'precision'),
                       ('DDoS recall', 'recall'), ('DDoS F1', 'f1')]:
        assert scores[label] == (f"{artifact['metrics'][key] * 100:.4f}%" if key == 'accuracy' else f"{artifact['metrics'][key]:.8f}")
    assert any(f"{artifact['metrics']['false_positive_rate'] * 100:.7f}%" in item.value
               for item in app.markdown if 'False positive rate' in item.value)
    tn, fp, fn, tp = np.asarray(artifact['metrics']['confusion_matrix']).ravel()
    assert scores['False positives'] == f'{fp:,}'
    assert scores['False negatives'] == f'{fn:,}'
    errors = pd.read_csv('reports/real-data/error-examples.csv')
    assert errors.outcome.value_counts().to_dict() == {'FN': int(fn), 'FP': int(fp)}
    assert any(item.value.equals(errors) for item in app.dataframe)
    download = app.get('download_button')[0]
    assert download.proto.url  # Streamlit generated a downloadable media endpoint
    assert len(app.get('download_button')) == 1
    app.button(key='global_shap').click().run(timeout=120)
    healthy(app)
    explanation = app.session_state['global_explanation']
    assert explanation.values.shape == (100, len(artifact['feature_schema']))
    sampled_frame = frame.sample(n=100, random_state=42)
    global_error = float(np.max(np.abs(
        explanation.base_values + explanation.values.sum(axis=1)
        - artifact['pipeline'].predict_proba(sampled_frame)[:, 1])))
    assert global_error < 1e-6
    app.button(key='local_shap').click().run(timeout=120)
    healthy(app)
    row, local = app.session_state['local_explanation']
    local_error = float(abs(local.base_values + local.values.sum() - result.iloc[row].ddos_probability))
    assert local_error < 1e-6
    rendered_images = len(app.get('imgs'))
    # Exercise a real held-out unlabeled CSV with reversed feature order.
    upload = BytesIO(frame.iloc[:, ::-1].to_csv(index=False).encode())
    with patch.object(st, 'file_uploader', lambda *args, **kwargs: upload):
        uploaded = AppTest.from_file(app_file).run(timeout=60)
        uploaded.button[0].click().run(timeout=60)
        healthy(uploaded)
        pd.testing.assert_frame_equal(uploaded.session_state['analyzed'][1], expected)
        assert len(uploaded.get('download_button')) == 1
        upload_scores = {item.label: item.value for item in uploaded.metric}
        assert upload_scores == scores
        uploaded.button(key='global_shap').click().run(timeout=120)
        healthy(uploaded)
        uploaded.button(key='local_shap').click().run(timeout=120)
        healthy(uploaded)
        assert 'global_explanation' in uploaded.session_state
        assert 'local_explanation' in uploaded.session_state
    # Verify an incompatible upload does not show stale inference results.
    with patch.object(st, 'file_uploader', lambda *args, **kwargs: BytesIO(b'wrong\n1\n')):
        invalid = AppTest.from_file(app_file).run(timeout=60)
        invalid.button[0].click().run(timeout=60)
        assert not invalid.exception
        assert any('Missing required feature columns' in item.value for item in invalid.error)
        assert len(invalid.get('download_button')) == 0
    report = {
        'status': 'passed', 'method': 'Streamlit AppTest, actual trained real-data artifact; no fitting',
        'model_path': str(model), 'provenance': artifact['metadata']['provenance'],
        'saved_sample_rows': len(result), 'displayed_metrics': scores,
        'prediction_labels': result.prediction.value_counts().to_dict(),
        'global_additivity_max_error': global_error, 'local_additivity_error': local_error,
        'rendered_image_elements_after_explanations': rendered_images,
        'checks': ['real provenance displayed', 'saved held-out sample predictions equal direct model output',
                   'valid finite probabilities', 'saved held-out metrics displayed', 'download button present',
                   'global and local SHAP rendered without errors',
                   'unlabeled reversed-column CSV upload produces identical predictions and metrics',
                   'global and local SHAP work on uploaded held-out rows',
                   'incompatible upload yields actionable error and no download'],
        'scope': 'Uploader byte boundary is simulated; native browser file picker is not exercised.'}
    Path('reports/real-data/dashboard-validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
