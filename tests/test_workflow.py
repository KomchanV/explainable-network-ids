import json
import joblib

import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import train_test_split

from src.data_loader import load_training_data, read_csv
from src.evaluate import classification_metrics
from src.predict import load_artifact, predict_batch
from src.train import train_model


@pytest.fixture
def trained(flow_csv, tmp_path):
    artifact = train_model(flow_csv, tmp_path / 'model', max_train_rows=100,
                           n_estimators=12, provenance='synthetic')
    return artifact, tmp_path / 'model'


def test_training_persistence_schema_and_heldout(trained, flow_csv):
    artifact, folder = trained
    assert artifact['metadata']['provenance'] == 'synthetic'
    assert artifact['metadata']['test_rows'] == 40
    assert artifact['metadata']['train_rows_before_subsampling'] == 160
    assert artifact['metadata']['train_rows'] == 100
    assert artifact['feature_schema'] == ['Flow Duration', 'Total Fwd Packets', 'Flow Bytes/s']
    assert set(artifact['pipeline'].named_steps['classifier'].classes_) == {0, 1}
    X, y, _ = load_training_data(flow_csv)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=.2, stratify=y, random_state=42)
    X_train, _, y_train, _ = train_test_split(
        X_train, y_train, train_size=100, stratify=y_train, random_state=42)
    np.testing.assert_allclose(
        artifact['pipeline'].named_steps['imputer'].statistics_,
        X_train[artifact['feature_schema']].median().to_numpy())
    assert artifact['metrics'] == classification_metrics(y_test, artifact['pipeline'].predict(X_test))
    assert json.loads((folder / 'metrics.json').read_text()) == artifact['metrics']
    loaded = load_artifact(folder / 'model.joblib')
    input_data = read_csv(flow_csv).iloc[:10]
    result, notes = predict_batch(loaded, input_data)
    assert len(result) == 10
    assert result['prediction'].isin(['BENIGN', 'DDoS']).all()
    assert result['ddos_probability'].between(0, 1).all()
    assert 'Label' in notes['ignored_columns']
    second, _ = predict_batch(artifact, input_data[input_data.columns[::-1]])
    pd.testing.assert_frame_equal(result, second)
    assert len(artifact['explanation_sample']) <= 100


def test_prediction_schema_errors_and_explicit_extra_columns(trained):
    artifact, _ = trained
    frame = artifact['explanation_sample'].copy()
    with pytest.raises(ValueError, match='Missing required'):
        predict_batch(artifact, frame.drop(columns=artifact['feature_schema'][0]))
    frame['unexpected'] = 'ignored'
    _, notes = predict_batch(artifact, frame)
    assert 'unexpected' in notes['ignored_columns']
    frame[artifact['feature_schema'][0]] = 'not numeric'
    with pytest.raises(ValueError, match='Non-numeric'):
        predict_batch(artifact, frame)


def test_metrics_orientation_and_undefined_fpr():
    m = classification_metrics([0, 0, 1, 1], [0, 1, 1, 1])
    assert m['confusion_matrix'] == [[1, 1], [0, 2]]
    assert m['false_positive_rate'] == .5
    assert m['accuracy'] == .75
    assert classification_metrics([1, 1], [1, 0])['false_positive_rate'] is None


def test_single_class_training_fails(flow_csv, tmp_path):
    frame = read_csv(flow_csv)
    path = tmp_path / 'one.csv'
    frame.loc[frame.Label == 'BENIGN'].to_csv(path, index=False)
    with pytest.raises(ValueError, match='both'):
        train_model(path, tmp_path / 'out')


def test_bad_subsample_fails(flow_csv, tmp_path):
    with pytest.raises(ValueError, match='max_train_rows'):
        train_model(flow_csv, tmp_path / 'out', max_train_rows=1)


def test_missing_cells_use_saved_medians_without_refitting(trained):
    artifact, _ = trained
    frame = artifact['explanation_sample'].iloc[:2].copy()
    name = artifact['feature_schema'][0]
    frame[name] = [np.nan, np.inf]
    before = artifact['pipeline'].named_steps['imputer'].statistics_.copy()
    result, notes = predict_batch(artifact, frame)
    expected = frame.copy()
    expected[name] = before[0]
    expected_result, _ = predict_batch(artifact, expected)
    pd.testing.assert_frame_equal(result, expected_result)
    np.testing.assert_array_equal(before, artifact['pipeline'].named_steps['imputer'].statistics_)
    assert notes['imputed_cells'] == 2


def test_no_usable_values_and_empty_inputs_fail(trained):
    artifact, _ = trained
    frame = artifact['explanation_sample'].iloc[:1].copy()
    with pytest.raises(ValueError, match='No network flow'):
        predict_batch(artifact, frame.iloc[:0])
    frame.loc[:, :] = np.nan
    with pytest.raises(ValueError, match='no usable feature'):
        predict_batch(artifact, frame)


def test_label_values_cannot_change_predictions_and_duplicates_are_preserved(trained):
    artifact, _ = trained
    frame = artifact['explanation_sample'].iloc[:3].copy()
    frame = pd.concat([frame, frame.iloc[:1]], ignore_index=True)
    frame['Label'] = 'BENIGN'
    first, _ = predict_batch(artifact, frame)
    frame['Label'] = 'DDoS'
    second, _ = predict_batch(artifact, frame)
    pd.testing.assert_frame_equal(first, second)
    assert len(first) == 4
    assert first.iloc[0].ddos_probability == first.iloc[-1].ddos_probability


def test_corrupt_artifacts_fail_with_actionable_error(tmp_path):
    path = tmp_path / 'corrupt.joblib'
    path.write_text('not a Joblib artifact')
    with pytest.raises(ValueError, match='Could not read model'):
        load_artifact(path)


@pytest.mark.parametrize('field,value', [
    ('metadata', {}), ('metrics', {}), ('pipeline', None),
    ('label_mapping', {'BENIGN': 1, 'DDoS': 0}),
])
def test_incomplete_or_inconsistent_bundles_are_rejected(trained, tmp_path, field, value):
    artifact, _ = trained
    artifact[field] = value
    path = tmp_path / 'incomplete.joblib'
    joblib.dump(artifact, path)
    with pytest.raises(ValueError, match='artifact'):
        load_artifact(path)


def test_holdout_cannot_affect_feature_selection_or_fitted_rows(tmp_path, monkeypatch):
    from src.preprocess import NumericFeatures
    rows = np.arange(100)
    y = pd.Series(rows % 2)
    train_ids, test_ids = train_test_split(rows, test_size=.2, stratify=y, random_state=42)
    frame = pd.DataFrame({'Flow Duration': rows + 1., 'train_constant': 0.,
                          'train_empty': np.nan, 'Label': np.where(y, 'DDoS', 'BENIGN')})
    frame.loc[test_ids, 'train_constant'] = np.arange(1, 21)
    frame.loc[test_ids, 'train_empty'] = np.arange(1, 21)
    path = tmp_path / 'holdout_only_variation.csv'
    frame.to_csv(path, index=False)
    seen = []
    original_fit = NumericFeatures.fit
    def recording_fit(self, X, y=None):
        seen.extend(X['Flow Duration'].tolist())
        return original_fit(self, X, y)
    monkeypatch.setattr(NumericFeatures, 'fit', recording_fit)
    artifact = train_model(path, tmp_path / 'out', max_train_rows=50, n_estimators=5)
    assert artifact['feature_schema'] == ['Flow Duration']
    assert len(seen) == 50
    assert set(seen).issubset(set(train_ids + 1.))
    assert set(seen).isdisjoint(set(test_ids + 1.))
    assert artifact['metadata']['test_rows'] == 20
    np.testing.assert_allclose(artifact['pipeline'].named_steps['imputer'].statistics_, [np.median(seen)])
