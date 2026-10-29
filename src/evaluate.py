"""Metrics for labeled data; DDoS (1) is always the positive class."""

import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, precision_score, recall_score, f1_score


def classification_metrics(y_true, y_pred):
    truth, prediction = np.asarray(y_true), np.asarray(y_pred)
    if truth.ndim != 1 or prediction.ndim != 1 or len(truth) == 0 or len(truth) != len(prediction):
        raise ValueError('Evaluation requires equally sized, nonempty label arrays.')
    if not np.isin(truth, [0, 1]).all() or not np.isin(prediction, [0, 1]).all():
        raise ValueError('Evaluation labels must be 0 (BENIGN) or 1 (DDoS).')
    matrix = confusion_matrix(truth, prediction, labels=[0, 1])
    tn, fp, fn, tp = matrix.ravel()
    return {
        'accuracy': float(accuracy_score(truth, prediction)),
        'precision': float(precision_score(truth, prediction, zero_division=0)),
        'recall': float(recall_score(truth, prediction, zero_division=0)),
        'f1': float(f1_score(truth, prediction, zero_division=0)),
        'false_positive_rate': float(fp / (tn + fp)) if tn + fp else None,
        'confusion_matrix': matrix.tolist(),
        'evaluated_rows': len(truth),
    }
