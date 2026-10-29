import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def flow_csv(tmp_path):
    """Synthetic fixture: structural validation, not real intrusion traffic."""
    rng = np.random.default_rng(42)
    label = np.tile([0, 1], 100)
    frame = pd.DataFrame({
        ' Flow Duration': rng.lognormal(5 + label, 1),
        'Total Fwd Packets': rng.poisson(10 + 20 * label),
        'Flow Bytes/s': rng.lognormal(7 + label * 2, 1.5),
        'Constant': 0,
        'Empty': np.nan,
        ' Source IP': ['192.0.2.1'] * 200,
        ' Label': np.where(label, 'DDoS', 'BENIGN'),
    })
    frame.loc[0, 'Flow Bytes/s'] = np.inf
    frame.loc[1, 'Total Fwd Packets'] = np.nan
    path = tmp_path / 'SYNTHETIC_flows.csv'
    pd.concat([frame, frame.iloc[:10]], ignore_index=True).to_csv(path, index=False)
    return path
