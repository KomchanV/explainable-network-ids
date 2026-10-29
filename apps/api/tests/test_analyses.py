"""Offline analysis resource integration tests with an isolated fitted fixture."""
import io
import time

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from apps.api.main import Settings, create_app
from src.predict import predict_batch
from src.synthetic import generate_fixture
from src.train import train_model


@pytest.fixture(scope='module')
def bundle(tmp_path_factory):
    root = tmp_path_factory.mktemp('analysis-model')
    generate_fixture(root / 'fixture.csv', rows=60)
    artifact = train_model(root / 'fixture.csv', root / 'model', n_estimators=3, provenance='synthetic')
    return root / 'model/model.joblib', artifact


@pytest.fixture
def client(bundle):
    with TestClient(create_app(Settings(model_path=bundle[0]))) as client:
        yield client


def upload(client, frame):
    return client.post('/api/v1/analyses?filename=flows.csv', content=frame.to_csv(index=False).encode(),
                       headers={'Content-Type': 'text/csv'})


def test_complete_workflow_and_parity(client, bundle):
    frame = bundle[1]['explanation_sample'].iloc[:6]
    frame = pd.concat([frame, frame.iloc[:1]], ignore_index=True)
    frame['Source IP'] = 'private-do-not-store'
    expected, notes = predict_batch(bundle[1], frame)
    response = upload(client, frame)
    assert response.status_code == 201, response.text
    summary = response.json()
    id = summary['id']
    base = f'/api/v1/analyses/{id}'
    assert summary['total_flows'] == 7
    assert summary['benign_count'] + summary['ddos_count'] == 7
    assert summary['ignored_columns'] == notes['ignored_columns']
    assert client.get(base).json() == summary
    result = client.get(base + '/flows?page_size=2').json()
    assert result['total'] == 7
    assert [r['row_number'] for r in result['items']] == [1, 2]
    assert client.get(base + '/flows?page=2&page_size=2').json()['items'][0]['row_number'] == 3
    all_rows = client.get(base + '/flows').json()['items']
    assert [r['prediction'] for r in all_rows] == expected.prediction.tolist()
    np.testing.assert_allclose([r['ddos_probability'] for r in all_rows], expected.ddos_probability, atol=1e-12)
    filtered = client.get(base + '/flows?prediction=DDoS&probability_min=0.2&sort=probability&direction=desc').json()
    assert all(r['prediction'] == 'DDoS' and r['ddos_probability'] >= .2 for r in filtered['items'])
    assert filtered['items'] == sorted(filtered['items'], key=lambda r: (-r['ddos_probability'], r['row_number']))
    detail = client.get(base + '/flows/1').json()
    assert set(detail['features']) == set(bundle[1]['feature_schema'])
    assert 'private-do-not-store' not in str(detail)
    assert client.get(base + '/flows/999').status_code == 404
    assert client.get(base + '/flows?row_number=7').json()['total'] == 1
    assert client.get(base + '/flows?probability_min=0.9&probability_max=0.1').status_code == 422
    exported = client.get(base + '/export')
    actual = pd.read_csv(io.StringIO(exported.text))
    pd.testing.assert_frame_equal(actual, expected, check_exact=False, atol=1e-12)
    assert client.delete(base).status_code == 204
    assert client.get(base).status_code == 404
    assert not list(client.app.state.analyses.root.iterdir())


@pytest.mark.parametrize('data', [b'', b'x\n', b'x\n1\n', b'x,x\n1,2\n', b'\xff', b'"unclosed', b'x\n1,2\n', b'x\x00\n1'])
def test_invalid_csv(client, data):
    response = client.post('/api/v1/analyses?filename=x.csv', content=data, headers={'Content-Type': 'text/csv'})
    assert response.status_code == 422
    assert response.json()['error']['code'] == 'invalid_csv'
    assert not list(client.app.state.analyses.root.iterdir())


def test_limits_expiry_and_capacity(client, bundle, monkeypatch):
    store = client.app.state.analyses
    frame = bundle[1]['explanation_sample'].iloc[:2]
    monkeypatch.setattr(store, 'max_upload_bytes', 10)
    assert upload(client, frame).status_code == 413
    monkeypatch.setattr(store, 'max_upload_bytes', 200 * 1024 * 1024)
    monkeypatch.setattr(store, 'max_rows', 1)
    assert upload(client, frame).status_code == 422
    monkeypatch.setattr(store, 'max_rows', 50000)
    monkeypatch.setattr(store, 'max_sessions', 1)
    id = upload(client, frame).json()['id']
    assert upload(client, frame).status_code == 503
    monkeypatch.setattr(store, 'ttl', 0)
    assert client.get('/api/v1/analyses/' + id).status_code == 410
    assert not list(store.root.iterdir())


def test_bom_duplicate_exception_and_missing_values(client, bundle):
    frame = bundle[1]['explanation_sample'].iloc[:2].copy()
    frame.iloc[0, 0] = np.nan
    frame['Fwd Header Length'] = 4
    # Explicit duplicate exception; append a redundant column to every data row.
    lines = frame.to_csv(index=False).splitlines()
    data = '\ufeff' + lines[0] + ',Fwd Header Length\n' + '\n'.join(line + ',4' for line in lines[1:])
    response = client.post('/api/v1/analyses?filename=x.csv', content=data.encode(), headers={'Content-Type': 'text/csv'})
    assert response.status_code == 201, response.text
    assert 'Fwd Header Length.1' in response.json()['ignored_columns']
    assert response.json()['imputed_cells'] >= 1


def test_missing_model_and_media_type(tmp_path):
    app = create_app(Settings(model_path=tmp_path / 'missing'))
    with TestClient(app) as client:
        root = client.app.state.analyses.root
        assert client.post('/api/v1/analyses', content=b'x\n1').status_code == 503
    assert not root.exists()


def test_streamed_limit_without_content_length(client, monkeypatch):
    store = client.app.state.analyses
    monkeypatch.setattr(store, 'max_upload_bytes', 10)
    def chunks():
        yield b'x\n'
        yield b'1' * 9
    response = client.post('/api/v1/analyses', content=chunks(), headers={'Content-Type': 'text/csv'})
    assert response.status_code == 413
    assert not list(store.root.iterdir())


def test_storage_failure_and_ingestion_busy(client, bundle, monkeypatch):
    store = client.app.state.analyses
    frame = bundle[1]['explanation_sample'].iloc[:2]
    monkeypatch.setattr(store, 'max_disk_bytes', 1)
    assert upload(client, frame).status_code == 503
    assert not store.sessions
    assert not list(store.root.iterdir())
    store.ingestion.acquire()
    try:
        assert upload(client, frame).json()['error']['code'] == 'analysis_busy'
    finally:
        store.ingestion.release()
    assert client.post('/api/v1/analyses', content=b'x\n1', headers={'Content-Type': 'application/json'}).status_code == 415


def test_results_never_rerun_inference_and_filters_are_exact(client, bundle, monkeypatch):
    frame = bundle[1]['explanation_sample']
    expected, _ = predict_batch(bundle[1], frame)
    id = upload(client, frame).json()['id']
    def forbidden(*args, **kwargs):
        raise AssertionError('Result retrieval must not run inference')
    monkeypatch.setattr('src.predict.predict_batch', forbidden)
    base = f'/api/v1/analyses/{id}'
    for label in ('BENIGN', 'DDoS'):
        body = client.get(base + '/flows', params={'prediction': label, 'probability_min': .1,
                          'probability_max': .9, 'sort': 'probability', 'direction': 'asc'}).json()
        selected = expected.loc[(expected.prediction == label) & expected.ddos_probability.between(.1, .9)]
        selected = selected.sort_values(['ddos_probability', 'row_number'])
        assert body['total'] == len(selected)
        assert [r['row_number'] for r in body['items']] == selected.row_number.tolist()
    rows = client.get(base + '/flows?direction=desc').json()['items']
    assert [r['row_number'] for r in rows] == list(range(len(frame), 0, -1))
    assert client.get(base + '/flows?page=999').json()['items'] == []
    for query in ('page=0', 'page_size=101', 'prediction=attack', 'probability_min=-1'):
        assert client.get(base + '/flows?' + query).status_code == 422
    assert client.get(base + '/flows/1').status_code == 200
    assert client.get(base + '/export').status_code == 200


def test_actual_row_limit_before_inference(client):
    response = client.post('/api/v1/analyses', content=b'x\n' + b'1\n' * 50001, headers={'Content-Type': 'text/csv'})
    assert response.status_code == 422
    assert '50,000 row limit' in response.json()['error']['message']
    assert not list(client.app.state.analyses.root.iterdir())


def test_cleanup_sweep_and_isolation(client, bundle):
    store = client.app.state.analyses
    frame = bundle[1]['explanation_sample'].iloc[:2]
    first = upload(client, frame).json()['id']
    second = upload(client, frame).json()['id']
    assert first != second
    store.sessions[first].deadline = time.monotonic() - 1
    store.cleanup()
    assert client.get(f'/api/v1/analyses/{first}').status_code == 410
    assert client.get(f'/api/v1/analyses/{second}').status_code == 200
    assert len(list(store.root.iterdir())) == 1


def test_csv_shape_bounds_before_engine(client, bundle, monkeypatch):
    store = client.app.state.analyses
    monkeypatch.setattr(store, 'max_columns', 2)
    assert upload(client, bundle[1]['explanation_sample'].iloc[:2]).status_code == 422
    monkeypatch.setattr(store, 'max_columns', 256)
    monkeypatch.setattr(store, 'max_cells', 1)
    assert upload(client, bundle[1]['explanation_sample'].iloc[:2]).status_code == 422
    assert not list(store.root.iterdir())


def test_upload_deadline_releases_slot(client, monkeypatch):
    import asyncio
    import httpx
    store = client.app.state.analyses
    monkeypatch.setattr(store, 'upload_timeout', .01)
    async def run():
        async def stalled():
            yield b'x\n'
            await asyncio.sleep(1)
            yield b'1'
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=client.app), base_url='http://test') as async_client:
            response = await async_client.post('/api/v1/analyses', content=stalled(), headers={'Content-Type': 'text/csv'})
            assert response.status_code == 408
    asyncio.run(run())
    assert not store.ingestion.locked()
    assert not list(store.root.iterdir())
