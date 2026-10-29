"""Strict CSV loading and deterministic, label-aware dataset preparation."""

import csv
from contextlib import contextmanager
from io import TextIOWrapper
from pathlib import Path
import re
import warnings

import numpy as np
import pandas as pd


def column_key(name):
    return re.sub(r'[^a-z0-9]', '', str(name).lower())


# Conservative exclusions for the fixed CIC-IDS2017 capture scenario.
NON_FEATURE_KEYS = {
    'flowid', 'id', 'index', 'srcip', 'sourceip', 'dstip', 'destinationip',
    'srcaddr', 'dstaddr', 'sourceaddress', 'destinationaddress',
    'sourceport', 'srcport', 'destinationport', 'dstport',
    'timestamp', 'time', 'date', 'label', 'class', 'target', 'attack',
    'attacktype', 'attackcategory', 'category', 'prediction',
    'predictedlabel', 'ddosprobability', 'rownumber',
    'fwdheaderlength1',  # CIC-IDS2017's documented redundant field.
}


def is_non_feature(name):
    key = column_key(name)
    # Pandas exports may preserve previously disambiguated metadata as Label.1
    # or Source IP.1. These remain targets/identifiers, not numeric features.
    base_key = column_key(re.sub(r'(?:\.\d+)+$', '', str(name)))
    return key in NON_FEATURE_KEYS or base_key in NON_FEATURE_KEYS or key.startswith('unnamed')


def normalize_columns(frame):
    result = frame.copy(deep=False)
    columns = [str(c).strip().lstrip('\ufeff') for c in frame.columns]
    if any(not c for c in columns):
        raise ValueError('CSV contains an empty column name.')
    if len({c.casefold() for c in columns}) != len(columns):
        raise ValueError(f'CSV contains duplicate or ambiguous column names after trimming: {columns}')
    result.columns = columns
    return result


@contextmanager
def _text_stream(source):
    if isinstance(source, (str, Path)):
        with open(source, encoding='utf-8-sig', newline='') as stream:
            yield stream
    else:
        source.seek(0)
        if isinstance(source.read(0), bytes):
            wrapper = TextIOWrapper(source, encoding='utf-8-sig', newline='')
            try:
                yield wrapper
            finally:
                wrapper.detach()  # UploadedFile belongs to the caller.
        else:
            yield source


def read_csv(source, *, max_rows=None):
    """Read strict comma-separated UTF-8 CSV in chunks, without silently losing fields.

    Chunking bounds parser intermediates; the resulting DataFrame still lives in RAM.
    max_rows rejects an oversized input rather than silently truncating it.
    """
    try:
        with _text_stream(source) as stream:
            # Pandas' C parser silently truncates fields at NUL bytes. Reject
            # these before parsing, with bounded memory even for large files.
            while block := stream.read(1_048_576):
                if '\x00' in block:
                    raise ValueError('Invalid CSV: NUL bytes are not allowed.')
            stream.seek(0)
            header = next(csv.reader(stream, strict=True), None)
            if not header:
                raise ValueError('CSV is empty or has no header.')
            header = [c.strip().lstrip('\ufeff') for c in header]
            # Original CICFlowMeter exports repeat this known feature. Assign a
            # stable name to its second occurrence; it is excluded from modeling.
            repeated = [i for i, c in enumerate(header) if c.casefold() == 'fwd header length']
            if len(repeated) == 2:
                header[repeated[1]] = 'Fwd Header Length.1'
            normalize_columns(pd.DataFrame(columns=header))
            stream.seek(0)
            with warnings.catch_warnings():
                # index_col=False prevents implicit index inference on overlong rows;
                # its ParserWarning is an error, so no extra fields are discarded.
                warnings.simplefilter('error', pd.errors.ParserWarning)
                chunks = []
                total = 0
                for chunk in pd.read_csv(stream, chunksize=50_000, low_memory=False,
                                         index_col=False, on_bad_lines='error',
                                         names=header, header=0,
                                         nrows=None if max_rows is None else max_rows + 1):
                    total += len(chunk)
                    if max_rows is not None and total > max_rows:
                        raise ValueError(f'CSV exceeds the {max_rows:,} row limit. Use the CLI for larger files.')
                    chunks.append(chunk)
            if not chunks or total == 0:
                raise ValueError('CSV has no data rows.')
            return normalize_columns(pd.concat(chunks, ignore_index=True))
    except (pd.errors.ParserError, pd.errors.EmptyDataError, pd.errors.ParserWarning,
            UnicodeError, csv.Error) as exc:
        raise ValueError(f'Invalid CSV: {exc}') from exc


def numeric_frame(frame):
    """Pointwise conversion, with no learned statistics or feature selection."""
    return frame.apply(pd.to_numeric, errors='coerce').replace([np.inf, -np.inf], np.nan)


def load_training_data(source):
    frame = read_csv(source)
    label_columns = [c for c in frame if c.casefold() == 'label']
    if len(label_columns) != 1:
        raise ValueError('Training requires exactly one label column named Label.')
    label_column = label_columns[0]
    info = {'input_rows': len(frame)}
    labels = frame[label_column].astype('string').str.strip().str.upper()
    keep = labels.isin(['BENIGN', 'DDOS'])
    info['unsupported_labels_removed'] = int((~keep).sum())
    frame = frame.loc[keep].copy()
    frame[label_column] = labels.loc[keep].map({'BENIGN': 0, 'DDOS': 1}).astype('int8')
    before = len(frame)
    frame = frame.drop_duplicates()
    info['duplicates_removed'] = before - len(frame)
    excluded = [c for c in frame if is_non_feature(c)]
    info['excluded_columns'] = excluded
    X = numeric_frame(frame.drop(columns=excluded))
    if X.shape[1] == 0:
        raise ValueError('No candidate numeric feature columns remain after exclusions.')
    y = frame[label_column]
    # Differing metadata should not allow identical model records across the split.
    model_duplicates = X.assign(__label__=y).duplicated()
    info['feature_duplicates_removed'] = int(model_duplicates.sum())
    X = X.loc[~model_duplicates].reset_index(drop=True)
    y = y.loc[~model_duplicates].reset_index(drop=True)
    info['retained_rows'] = len(X)
    return X, y, info
