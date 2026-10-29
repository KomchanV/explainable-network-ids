"""Local Streamlit dashboard for the offline explainable network IDS."""

import hashlib
from io import BytesIO
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.metrics import ConfusionMatrixDisplay

from src.data_loader import read_csv
from src.predict import load_artifact, predict_batch


@st.cache_resource(show_spinner='Loading trained model…', max_entries=2)
def cached_model(path, fingerprint):
    return load_artifact(path)


@st.cache_data(show_spinner=False, max_entries=4)
def cached_global_shap(path, fingerprint, sample):
    from src.explain import explain_flows
    return explain_flows(cached_model(path, fingerprint), sample)


def show_prediction_results(result, notes):
    st.subheader('Batch results')
    st.caption('Probabilities are the model’s estimated P(DDoS); they are not calibrated confidence scores.')
    if notes['ignored_columns']:
        st.info('Ignored extra columns: ' + ', '.join(notes['ignored_columns']))
    if notes['imputed_cells']:
        st.info(f"{notes['imputed_cells']:,} missing or infinite feature values used saved training medians.")
    st.dataframe(result.head(1000), use_container_width=True, hide_index=True,
                 column_config={'ddos_probability': st.column_config.NumberColumn('P(DDoS)', format='%.4f')})
    if len(result) > 1000:
        st.caption('Preview shows the first 1,000 rows. The download includes all analyzed flows.')
    st.download_button('Download prediction CSV', data=result.to_csv(index=False).encode('utf-8'),
                       file_name='network_flow_predictions.csv', mime='text/csv')


def main():
    st.set_page_config(page_title='Explainable Network IDS', page_icon='🛡️', layout='wide')
    st.caption('NETWORK SECURITY  /  MACHINE LEARNING LAB')
    st.title('Explainable Network IDS')
    st.markdown('Inspect offline network flows, detect **BENIGN / DDoS** traffic, and examine the model’s reasoning.')
    path = Path(os.environ.get('IDS_MODEL_PATH', 'models/model.joblib'))
    if not path.is_file():
        st.info('Train a model first, then refresh this page. See README.md for dataset setup.')
        st.code('python -m src.synthetic --output data/raw/SYNTHETIC_flows.csv')
        st.code('python -m src.train --data data/raw/SYNTHETIC_flows.csv --provenance synthetic')
        return
    fingerprint = (path.stat().st_mtime_ns, path.stat().st_size)
    try:
        artifact = cached_model(str(path.resolve()), fingerprint)
    except Exception as exc:
        st.error(f'Could not load the local model: {exc}. Use the pinned dependencies or retrain it.')
        return
    metadata = artifact['metadata']
    provenance = metadata['provenance']
    if provenance == 'synthetic':
        st.warning('SYNTHETIC DEMONSTRATION — this model and its evaluation use invented fixture data. '
                   'These are software validation results, not CIC-IDS2017 research results.')
    elif provenance == 'unspecified':
        st.warning('Dataset provenance was not specified at training time. Do not assume this model was trained on CIC-IDS2017.')
    else:
        st.info('Training source declared by the trainer: CIC-IDS2017. Dataset authenticity is not automatically verified.')

    with st.sidebar:
        st.subheader('Upload and prediction')
        upload = st.file_uploader('Network flow CSV', type=['csv'], help='UTF-8 CSV. Maximum 50,000 rows / 200 MB.')
        use_sample = st.checkbox('Use saved held-out sample', help='Demonstrates inference on a small saved evaluation sample.')
        analyze = st.button('Analyze CSV', type='primary', disabled=upload is None or use_sample)
        st.caption(f"Model: Random Forest · {len(artifact['feature_schema'])} features")
        st.caption(f"Training rows: {metadata['train_rows']:,} · Held-out rows: {metadata['test_rows']:,}")
        with st.expander('Required feature schema'):
            st.write(artifact['feature_schema'])
            st.caption('Missing required columns are rejected. Extra columns are ignored and reported.')

    upload_bytes = upload.getvalue() if upload is not None else None
    token = (str(path.resolve()), fingerprint, 'sample' if use_sample else
             hashlib.sha256(upload_bytes).hexdigest() if upload_bytes is not None else None)
    if st.session_state.get('input_token') != token:
        st.session_state['input_token'] = token
        for key in ['analyzed', 'global_explanation', 'local_explanation']:
            st.session_state.pop(key, None)
    if (use_sample and 'analyzed' not in st.session_state) or analyze:
        try:
            with st.spinner('Validating schema and classifying flows…'):
                frame = (artifact['explanation_sample'].copy() if use_sample else
                         read_csv(BytesIO(upload_bytes), max_rows=50_000))
                result, notes = predict_batch(artifact, frame)
                st.session_state['analyzed'] = (frame, result, notes)
        except (ValueError, OSError) as exc:
            st.session_state.pop('analyzed', None)
            st.error(f'CSV could not be analyzed: {exc}')

    overview, predictions, performance, explanations = st.tabs(
        ['Overview', 'Prediction results', 'Model performance', 'Explainable AI'])
    analyzed = st.session_state.get('analyzed')
    with overview:
        st.subheader('Detection overview')
        result = analyzed[1] if analyzed else None
        total = len(result) if result is not None else 0
        ddos = int((result.prediction == 'DDoS').sum()) if result is not None else 0
        for column, label, value in zip(st.columns(4),
                                        ['Analyzed flows', 'Predicted BENIGN', 'Predicted DDoS', 'Predicted DDoS share'],
                                        [f'{total:,}', f'{total-ddos:,}', f'{ddos:,}', f'{ddos/total:.1%}' if total else '—']):
            column.metric(label, value)
        st.caption('Counts describe the current batch’s predictions. They are not labeled ground truth.')
        if analyzed:
            counts = result.prediction.value_counts().reindex(['BENIGN', 'DDoS'], fill_value=0)
            fig, ax = plt.subplots(figsize=(7, 2.5))
            ax.bar(counts.index, counts.values, color=['#147d92', '#c45442'])
            ax.set_ylabel('Predicted flows')
            fig.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
            st.caption('Current source: ' + ('saved held-out feature sample' if use_sample else 'uploaded CSV'))
        else:
            st.info('Upload a compatible CSV and select Analyze CSV, or enable the saved held-out sample.')

    with predictions:
        if analyzed:
            show_prediction_results(analyzed[1], analyzed[2])
        else:
            st.info('Analyze a CSV to view and download predictions.')

    with performance:
        st.subheader('Labeled held-out evaluation')
        st.caption(f"Source: {provenance} · {metadata['dataset_filename']} · "
                   f"{metadata['test_rows']:,} test rows · seed {metadata['random_state']} · 80/20 split")
        st.caption('These saved training-run metrics do not measure the accuracy of the current upload.')
        metrics = artifact['metrics']
        for col, key, name in zip(st.columns(4), ['accuracy', 'precision', 'recall', 'f1'],
                                  ['Accuracy', 'DDoS precision', 'DDoS recall', 'DDoS F1']):
            col.metric(name, f'{metrics[key] * 100:.4f}%' if key == 'accuracy' else f'{metrics[key]:.8f}')
        fpr = metrics['false_positive_rate']
        st.write('False positive rate: ' + (f'{fpr * 100:.7f}%' if fpr is not None else 'undefined (no negative labels)'))
        tn, fp, fn, tp = np.asarray(metrics['confusion_matrix']).ravel()
        count_cols = st.columns(2)
        count_cols[0].metric('False positives', f'{fp:,}')
        count_cols[1].metric('False negatives', f'{fn:,}')
        st.caption('Same-capture random holdout: benchmark performance does not establish real-world generalization.')
        matrix_col, detail_col = st.columns([1, 1])
        with matrix_col:
            fig, ax = plt.subplots(figsize=(5, 3.5))
            ConfusionMatrixDisplay(np.asarray(metrics['confusion_matrix']),
                                   display_labels=['BENIGN', 'DDoS']).plot(ax=ax, cmap='Blues', colorbar=False, values_format='d')
            fig.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
        with detail_col:
            st.markdown('**Reading the matrix**')
            st.write('Rows are actual labels; columns are model predictions. '
                     'A false positive is BENIGN traffic predicted as DDoS.')
            with st.expander('Training and data provenance'):
                st.json(metadata)

        if provenance == 'cic-ids2017':
            st.subheader('Verified held-out errors')
            report_dir = Path(__file__).parent / 'reports/real-data'
            comparison_path = report_dir / 'baseline-comparison.json'
            if comparison_path.is_file():
                import json
                comparison = json.loads(comparison_path.read_text())
                if comparison.get('model_sha256') == hashlib.sha256(path.read_bytes()).hexdigest():
                    errors = pd.read_csv(report_dir / 'error-examples.csv')
                    st.dataframe(errors, hide_index=True, use_container_width=True)
                    st.caption('All saved Random Forest errors; row IDs refer to cleaned data. '
                               'FP: BENIGN predicted DDoS; FN: DDoS predicted BENIGN.')
                    for outcome in ['FP', 'FN']:
                        image = report_dir / f'figures/local-{outcome}.png'
                        if image.is_file():
                            st.image(str(image), caption=f'First {outcome} in deterministic held-out order; saved Tree SHAP explanation')
                else:
                    st.warning('Saved error report belongs to a different model. Regenerate the baseline comparison.')
            else:
                st.info('Run python -m scripts.compare_baseline to prepare verified error examples.')

    with explanations:
        st.subheader('Why did the model predict DDoS?')
        st.caption('Positive-class Tree SHAP · probability units · contributions describe model behavior, not causality.')
        if analyzed:
            frame, result, _ = analyzed
            from src.explain import global_importance, importance_figure, waterfall_figure, explain_flows
            st.markdown('**Global feature importance**')
            st.caption('Mean absolute SHAP values across up to 100 randomly selected flows from the current batch.')
            if st.button('Generate global explanation', key='global_shap'):
                try:
                    with st.spinner('Computing Tree SHAP on a bounded sample…'):
                        sample = frame.sample(n=min(100, len(frame)), random_state=42)
                        st.session_state['global_explanation'] = cached_global_shap(str(path.resolve()), fingerprint, sample)
                except Exception as exc:
                    st.error(f'Global explanation failed: {exc}')
            if 'global_explanation' in st.session_state:
                explanation = st.session_state['global_explanation']
                fig = importance_figure(explanation)
                st.pyplot(fig)
                plt.close(fig)
                st.dataframe(global_importance(explanation), hide_index=True, use_container_width=True)

            st.divider()
            st.markdown('**Individual flow explanation**')
            row = int(st.number_input('Flow data row (1-based)', min_value=1, max_value=len(frame), value=1, step=1)) - 1
            prediction = result.iloc[row]
            st.write(f"Prediction: **{prediction['prediction']}** · P(DDoS): **{prediction['ddos_probability']:.4f}**")
            if st.button('Explain selected flow', key='local_shap'):
                try:
                    with st.spinner('Explaining selected flow…'):
                        local = explain_flows(artifact, frame.iloc[[row]], max_samples=1)[0]
                        st.session_state['local_explanation'] = (row, local)
                except Exception as exc:
                    st.error(f'Local explanation failed: {exc}')
            stored = st.session_state.get('local_explanation')
            if stored and stored[0] == row:
                local = stored[1]
                fig = waterfall_figure(local)
                st.pyplot(fig)
                plt.close(fig)
                st.caption(f'Baseline P(DDoS) {float(local.base_values):.4f} + '
                           f'sum of contributions {float(local.values.sum()):+.4f} = '
                           f'{float(local.base_values + local.values.sum()):.4f}. '
                           'Positive values raise the DDoS output; negative values lower it.')
                values = pd.DataFrame({'feature': local.feature_names, 'model_input_value': local.data,
                                       'shap_ddos_probability_units': local.values})
                values['direction'] = np.where(local.values > 0, 'increases DDoS output',
                                                np.where(local.values < 0, 'decreases DDoS output', 'no contribution'))
                order = np.argsort(-np.abs(local.values))
                st.dataframe(values.iloc[order], use_container_width=True, hide_index=True)
                st.caption('Model input values above include imputation with training medians where needed.')
        else:
            st.info('Analyze flows to generate global and individual explanations.')
    st.divider()
    st.caption('Academic offline prototype · BENIGN / DDoS only · Inspired by E-XAI (IEEE Access, 2024)')


if __name__ == '__main__':
    main()
