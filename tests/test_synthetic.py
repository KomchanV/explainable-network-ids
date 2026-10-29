import pandas as pd

from src.synthetic import generate_fixture


def test_synthetic_fixture_is_reproducible_and_clearly_marked(tmp_path):
    first = tmp_path / 'SYNTHETIC_first.csv'
    second = tmp_path / 'SYNTHETIC_second.csv'
    generate_fixture(first, rows=300)
    generate_fixture(second, rows=300)
    assert first.read_bytes() == second.read_bytes()
    frame = pd.read_csv(first)
    assert len(frame) == 300
    assert set(frame['Label']) == {'BENIGN', 'DDoS'}
    assert first.with_suffix('.README.txt').exists()
    assert 'SYNTHETIC' in first.with_suffix('.README.txt').read_text()
