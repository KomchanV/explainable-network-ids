from io import BytesIO, StringIO

import numpy as np
import pandas as pd
import pytest

from src.data_loader import load_training_data, read_csv
from src.preprocess import NumericFeatures


def test_loader_filters_deduplicates_and_excludes_identifiers():
    data = StringIO(' Flow ID, Source IP, Destination Port, Flow Duration, Label\n'
                    'a,1.2.3.4,80,1,BENIGN\n'
                    'a,1.2.3.4,80,1,BENIGN\n'
                    'b,1.2.3.5,443,5,DDoS\n'
                    'c,1.2.3.6,22,9,PortScan\n')
    X, y, info = load_training_data(data)
    assert X.columns.tolist() == ['Flow Duration']
    assert y.tolist() == [0, 1]
    assert info['duplicates_removed'] == 1
    assert info['unsupported_labels_removed'] == 1


@pytest.mark.parametrize('csv', ['', 'x,x,Label\n1,2,BENIGN',
                                 'x, x,Label\n1,2,BENIGN',
                                 'x,Label\n1,BENIGN,extra', 'x,Label\n"unterminated'])
def test_invalid_csv_rejected(csv):
    with pytest.raises(ValueError):
        read_csv(StringIO(csv))


def test_missing_and_ambiguous_label_rejected():
    for csv in ['x\n1', 'x,Label,label\n1,BENIGN,BENIGN']:
        with pytest.raises(ValueError, match='label'):
            load_training_data(StringIO(csv))


def test_numeric_selection_uses_training_only_and_restores_order():
    train = pd.DataFrame({'good': ['1', '3', 'bad'], 'constant': [2, 2, 2],
                          'empty': [np.nan, np.inf, -np.inf]})
    prep = NumericFeatures().fit(train)
    assert prep.get_feature_names_out().tolist() == ['good']
    test = pd.DataFrame({'empty': [7], 'good': ['5']})
    assert prep.transform(test).iloc[0, 0] == 5
    with pytest.raises(ValueError, match='Missing required'):
        prep.transform(pd.DataFrame({'wrong': [1]}))


def test_no_usable_features_rejected():
    with pytest.raises(ValueError, match='usable'):
        NumericFeatures().fit(pd.DataFrame({'a': ['bad', 'bad']}))


def test_utf8_bom_upload_stream_is_reusable_and_row_limit_is_enforced():
    source = BytesIO('\ufeff Flow Duration,Label\n1,BENIGN\n2,DDoS\n'.encode())
    assert read_csv(source).columns.tolist() == ['Flow Duration', 'Label']
    assert not source.closed
    with pytest.raises(ValueError, match='row limit'):
        read_csv(source, max_rows=1)
    assert len(read_csv(source)) == 2


def test_labels_are_normalized_and_metadata_only_duplicates_are_removed():
    X, y, info = load_training_data(StringIO('Flow ID,x,Label\na,1, benign \nb,1,BENIGN\nc,2, ddos \n'))
    assert y.tolist() == [0, 1]
    assert X.x.tolist() == [1, 2]
    assert info['feature_duplicates_removed'] == 1


def test_original_cic_duplicate_fwd_header_length_is_supported():
    source = StringIO(' Fwd Header Length, Fwd Header Length, Label\n'
                      '20,20,BENIGN\n40,40,DDoS\n')
    parsed = read_csv(source)
    assert parsed.columns.tolist() == ['Fwd Header Length', 'Fwd Header Length.1', 'Label']
    X, y, info = load_training_data(source)
    assert X.columns.tolist() == ['Fwd Header Length']
    assert 'Fwd Header Length.1' in info['excluded_columns']
    assert y.tolist() == [0, 1]


def test_nul_bytes_are_rejected_instead_of_silently_truncating_values():
    with pytest.raises(ValueError, match='NUL'):
        read_csv(BytesIO(b'x,Label\n12\x0034,BENIGN\n'))


def test_pandas_suffixed_target_and_identifier_copies_cannot_leak_into_features():
    source = StringIO('Flow Duration,Label,Label.1,Source IP.1,Destination Port.1\n'
                      '1,BENIGN,0,100,80\n2,DDoS,1,200,443\n')
    X, _, info = load_training_data(source)
    assert X.columns.tolist() == ['Flow Duration']
    assert {'Label.1', 'Source IP.1', 'Destination Port.1'} <= set(info['excluded_columns'])
