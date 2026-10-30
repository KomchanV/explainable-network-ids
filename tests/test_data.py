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


def test_csv_parser_chunk_boundary_preserves_order_and_duplicate_flows():
    # Two narrow columns keep this regular CI fixture small (<500 KiB).
    source = StringIO(' value,Label\n' + '1,BENIGN\n' * 50000 + '2,DDoS\n1,BENIGN\n')
    frame = read_csv(source)
    assert frame.columns.tolist() == ['value', 'Label']
    assert len(frame) == 50002
    assert frame.value.iloc[[0, 49999, 50000, 50001]].tolist() == [1, 1, 2, 1]
    assert frame.Label.iloc[50000] == 'DDoS'
    assert frame.index.tolist() == list(range(50002))


def test_late_malformed_record_and_row_limit_never_return_a_partial_frame():
    prefix = 'x,y\n' + '1,2\n' * 50000
    with pytest.raises(ValueError, match='Invalid CSV'):
        read_csv(StringIO(prefix + '3,4,5\n'))
    with pytest.raises(ValueError, match='50,000 row limit'):
        read_csv(StringIO(prefix + '3,4\n'), max_rows=50000)


def test_record_validation_preserves_quoted_fields_short_rows_and_large_cells():
    # Commas/newlines inside quoted cells are not record separators. Short rows
    # retain pandas' missing-cell behavior; no content is normalized in the scan.
    source = StringIO('x,metadata\n1,"comma, and\nnewline"\n2\n3,' + 'v' * 100000 + '\n')
    frame = read_csv(source)
    assert frame.metadata.iloc[0] == 'comma, and\nnewline'
    assert pd.isna(frame.metadata.iloc[1])
    assert frame.metadata.iloc[2] == 'v' * 100000


def test_oversized_csv_field_is_rejected_explicitly():
    import csv
    with pytest.raises(ValueError, match='Invalid CSV'):
        read_csv(StringIO('x,metadata\n1,' + 'v' * (csv.field_size_limit() + 1) + '\n'))


@pytest.mark.parametrize('size', [1, 2, 5])
def test_strict_chunk_iterator_matches_compatibility_reader(size):
    from src.data_loader import iter_csv_chunks
    data = '\ufeff x,metadata\n1,"comma, and\nnewline"\n2,hello\n1,hello\n4,world\n'
    chunks = list(iter_csv_chunks(StringIO(data), batch_size=size))
    assert all(len(chunk) <= size for chunk in chunks)
    pd.testing.assert_frame_equal(pd.concat(chunks, ignore_index=True), read_csv(StringIO(data)))
    with pytest.raises(ValueError, match='batch_size'):
        list(iter_csv_chunks(StringIO(data), batch_size=0))
