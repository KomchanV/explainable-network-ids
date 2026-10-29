"""Bounded positive-class Tree SHAP with checked probability-space additivity."""

import argparse
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

from src.data_loader import read_csv
from src.predict import load_artifact, validate_features


def positive_class_values(values, rows, features):
    """Normalize SHAP's pre-0.45 list and modern multi-output ndarray formats.

    Reject ambiguous 2D outputs; the class axis must be explicitly available.
    """
    if isinstance(values, list) and len(values) == 2:
        result = np.asarray(values[1])
    else:
        values = np.asarray(values)
        if values.shape != (rows, features, 2):
            raise ValueError(f'Unexpected SHAP output shape {values.shape}; expected two explicit classes.')
        result = values[:, :, 1]
    if result.shape != (rows, features):
        raise ValueError(f'Unexpected positive-class SHAP shape {result.shape}.')
    return result


def explain_flows(artifact, frame, *, max_samples=100):
    """Explain at most 100 supplied flows; output values are in probability units.

    The caller selects representative samples. Training path counts supply the
    tree-path-dependent baseline; held-out rows are never fitted as background.
    """
    if max_samples < 1:
        raise ValueError('max_samples must be positive.')
    frame, _ = validate_features(artifact, frame.iloc[:min(max_samples, 100)])
    pipeline = artifact['pipeline']
    transformed = pipeline[:-1].transform(frame)
    classifier = pipeline.named_steps['classifier']
    explainer = shap.TreeExplainer(classifier, feature_perturbation='tree_path_dependent',
                                   model_output='raw')
    raw = explainer.shap_values(transformed, check_additivity=True)
    values = positive_class_values(raw, len(frame), transformed.shape[1])
    expected = np.asarray(explainer.expected_value)
    if expected.shape != (2,):
        raise ValueError(f'Unexpected SHAP base value shape {expected.shape}.')
    base_values = np.full(len(frame), expected[1], dtype=float)
    probability = pipeline.predict_proba(frame)[:, 1]
    if not np.allclose(base_values + values.sum(axis=1), probability, atol=1e-6, rtol=1e-5):
        raise ValueError('SHAP contributions do not reconstruct DDoS probability; cannot label output scale.')
    return shap.Explanation(values=values, base_values=base_values, data=transformed,
                            feature_names=artifact['feature_schema'])


def global_importance(explanation):
    return pd.DataFrame({
        'feature': explanation.feature_names,
        'mean_abs_shap': np.abs(explanation.values).mean(axis=0),
    }).sort_values('mean_abs_shap', ascending=False).reset_index(drop=True)


def importance_figure(explanation, *, top_n=15):
    ranking = global_importance(explanation).head(top_n).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, max(3, .3 * len(ranking))))
    ax.barh(ranking['feature'], ranking['mean_abs_shap'], color='#147d92')
    ax.set_xlabel('Mean absolute SHAP value (DDoS probability units)')
    ax.set_title(f'Sample feature importance · {len(explanation.values)} flows')
    fig.tight_layout()
    return fig


def waterfall_figure(explanation):
    plt.figure()
    shap.plots.waterfall(explanation, max_display=12, show=False)
    fig = plt.gcf()
    fig.tight_layout()
    return fig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', default='models/model.joblib', type=Path)
    parser.add_argument('--data', type=Path, help='Optional CSV; defaults to saved held-out sample.')
    parser.add_argument('--output-dir', default='reports/figures', type=Path)
    parser.add_argument('--max-samples', type=int, default=100)
    parser.add_argument('--row', type=int, default=0, help='Zero-based local row in the explanation sample.')
    args = parser.parse_args()
    try:
        artifact = load_artifact(args.model)
        frame = read_csv(args.data) if args.data else artifact['explanation_sample']
        frame = frame.sample(n=min(100, args.max_samples, len(frame)), random_state=42)
        explanation = explain_flows(artifact, frame, max_samples=args.max_samples)
        if not 0 <= args.row < len(explanation.values):
            raise ValueError('--row must be within the explanation sample.')
        args.output_dir.mkdir(parents=True, exist_ok=True)
        global_importance(explanation).to_csv(args.output_dir / 'global_importance.csv', index=False)
        for name, fig in [('global_shap', importance_figure(explanation)),
                          ('local_waterfall', waterfall_figure(explanation[args.row]))]:
            fig.savefig(args.output_dir / f'{name}.png', dpi=150, bbox_inches='tight')
            plt.close(fig)
    except (OSError, ValueError) as exc:
        parser.exit(2, f'Explanation failed: {exc}\n')
    print(f"Provenance: {artifact['metadata']['provenance']}")
    print(f'Saved SHAP plots for {len(explanation.values)} flows to {args.output_dir}; DDoS probability units.')


if __name__ == '__main__':
    main()
