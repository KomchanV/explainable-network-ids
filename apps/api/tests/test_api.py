"""API adapter contracts, including parity with the unchanged engine."""
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from apps.api.main import Settings, create_app
from src.predict import load_artifact, predict_batch


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(Settings(model_path=tmp_path / 'missing.joblib'))) as client:
        yield client


def test_health_without_model(client):
    assert client.get('/health').json() == {
        'status': 'ok', 'version': '0.2.0-alpha.1', 'model_available': False}
    response = client.get('/model')
    assert response.status_code == 503
    assert response.json()['error']['code'] == 'model_unavailable'
    assert '/missing.joblib' not in response.text


def test_validation_and_http_errors_share_envelope(client):
    response = client.post('/predict', json={'rows': []})
    assert response.status_code == 422
    assert response.json()['error']['code'] == 'validation_error'
    response = client.post('/predict', json={'rows': [{'x': 1}], 'model_path': '/tmp/evil.joblib'})
    assert response.status_code == 422
    assert client.get('/unknown').json()['error']['code'] == 'http_error'


def test_cors_and_openapi(client):
    response = client.options('/predict', headers={
        'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'POST'})
    assert response.headers['access-control-allow-origin'] == 'http://localhost:5173'
    schema = client.get('/openapi.json').json()
    assert set(schema['paths']) == {'/health', '/model', '/predict'}
    assert schema['paths']['/predict']['post']['responses']['422']['content']['application/json']['schema']['$ref'].endswith('/ErrorResponse')


def test_corrupt_model_does_not_prevent_startup(tmp_path):
    path = tmp_path / 'broken.joblib'
    path.write_text('invalid artifact')
    with TestClient(create_app(Settings(model_path=path))) as client:
        assert client.get('/health').status_code == 200
        assert client.get('/model').status_code == 503
        assert client.post('/predict', json={'rows': [{'x': 1}]}).status_code == 503


def test_environment_paths_are_root_relative(monkeypatch):
    monkeypatch.setenv('IDS_MODEL_PATH', 'models/custom.joblib')
    monkeypatch.setenv('IDS_CORS_ORIGINS', 'http://localhost:5173, http://127.0.0.1:5173')
    settings = Settings.from_env()
    assert settings.model_path == Path(__file__).resolve().parents[3] / 'models/custom.joblib'
    assert settings.cors_origins == ('http://localhost:5173', 'http://127.0.0.1:5173')


def test_trusted_model_parity_and_metadata():
    path = Path('models/model.joblib')
    if not path.is_file():
        pytest.skip('Optional trusted v0.1 artifact is not available')
    artifact = load_artifact(path)
    rows = artifact['explanation_sample'].iloc[:6].replace({np.nan: None}).to_dict(orient='records')
    expected, notes = predict_batch(artifact, artifact['explanation_sample'].iloc[:6])
    with TestClient(create_app(Settings(model_path=path))) as client:
        assert client.get('/health').json()['model_available']
        metadata = client.get('/model').json()
        assert metadata['feature_schema'] == artifact['feature_schema']
        assert metadata['provenance'] == artifact['metadata']['provenance']
        response = client.post('/predict', json={'rows': rows})
        assert response.status_code == 200
        body = response.json()
        assert body['ignored_columns'] == notes['ignored_columns']
        assert body['imputed_cells'] == notes['imputed_cells']
        assert [p['prediction'] for p in body['predictions']] == expected.prediction.tolist()
        assert [p['row_number'] for p in body['predictions']] == expected.row_number.tolist()
        np.testing.assert_allclose([p['ddos_probability'] for p in body['predictions']],
                                   expected.ddos_probability, atol=1e-12, rtol=0)
        invalid = client.post('/predict', json={'rows': [{'missing': 1}]})
        assert invalid.status_code == 422
        assert invalid.json()['error']['code'] == 'invalid_features'


def test_prediction_without_optional_local_artifact(tmp_path):
    # A small isolated fixture makes this test runnable in a clean clone.
    # It never writes to models/ and its scores are not scientific evidence.
    from src.synthetic import generate_fixture
    from src.train import train_model
    csv = tmp_path / 'SYNTHETIC.csv'
    generate_fixture(csv, rows=40)
    artifact = train_model(csv, tmp_path / 'fixture-model', n_estimators=3, provenance='synthetic')
    sample = artifact['explanation_sample'].iloc[:2]
    rows = sample.replace({np.nan: None}).to_dict(orient='records')
    expected, _ = predict_batch(artifact, sample)
    with TestClient(create_app(Settings(model_path=tmp_path / 'fixture-model/model.joblib'))) as client:
        response = client.post('/predict', json={'rows': rows})
        assert response.status_code == 200
        assert [p['prediction'] for p in response.json()['predictions']] == expected.prediction.tolist()
        np.testing.assert_allclose([p['ddos_probability'] for p in response.json()['predictions']],
                                   expected.ddos_probability, atol=1e-12, rtol=0)
        assert client.get('/model').json()['provenance'] == 'synthetic'
