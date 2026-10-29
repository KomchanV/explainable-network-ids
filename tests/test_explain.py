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
