from pathlib import Path
from io import BytesIO

import streamlit as st
import joblib
from streamlit.testing.v1 import AppTest

from src.train import train_model


def test_dashboard_without_artifact_shows_training_instructions(tmp_path, monkeypatch):
    monkeypatch.setenv('IDS_MODEL_PATH', str(tmp_path / 'missing.joblib'))
    app = AppTest.from_file(str(Path(__file__).parents[1] / 'app.py')).run(timeout=30)
    assert not app.exception
    assert any('Train' in item.value for item in app.info)


def test_dashboard_demo_predictions_and_explanations(flow_csv, tmp_path, monkeypatch):
    train_model(flow_csv, tmp_path / 'model', n_estimators=8, provenance='synthetic')
    monkeypatch.setenv('IDS_MODEL_PATH', str(tmp_path / 'model/model.joblib'))
    app = AppTest.from_file(str(Path(__file__).parents[1] / 'app.py')).run(timeout=60)
    assert not app.exception
    app.checkbox[0].check().run(timeout=60)
    assert not app.exception
    assert any(m.label == 'Analyzed flows' and int(m.value) > 0 for m in app.metric)
    assert any('synthetic' in w.value.lower() for w in app.warning)
    app.button(key='global_shap').click().run(timeout=60)
    assert not app.exception
    assert not app.error
    assert 'global_explanation' in app.session_state
    app.button(key='local_shap').click().run(timeout=60)
    assert not app.exception
    assert not app.error
    assert 'local_explanation' in app.session_state


def test_csv_upload_prediction_and_download(flow_csv, tmp_path, monkeypatch):
    """Simulate the uploader boundary with a real byte stream; run real app logic."""
    train_model(flow_csv, tmp_path / 'model', n_estimators=8, provenance='synthetic')
    monkeypatch.setenv('IDS_MODEL_PATH', str(tmp_path / 'model/model.joblib'))
    monkeypatch.setattr(st, 'file_uploader', lambda *args, **kwargs: BytesIO(flow_csv.read_bytes()))
    app = AppTest.from_file(str(Path(__file__).parents[1] / 'app.py')).run(timeout=30)
    app.button[0].click().run(timeout=30)
    assert not app.exception
    assert not app.error
    assert app.metric[0].value == '210'  # inference preserves duplicates
    assert len(app.get('download_button')) == 1
    assert any('Label' in item.value for item in app.info)


def test_invalid_upload_displays_error_without_results(flow_csv, tmp_path, monkeypatch):
    train_model(flow_csv, tmp_path / 'model', n_estimators=8, provenance='synthetic')
    monkeypatch.setenv('IDS_MODEL_PATH', str(tmp_path / 'model/model.joblib'))
    monkeypatch.setattr(st, 'file_uploader', lambda *args, **kwargs: BytesIO(b'wrong\n1\n'))
    app = AppTest.from_file(str(Path(__file__).parents[1] / 'app.py')).run(timeout=30)
    app.button[0].click().run(timeout=30)
    assert not app.exception
    assert any('Missing required' in item.value for item in app.error)
    assert app.metric[0].value == '0'
    assert len(app.get('download_button')) == 0


def test_incomplete_artifact_has_friendly_error_instead_of_runtime_exception(flow_csv, tmp_path, monkeypatch):
    artifact = train_model(flow_csv, tmp_path / 'model', n_estimators=5, provenance='synthetic')
    artifact['metadata'] = {}
    path = tmp_path / 'bad.joblib'
    joblib.dump(artifact, path)
    monkeypatch.setenv('IDS_MODEL_PATH', str(path))
    app = AppTest.from_file(str(Path(__file__).parents[1] / 'app.py')).run(timeout=30)
    assert not app.exception
    assert any('Could not load' in item.value for item in app.error)


def test_unlabeled_upload_keeps_saved_labeled_evaluation_metrics(flow_csv, tmp_path, monkeypatch):
    from src.data_loader import read_csv
    artifact = train_model(flow_csv, tmp_path / 'model', n_estimators=5, provenance='synthetic')
    monkeypatch.setenv('IDS_MODEL_PATH', str(tmp_path / 'model/model.joblib'))
    frame = read_csv(flow_csv).drop(columns='Label').iloc[:, ::-1]
    monkeypatch.setattr(st, 'file_uploader', lambda *args, **kwargs: BytesIO(frame.to_csv(index=False).encode()))
    app = AppTest.from_file(str(Path(__file__).parents[1] / 'app.py')).run(timeout=30)
    app.button[0].click().run(timeout=30)
    assert not app.exception
    assert not app.error
    scores = {item.label: item.value for item in app.metric}
    for label, key in [('Accuracy', 'accuracy'), ('DDoS precision', 'precision'),
                       ('DDoS recall', 'recall'), ('DDoS F1', 'f1')]:
        assert scores[label] == (f"{artifact['metrics'][key] * 100:.4f}%" if key == 'accuracy' else f"{artifact['metrics'][key]:.8f}")
    assert len(app.get('download_button')) == 1


def test_dashboard_does_not_round_near_perfect_metrics_to_perfect(flow_csv, tmp_path, monkeypatch):
    artifact = train_model(flow_csv, tmp_path / 'model', n_estimators=5, provenance='synthetic')
    artifact['metrics'].update(accuracy=0.9997062677933933, precision=0.9999609252891528,
                               recall=0.999531304925204, f1=0.9997460689520461,
                               false_positive_rate=1 / 18655,
                               confusion_matrix=[[18654, 1], [12, 25591]])
    artifact['metadata']['test_rows'] = 44258
    artifact['metrics']['evaluated_rows'] = 44258
    path = tmp_path / 'precision.joblib'
    joblib.dump(artifact, path)
    monkeypatch.setenv('IDS_MODEL_PATH', str(path))
    app = AppTest.from_file(str(Path(__file__).parents[1] / 'app.py')).run(timeout=60)
    assert not app.exception
    scores = {item.label: item.value for item in app.metric}
    assert scores['Accuracy'] == '99.9706%'
    assert scores['DDoS precision'] == '0.99996093'
    assert scores['False positives'] == '1'
    assert scores['False negatives'] == '12'
    assert any('0.0053605%' in item.value for item in app.markdown)
