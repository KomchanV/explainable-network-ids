"""Read-only, allowlisted projection of the saved held-out evaluation."""
import math
from numbers import Integral
from pathlib import PureWindowsPath
from typing import Annotated, Literal

from pydantic import BaseModel, Field

Score = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
Count = Annotated[int, Field(ge=0, strict=True)]

LIMITATIONS = [
    'Metrics describe the saved labeled held-out evaluation, not predictions on a current uploaded CSV.',
    'Training and testing originate from the same capture/dataset scenario; these results do not establish generalization to unseen networks.',
    'Performance may change under distribution shift. This evaluation does not prove robustness against adaptive attacks.',
    'Model probabilities are not calibrated confidence or threat-severity scores.',
    'SHAP explanations describe model behavior, not causal evidence.',
    'This is an offline academic prototype, not a production-ready security system.',
]


class Evaluation(BaseModel):
    accuracy: Score
    precision: Score
    recall: Score
    f1: Score
    false_positive_rate: Score | None
    confusion_matrix: tuple[tuple[Count, Count], tuple[Count, Count]]
    evaluated_rows: Annotated[int, Field(gt=0, strict=True)]


class ModelIdentity(BaseModel):
    identifier: str
    classifier: Literal['RandomForestClassifier']
    format_version: int
    feature_count: int


class Provenance(BaseModel):
    dataset_filename: str | None
    dataset_sha256: str | None
    source_type: Literal['synthetic', 'cic-ids2017', 'unspecified']
    training_timestamp: str | None
    evaluation_scope: str


class Methodology(BaseModel):
    train_rows: Count
    test_rows: Count
    test_fraction: Score | None
    random_state: int
    train_rows_before_subsampling: Count | None
    train_class_counts: dict[str, Count] | None
    test_class_counts: dict[str, Count] | None
    preprocessing_summary: str
    split_method: str


class ModelEvaluationResponse(BaseModel):
    model: ModelIdentity
    evaluation: Evaluation
    provenance: Provenance
    methodology: Methodology
    label_mapping: dict[str, int]
    limitations: list[str]


def evaluation_snapshot(artifact, identifier):
    """Validate rather than repair saved results; never invoke the pipeline."""
    metadata = artifact['metadata']
    if artifact['label_mapping'] != {'BENIGN': 0, 'DDoS': 1}:
        raise ValueError('Invalid label mapping')
    raw = artifact['metrics']
    for row in raw['confusion_matrix']:
        if any(isinstance(n, bool) or not isinstance(n, Integral) for n in row):
            raise ValueError('Matrix counts must be integers')
    e = Evaluation.model_validate(raw)
    (tn, fp), (fn, tp) = e.confusion_matrix
    total = tn + fp + fn + tp
    if total != e.evaluated_rows or total != metadata['test_rows']:
        raise ValueError('Inconsistent evaluation counts')
    divide = lambda n, d: n / d if d else 0.
    expected = dict(accuracy=(tn + tp) / total, precision=divide(tp, tp + fp),
                    recall=divide(tp, tp + fn), f1=divide(2 * tp, 2 * tp + fp + fn),
                    false_positive_rate=fp / (fp + tn) if fp + tn else None)
    for key, value in expected.items():
        saved = getattr(e, key)
        if (value is None) != (saved is None) or (value is not None and not math.isclose(saved, value, rel_tol=1e-9, abs_tol=1e-12)):
            raise ValueError('Saved scores disagree with confusion matrix')
    for key, expected_counts in [('test_class_counts', {'0': tn + fp, '1': fn + tp}),
                                 ('train_class_counts', None)]:
        counts = metadata.get(key)
        if counts is not None:
            if (not isinstance(counts, dict) or set(counts) != {'0', '1'}
                    or any(isinstance(n, bool) or not isinstance(n, Integral) or n < 0 for n in counts.values())
                    or (expected_counts is not None and counts != expected_counts)
                    or (expected_counts is None and sum(counts.values()) != metadata['train_rows'])):
                raise ValueError('Inconsistent recorded class counts')
    # Both slash conventions are stripped: a filename must never disclose paths.
    filename = metadata.get('dataset_filename')
    filename = PureWindowsPath(filename).name if filename else None
    digest = metadata.get('dataset_sha256')
    if digest is not None and (len(digest) != 64 or any(c not in '0123456789abcdefABCDEF' for c in digest)):
        raise ValueError('Invalid dataset fingerprint')
    return ModelEvaluationResponse(
        model=ModelIdentity(identifier=identifier, classifier='RandomForestClassifier',
                            format_version=artifact['format_version'], feature_count=len(artifact['feature_schema'])),
        evaluation=e,
        provenance=Provenance(dataset_filename=filename, dataset_sha256=digest,
                              source_type=metadata['provenance'], training_timestamp=metadata.get('created_at_utc'),
                              evaluation_scope='Saved labeled held-out evaluation from the training dataset scenario'),
        methodology=Methodology(**{k: metadata.get(k) for k in [
            'train_rows', 'test_rows', 'test_fraction', 'random_state', 'train_rows_before_subsampling',
            'train_class_counts', 'test_class_counts']},
            preprocessing_summary='Current training implementation: numeric features; identifiers and labels excluded; invalid/nonbinary labels removed; duplicates removed before splitting; unusable training columns excluded; median imputation fitted on training data; Random Forest classification.',
            split_method='Current training implementation: stratified train/test split with seed-controlled optional training subsampling. Missing historical settings are not inferred.'),
        label_mapping=artifact['label_mapping'], limitations=LIMITATIONS)
