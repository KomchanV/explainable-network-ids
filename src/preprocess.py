"""Sklearn-compatible, train-only feature selection with explicit schema checks."""

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_is_fitted

from src.data_loader import normalize_columns, numeric_frame


class NumericFeatures(TransformerMixin, BaseEstimator):
    def fit(self, X, y=None):
        frame = numeric_frame(normalize_columns(X))
        self.feature_names_in_ = np.asarray(frame.columns, dtype=object)
        self.n_features_in_ = len(self.feature_names_in_)
        self.columns_ = frame.columns[frame.nunique(dropna=True) > 1].tolist()
        self.dropped_columns_ = [c for c in frame if c not in self.columns_]
        if not self.columns_:
            raise ValueError('No usable nonconstant numeric features in training data.')
        return self

    def transform(self, X):
        check_is_fitted(self, 'columns_')
        frame = normalize_columns(X)
        missing = [c for c in self.columns_ if c not in frame]
        if missing:
            raise ValueError(f'Missing required feature columns: {", ".join(missing)}')
        return numeric_frame(frame.loc[:, self.columns_])

    def get_feature_names_out(self, input_features=None):
        check_is_fitted(self, 'columns_')
        return np.asarray(self.columns_, dtype=object)
