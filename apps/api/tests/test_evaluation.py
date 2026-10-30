import pytest
from fastapi.testclient import TestClient
from apps.api.main import Settings, create_app
from src.train import train_model
from src.synthetic import generate_fixture


@pytest.fixture
def evaluation_client(tmp_path):
    csv = tmp_path / 'SYNTHETIC.csv'
    generate_fixture(csv, rows=60)
    artifact = train_model(csv, tmp_path / 'model', n_estimators=3, provenance='synthetic')
    with TestClient(create_app(Settings(model_path=tmp_path / 'model/model.joblib'))) as client:
        yield client, artifact


def test_saved_snapshot(evaluation_client, monkeypatch):
    client, artifact = evaluation_client
    def forbidden(*args, **kwargs):
        raise AssertionError('Evaluation retrieval must not fit, predict or deserialize')
    import joblib
    monkeypatch.setattr(joblib, 'load', forbidden)
    pipeline = client.app.state.artifact['pipeline']
    monkeypatch.setattr(pipeline, 'predict', forbidden)
    monkeypatch.setattr(pipeline, 'fit', forbidden)
    response = client.get('/model/evaluation')
    assert response.status_code == 200
    body = response.json()
    assert body['evaluation'] == artifact['metrics']
    assert body['label_mapping'] == {'BENIGN': 0, 'DDoS': 1}
    assert body['provenance']['source_type'] == 'synthetic'
    assert body['methodology']['test_rows'] == body['evaluation']['evaluated_rows']
    assert client.get('/model').status_code == 200
    assert 'pipeline' not in body


@pytest.mark.parametrize('change', ['accuracy', 'negative', 'fractional', 'rows', 'nan', 'fpr', 'mapping'])
def test_inconsistent_snapshot(evaluation_client, change):
    client, _ = evaluation_client
    artifact = client.app.state.artifact
    if change == 'mapping':
        artifact['label_mapping'] = {'BENIGN': 1, 'DDoS': 0}
    elif change in ('negative', 'fractional'):
        artifact['metrics']['confusion_matrix'][0][0] = -1 if change == 'negative' else 1.5
    elif change == 'rows':
        artifact['metrics']['evaluated_rows'] += 1
    else:
        artifact['metrics'][{'nan': 'recall', 'fpr': 'false_positive_rate'}.get(change, change)] = float('nan') if change == 'nan' else .123456
    response = client.get('/model/evaluation')
    assert response.status_code == 500
    assert response.json()['error']['code'] == 'invalid_evaluation'


def test_missing_metadata_and_undefined_fpr(evaluation_client):
    client, _ = evaluation_client
    a = client.app.state.artifact
    for key in ['dataset_sha256', 'created_at_utc', 'test_fraction', 'train_class_counts', 'test_class_counts']:
        a['metadata'].pop(key, None)
    a['metrics'] = dict(accuracy=1., precision=1., recall=1., f1=1., false_positive_rate=None,
                        confusion_matrix=[[0, 0], [0, a['metadata']['test_rows']]], evaluated_rows=a['metadata']['test_rows'])
    body = client.get('/model/evaluation').json()
    assert body['evaluation']['false_positive_rate'] is None
    assert body['provenance']['dataset_sha256'] is None
    assert body['methodology']['test_fraction'] is None


def test_no_model(tmp_path):
    with TestClient(create_app(Settings(model_path=tmp_path / 'missing'))) as client:
        assert client.get('/model/evaluation').status_code == 503


@pytest.mark.parametrize('truth,predicted', [
    ([0, 0, 0, 1, 1, 1, 1], [0, 1, 1, 0, 1, 1, 1]),
    ([0, 0, 1, 1], [0, 0, 0, 0]),
    ([1, 1], [0, 1]),
])
def test_orientation_and_zero_division(evaluation_client, truth, predicted):
    from src.evaluate import classification_metrics
    client, _ = evaluation_client
    artifact = client.app.state.artifact
    artifact['metrics'] = classification_metrics(truth, predicted)
    artifact['metadata']['test_rows'] = len(truth)
    artifact['metadata'].pop('test_class_counts', None)
    body = client.get('/model/evaluation').json()
    assert body['evaluation'] == artifact['metrics']
    if len(truth) == 7:
        assert body['evaluation']['confusion_matrix'] == [[1, 2], [1, 3]]
        assert body['evaluation']['precision'] == .6
        assert body['evaluation']['recall'] == .75


def test_metadata_allowlist(evaluation_client):
    client, _ = evaluation_client
    metadata = client.app.state.artifact['metadata']
    metadata['private_path'] = '/secret/path'
    metadata['dataset_filename'] = '/private/training/capture.csv'
    body = client.get('/model/evaluation').json()
    assert body['provenance']['dataset_filename'] == 'capture.csv'
    assert '/secret' not in str(body)
    assert 'loading' not in body['methodology']


@pytest.mark.parametrize('key', ['train_class_counts', 'test_class_counts'])
def test_inconsistent_class_counts(evaluation_client, key):
    client, _ = evaluation_client
    client.app.state.artifact['metadata'][key] = {'0': 0, '1': 0}
    response = client.get('/model/evaluation')
    assert response.status_code == 500
    assert response.json()['error']['code'] == 'invalid_evaluation'
