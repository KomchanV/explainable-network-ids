"""On-demand HTTP adaptation of the authoritative positive-class SHAP engine."""
from typing import Literal

import numpy as np
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, FiniteFloat

from apps.api.analyses import AnalysisError, FlowPrediction

SEED = 42


class FeatureContribution(BaseModel):
    feature: str
    raw_value: FiniteFloat | None
    transformed_value: FiniteFloat
    shap_value: FiniteFloat
    absolute_contribution: FiniteFloat


class LocalExplanation(FlowPrediction):
    analysis_id: str
    base_value: FiniteFloat
    reconstructed_probability: FiniteFloat
    reconstruction_error: FiniteFloat
    class_explained: Literal['DDoS'] = 'DDoS'
    model_identifier: str
    model_provenance: Literal['synthetic', 'cic-ids2017', 'unspecified']
    feature_contributions: list[FeatureContribution]


class FeatureImportance(BaseModel):
    feature: str
    mean_abs_shap: FiniteFloat


class GlobalExplanation(BaseModel):
    analysis_id: str
    sample_size: int
    sampled_row_numbers: list[int]
    sampling_seed: int = SEED
    sampling_method: str = 'Uniform without replacement across the entire uploaded analysis; row order restored.'
    class_explained: Literal['DDoS'] = 'DDoS'
    model_identifier: str
    model_provenance: Literal['synthetic', 'cic-ids2017', 'unspecified']
    max_reconstruction_error: FiniteFloat
    feature_importance: list[FeatureImportance]


def snapshot(store, id, model_identifier, *, row_number=None, sample_size=50):
    """Read bounded owned copies while deletion/expiry is excluded by the lock."""
    import json
    import pandas as pd
    with store.lock:
        session = store.get(id)
        if session.summary.model_identifier != model_identifier:
            raise AnalysisError(503, 'model_unavailable', 'The analysis model is no longer available.')
        count = len(session.offsets)
        if row_number is not None:
            if not 1 <= row_number <= count:
                raise AnalysisError(404, 'flow_not_found', 'Flow row not found.')
            indices = np.array([row_number - 1])
        else:
            indices = np.sort(np.random.default_rng(SEED).choice(count, min(sample_size, count), replace=False))
        rows = []
        with session.path.open('rb') as source:
            for index in indices:
                source.seek(session.offsets[index])
                rows.append(json.loads(source.readline()))
        return session.summary.model_copy(deep=True), pd.DataFrame(rows), session.predictions.iloc[indices].copy(deep=True)


def checked_explanation(artifact, frame, predictions):
    from src.explain import explain_flows
    schema = artifact['feature_schema']
    frame = frame.loc[:, schema]
    try:
        explanation = explain_flows(artifact, frame, max_samples=len(frame))
        values = np.asarray(explanation.values, dtype=float)
        bases = np.asarray(explanation.base_values, dtype=float)
        data = np.asarray(explanation.data, dtype=float)
        shape = (len(frame), len(schema))
        if (values.shape != shape or data.shape != shape or bases.shape != (len(frame),)
                or list(explanation.feature_names) != schema
                or not all(np.isfinite(array).all() for array in (values, bases, data))):
            raise ValueError('Invalid explanation dimensions or numerical values.')
    except Exception:
        # Engine/library errors may embed raw data or artifact paths. Never echo them.
        raise AnalysisError(500, 'shap_failure', 'SHAP calculation failed validation. Contact the server operator.') from None
    reconstructed = bases + values.sum(axis=1)
    stored = predictions.ddos_probability.to_numpy(dtype=float)
    if not np.isfinite(stored).all() or not np.allclose(reconstructed, stored, atol=1e-6, rtol=1e-5):
        raise AnalysisError(500, 'reconstruction_failure', 'SHAP contributions do not reconstruct the stored DDoS probability.')
    return explanation, reconstructed, np.abs(reconstructed - stored)


def router(artifact_for, error_model):
    api = APIRouter(prefix='/api/v1/analyses', responses={
        code: {'model': error_model} for code in (404, 410, 422, 500, 503)})

    def compute(id, request, row_number=None, sample_size=50, top_n=15):
        from src.explain import global_importance
        artifact = artifact_for(request)
        if top_n is None:
            top_n = min(15, len(artifact['feature_schema']))
        if row_number is None and top_n > len(artifact['feature_schema']):
            raise AnalysisError(422, 'invalid_top_n', 'top_n must not exceed the model feature count.')
        store = request.app.state.analyses
        if not store.explanation.acquire(blocking=False):
            raise AnalysisError(503, 'explanation_busy', 'Another explanation is being computed. Retry after it finishes.')
        try:
            summary, frame, predictions = snapshot(store, id, request.app.state.model_identifier,
                                                  row_number=row_number, sample_size=sample_size)
            explanation, reconstructed, errors = checked_explanation(artifact, frame, predictions)
            common = dict(analysis_id=id, model_identifier=summary.model_identifier,
                          model_provenance=summary.model_provenance)
            if row_number is not None:
                result = LocalExplanation(**common, **predictions.iloc[0].to_dict(),
                    base_value=float(explanation.base_values[0]), reconstructed_probability=float(reconstructed[0]),
                    reconstruction_error=float(errors[0]), feature_contributions=[
                        FeatureContribution(feature=name, raw_value=None if frame[name].iloc[0] is None or np.isnan(frame[name].iloc[0]) else float(frame[name].iloc[0]),
                            transformed_value=float(explanation.data[0, index]),
                            shap_value=float(explanation.values[0, index]),
                            absolute_contribution=float(abs(explanation.values[0, index])))
                        for index, name in enumerate(artifact['feature_schema'])])
            else:
                ranking = global_importance(explanation).head(top_n)
                if not np.isfinite(ranking.mean_abs_shap.to_numpy()).all():
                    raise AnalysisError(500, 'shap_failure', 'SHAP importance contains invalid numerical values.')
                result = GlobalExplanation(**common, sample_size=len(frame),
                    sampled_row_numbers=predictions.row_number.tolist(), max_reconstruction_error=float(errors.max()),
                    feature_importance=ranking.to_dict(orient='records'))
            # A snapshot can finish safely after deletion, but cannot resurrect a session.
            with store.lock:
                store.get(id)
            return result
        finally:
            store.explanation.release()

    @api.get('/{id}/flows/{row_number}/explanation', response_model=LocalExplanation,
             operation_id='explainAnalysisFlow')
    def local(id: str, row_number: int, request: Request):
        return compute(id, request, row_number=row_number)

    @api.get('/{id}/explanations/global', response_model=GlobalExplanation, operation_id='explainAnalysisSample')
    def global_sample(id: str, request: Request, sample_size: int = Query(50, ge=1, le=100),
                      top_n: int | None = Query(None, ge=1, description='Defaults to min(15, model feature count).')):
        return compute(id, request, sample_size=sample_size, top_n=top_n)

    return api
