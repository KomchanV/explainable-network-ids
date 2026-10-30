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


def test_local_explanation_parity_imputation_and_order(client, bundle):
    frame = bundle[1]['explanation_sample'].copy()
    frame.iloc[0, 0] = np.nan
    id = upload(client, frame).json()['id']
    base = f'/api/v1/analyses/{id}'
    labels = set()
    for number in range(1, len(frame) + 1):
        response = client.get(f'{base}/flows/{number}/explanation')
        assert response.status_code == 200, response.text
        body = response.json()
        stored = client.get(f'{base}/flows/{number}').json()
        labels.add(body['prediction'])
        assert body['ddos_probability'] == stored['ddos_probability']
        assert body['class_explained'] == 'DDoS'
        features = body['feature_contributions']
        assert [f['feature'] for f in features] == bundle[1]['feature_schema']
        reconstructed = body['base_value'] + sum(f['shap_value'] for f in features)
        np.testing.assert_allclose(reconstructed, stored['ddos_probability'], atol=1e-6, rtol=1e-5)
        assert body['reconstructed_probability'] == pytest.approx(reconstructed)
        assert body['reconstruction_error'] <= 1e-6 + 1e-5 * stored['ddos_probability']
        transformed = bundle[1]['pipeline'][:-1].transform(frame.iloc[[number-1]])[0]
        np.testing.assert_allclose([f['transformed_value'] for f in features], transformed)
        if number == 1:
            assert features[0]['raw_value'] is None
        assert all(np.isfinite(f['shap_value']) for f in features)
    assert labels == {'BENIGN', 'DDoS'}


def test_global_explanation_sample_and_importance(client, bundle):
    from src.explain import explain_flows, global_importance
    frame = pd.concat([bundle[1]['explanation_sample']] * 12, ignore_index=True)
    id = upload(client, frame).json()['id']
    path = f'/api/v1/analyses/{id}/explanations/global'
    body = client.get(path, params={'sample_size': 7, 'top_n': 3}).json()
    assert body == client.get(path, params={'sample_size': 7, 'top_n': 3}).json()
    selected = np.sort(np.random.default_rng(42).choice(len(frame), size=7, replace=False))
    assert body['sampled_row_numbers'] == (selected + 1).tolist()
    assert max(selected) > 7
    expected = global_importance(explain_flows(bundle[1], frame.iloc[selected])).head(3)
    assert [f['feature'] for f in body['feature_importance']] == expected.feature.tolist()
    np.testing.assert_allclose([f['mean_abs_shap'] for f in body['feature_importance']], expected.mean_abs_shap)
    assert body['sample_size'] == 7
    assert body['sampling_seed'] == 42
    assert client.get(path).json()['sample_size'] == 50
    assert client.get(path + '?sample_size=100').json()['sample_size'] == 100
    for query in ('sample_size=101', 'sample_size=0', 'top_n=0', 'top_n=9999'):
        assert client.get(path + '?' + query).status_code == 422


def test_explanation_lifecycle_busy_and_missing_model(client, bundle):
    id = upload(client, bundle[1]['explanation_sample'].iloc[:2]).json()['id']
    local = f'/api/v1/analyses/{id}/flows/1/explanation'
    global_path = f'/api/v1/analyses/{id}/explanations/global'
    for path in (local, global_path):
        store = client.app.state.analyses
        store.explanation.acquire()
        try:
            response = client.get(path)
            assert response.status_code == 503
            assert response.json()['error']['code'] == 'explanation_busy'
        finally:
            store.explanation.release()
    assert client.get(f'/api/v1/analyses/{id}/flows/0/explanation').status_code == 404
    assert client.get(f'/api/v1/analyses/{id}/flows/999/explanation').status_code == 404
    artifact = client.app.state.artifact
    client.app.state.artifact = None
    assert client.get(local).json()['error']['code'] == 'model_unavailable'
    client.app.state.artifact = artifact
    store.sessions[id].deadline = time.monotonic() - 1
    for path in (local, global_path):
        assert client.get(path).status_code == 410
    assert not list(store.root.iterdir())
    for path in ('flows/1/explanation', 'explanations/global'):
        assert client.get(f'/api/v1/analyses/nonexistent/{path}').status_code == 404


def test_explanation_failures_are_safe(client, bundle, monkeypatch):
    import src.explain
    id = upload(client, bundle[1]['explanation_sample'].iloc[:2]).json()['id']
    local = f'/api/v1/analyses/{id}/flows/1/explanation'
    original = src.explain.explain_flows
    def fail(*args, **kwargs):
        raise ValueError('private-upload-value /local/model.joblib')
    monkeypatch.setattr(src.explain, 'explain_flows', fail)
    response = client.get(local)
    assert response.status_code == 500
    assert response.json()['error']['code'] == 'shap_failure'
    assert 'private-upload' not in response.text and 'joblib' not in response.text
    def corrupt(*args, **kwargs):
        explanation = original(*args, **kwargs)
        explanation.values[0, 0] += .1
        return explanation
    monkeypatch.setattr(src.explain, 'explain_flows', corrupt)
    assert client.get(local).json()['error']['code'] == 'reconstruction_failure'
    def nonfinite(*args, **kwargs):
        explanation = original(*args, **kwargs)
        explanation.data[0, 0] = np.nan
        return explanation
    monkeypatch.setattr(src.explain, 'explain_flows', nonfinite)
    assert client.get(local).json()['error']['code'] == 'shap_failure'
    assert not client.app.state.analyses.explanation.locked()


@pytest.mark.parametrize('endpoint', ['flows/1/explanation', 'explanations/global'])
@pytest.mark.parametrize('lifecycle', ['delete', 'expire'])
def test_lifecycle_overlaps_explanation_without_holding_store_lock(client, bundle, monkeypatch, endpoint, lifecycle):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    import src.explain
    id = upload(client, bundle[1]['explanation_sample'].iloc[:2]).json()['id']
    entered, release = threading.Event(), threading.Event()
    original = src.explain.explain_flows
    def slow(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        return original(*args, **kwargs)
    monkeypatch.setattr(src.explain, 'explain_flows', slow)
    with ThreadPoolExecutor() as executor:
        pending = executor.submit(client.get, f'/api/v1/analyses/{id}/{endpoint}')
        assert entered.wait(5)
        try:
            assert client.get(f'/api/v1/analyses/{id}/{endpoint}').json()['error']['code'] == 'explanation_busy'
            if lifecycle == 'delete':
                assert client.delete(f'/api/v1/analyses/{id}').status_code == 204
            else:
                client.app.state.analyses.sessions[id].deadline = time.monotonic() - 1
                client.app.state.analyses.cleanup()
            assert not list(client.app.state.analyses.root.iterdir())
        finally:
            release.set()
        assert pending.result().status_code == (404 if lifecycle == 'delete' else 410)


@pytest.mark.parametrize('kind', ['values_shape', 'bases_shape', 'data_shape', 'feature_order', 'infinite', 'stored_probability'])
def test_explanation_rejects_invalid_numerical_contract(client, bundle, monkeypatch, kind):
    import src.explain
    id = upload(client, bundle[1]['explanation_sample'].iloc[:2]).json()['id']
    original = src.explain.explain_flows
    def malformed(*args, **kwargs):
        from types import SimpleNamespace
        actual = original(*args, **kwargs)
        explanation = SimpleNamespace(values=actual.values, base_values=actual.base_values,
                                      data=actual.data, feature_names=actual.feature_names)
        if kind == 'values_shape':
            explanation.values = explanation.values[:, :-1]
        elif kind == 'bases_shape':
            explanation.base_values = np.array([[.5]])
        elif kind == 'data_shape':
            explanation.data = explanation.data[:, :-1]
        elif kind == 'feature_order':
            explanation.feature_names = explanation.feature_names[::-1]
        elif kind == 'infinite':
            explanation.values[0, 0] = np.inf
        return explanation
    monkeypatch.setattr(src.explain, 'explain_flows', malformed)
    if kind == 'stored_probability':
        client.app.state.analyses.sessions[id].predictions.loc[0, 'ddos_probability'] = .123456789
    for path in ('flows/1/explanation', 'explanations/global'):
        response = client.get(f'/api/v1/analyses/{id}/{path}')
        assert response.status_code == 500
        expected = 'reconstruction_failure' if kind == 'stored_probability' else 'shap_failure'
        assert response.json()['error']['code'] == expected
    assert not client.app.state.analyses.explanation.locked()


def test_small_global_sample_and_deleted_session(client, bundle):
    id = upload(client, bundle[1]['explanation_sample'].iloc[:2]).json()['id']
    path = f'/api/v1/analyses/{id}/explanations/global'
    result = client.get(path).json()
    assert result['sample_size'] == 2
    assert result['sampled_row_numbers'] == [1, 2]
    assert len(result['feature_importance']) == len(bundle[1]['feature_schema'])
    assert client.delete(f'/api/v1/analyses/{id}').status_code == 204
    assert client.get(path).status_code == 404
    assert client.get(f'/api/v1/analyses/{id}/flows/1/explanation').status_code == 404
    assert not list(client.app.state.analyses.root.iterdir())


@pytest.mark.parametrize('batch_size', [1, 2, 7])
def test_partitioned_inference_scientific_baseline(bundle, batch_size):
    """Oracle for future streaming integration; never refit the saved imputer."""
    artifact = bundle[1]
    frame = artifact['explanation_sample'].iloc[:6].copy()
    frame.iloc[0, 0] = np.nan
    frame.iloc[2, 1] = np.inf
    frame = pd.concat([frame, frame.iloc[[0, 3]]], ignore_index=True)
    frame['Source IP'] = 'ignored synthetic metadata'
    statistics = artifact['pipeline'].named_steps['imputer'].statistics_.copy()
    expected, expected_notes = predict_batch(artifact, frame)
    batches, imputed = [], 0
    for start in range(0, len(frame), batch_size):
        predictions, notes = predict_batch(artifact, frame.iloc[start:start + batch_size])
        assert predictions.row_number.tolist() == list(range(1, len(predictions) + 1))
        predictions.row_number += start
        batches.append(predictions)
        imputed += notes['imputed_cells']
        assert notes['ignored_columns'] == expected_notes['ignored_columns']
    actual = pd.concat(batches, ignore_index=True)
    pd.testing.assert_frame_equal(actual, expected, check_exact=True)
    assert imputed == expected_notes['imputed_cells']
    np.testing.assert_array_equal(statistics, artifact['pipeline'].named_steps['imputer'].statistics_)


def test_probability_ties_and_inclusive_boundaries(client, bundle):
    frame = pd.concat([bundle[1]['explanation_sample'].iloc[:1]] * 7, ignore_index=True)
    expected, _ = predict_batch(bundle[1], frame)
    id = upload(client, frame).json()['id']
    base = f'/api/v1/analyses/{id}'
    probability = float(expected.ddos_probability.iloc[0])
    for direction in ('asc', 'desc'):
        rows = []
        for page in (1, 2, 3):
            response = client.get(base + '/flows', params={
                'probability_min': probability, 'probability_max': probability,
                'sort': 'probability', 'direction': direction, 'page_size': 3, 'page': page})
            assert response.status_code == 200
            assert response.json()['total'] == 7
            rows.extend(response.json()['items'])
        assert [row['row_number'] for row in rows] == list(range(1, 8))
        assert all(row['ddos_probability'] == probability for row in rows)
    exported = pd.read_csv(io.StringIO(client.get(base + '/export').text))
    pd.testing.assert_frame_equal(exported, expected, check_exact=False, atol=1e-12)


def test_inference_failure_is_atomic_and_releases_ingestion(client, bundle, monkeypatch):
    frame = bundle[1]['explanation_sample'].iloc[:2]
    with monkeypatch.context() as patch:
        def fail(*args, **kwargs):
            raise ValueError('synthetic failure containing sensitive-input-marker')
        patch.setattr('src.predict.predict_batch', fail)
        response = upload(client, frame)
    assert response.status_code == 422
    assert 'sensitive-input-marker' not in response.text
    assert not client.app.state.analyses.sessions
    assert not list(client.app.state.analyses.root.iterdir())
    assert upload(client, frame).status_code == 201


def test_synthetic_lifecycle_benchmark(bundle, tmp_path):
    from scripts.benchmark_traffic import run_case
    result = run_case(bundle[0], rows=9, directory=tmp_path)
    assert result['rows'] == 9
    assert result['export_rows'] == 9
    assert result['storage_bytes'] > 0
    assert result['input_bytes'] > 0
    assert result['python_peak_bytes'] > 0
    assert result['process_peak_rss_bytes'] >= result['process_peak_rss_before_bytes']
    assert result['rows_per_second'] > 0
    assert result['max_shap_reconstruction_error'] < 1e-5
    assert set(result['stage_seconds']) == {'ingestion', 'queries', 'local_shap', 'global_shap', 'export'}
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('rows', [0, -1, 50001])
def test_benchmark_rejects_invalid_sizes_before_model_loading(tmp_path, rows):
    from scripts.benchmark_traffic import run_case
    with pytest.raises(ValueError, match='rows'):
        run_case(tmp_path / 'not-a-model', rows=rows, directory=tmp_path)
    assert not list(tmp_path.iterdir())
