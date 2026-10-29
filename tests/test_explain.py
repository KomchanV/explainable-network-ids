import numpy as np
import pytest

from src.explain import explain_flows, positive_class_values, global_importance, waterfall_figure
from src.train import train_model


def test_shap_formats_select_positive_class():
    values = np.arange(12).reshape(3, 4)
    np.testing.assert_array_equal(positive_class_values([-values, values], 3, 4), values)
    np.testing.assert_array_equal(
        positive_class_values(np.stack([-values, values], axis=-1), 3, 4), values)
    with pytest.raises(ValueError, match='SHAP'):
        positive_class_values(values, 3, 4)


def test_shap_reconstructs_ddos_probability(flow_csv, tmp_path):
    artifact = train_model(flow_csv, tmp_path / 'model', n_estimators=10,
                           provenance='synthetic')
    sample = artifact['explanation_sample'].iloc[:8]
    explanation = explain_flows(artifact, sample, max_samples=5)
    assert explanation.values.shape == (5, len(artifact['feature_schema']))
    probability = artifact['pipeline'].predict_proba(sample.iloc[:5])[:, 1]
    np.testing.assert_allclose(explanation.base_values + explanation.values.sum(axis=1),
                               probability, atol=1e-6)
    ranking = global_importance(explanation)
    assert ranking['mean_abs_shap'].is_monotonic_decreasing
    fig = waterfall_figure(explanation[0])
    assert len(fig.axes) > 0
    import matplotlib.pyplot as plt
    plt.close(fig)


def test_shap_imputation_order_and_mean_absolute_values(flow_csv, tmp_path):
    artifact = train_model(flow_csv, tmp_path / 'model', n_estimators=3, provenance='synthetic')
    sample = artifact['explanation_sample'].iloc[:6].copy()
    sample.iloc[0, 0] = np.nan
    # Unordered request columns must still match the original fitted feature order.
    explanation = explain_flows(artifact, sample.iloc[:, ::-1])
    schema = artifact['feature_schema']
    assert explanation.feature_names == schema
    np.testing.assert_allclose(explanation.data, artifact['pipeline'][:-1].transform(sample))
    assert explanation.data[0, 0] == artifact['pipeline'].named_steps['imputer'].statistics_[0]
    assert explanation.base_values.shape == (6,)
    assert all(np.isfinite(array).all() for array in (explanation.values, explanation.data, explanation.base_values))
    np.testing.assert_allclose(explanation.base_values + explanation.values.sum(axis=1),
                               artifact['pipeline'].predict_proba(sample)[:, 1], atol=1e-6, rtol=1e-5)
    ranking = global_importance(explanation).set_index('feature')
    np.testing.assert_allclose(ranking.loc[schema].mean_abs_shap,
                               np.abs(explanation.values).mean(axis=0))


@pytest.mark.parametrize('values', [np.zeros((2, 3)), np.zeros((2, 3, 1)),
                                    [np.zeros((2, 2)), np.zeros((2, 2))]])
def test_reject_ambiguous_or_malformed_positive_class_shapes(values):
    with pytest.raises(ValueError, match='SHAP'):
        positive_class_values(values, 2, 3)
