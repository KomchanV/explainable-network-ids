"""Generate explicitly synthetic flow-like CSVs for software smoke tests only."""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def generate_fixture(output, *, rows=400, random_state=42):
    if rows < 20:
        raise ValueError('Use at least 20 rows for a stratified smoke test.')
    rng = np.random.default_rng(random_state)
    labels = rng.permutation(np.arange(rows) % 2)
    frame = pd.DataFrame({
        'Flow Duration': rng.lognormal(7 + .6 * labels, 1.1),
        'Total Fwd Packets': rng.poisson(12 + 8 * labels),
        'Total Backward Packets': rng.poisson(10 - 4 * labels),
        'Flow Bytes/s': rng.lognormal(8 + labels, 1.3),
        'Flow Packets/s': rng.lognormal(3 + .8 * labels, 1.1),
        'Packet Length Mean': rng.normal(500 - labels * 100, 120).clip(20),
        'Constant Feature': 0,
        'Source IP': ['192.0.2.1'] * rows,
        'Destination Port': np.where(labels, 80, 443),
        'Label': np.where(labels, 'DDoS', 'BENIGN'),
    })
    frame.loc[0, 'Flow Bytes/s'] = np.inf
    frame.loc[1, 'Total Fwd Packets'] = np.nan
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    path.with_suffix('.README.txt').write_text(
        'SYNTHETIC FIXTURE — invented flow-like data for software smoke tests only.\n'
        'This is NOT CIC-IDS2017. Metrics are NOT research or real-traffic results.\n'
        f'Rows: {rows}; seed: {random_state}.\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('data/raw/SYNTHETIC_flows.csv'))
    parser.add_argument('--rows', type=int, default=400)
    args = parser.parse_args()
    try:
        generate_fixture(args.output, rows=args.rows)
    except (ValueError, OSError) as exc:
        parser.exit(2, f'Fixture generation failed: {exc}\n')
    print(f'SYNTHETIC ONLY: wrote {args.rows} invented records to {args.output}.')
    print('Train with --provenance synthetic. Do not report fixture scores as research results.')


if __name__ == '__main__':
    main()
