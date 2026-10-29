"""Isolated synthetic model and CSV for browser tests. Never touches models/."""
from pathlib import Path
import tempfile

import pandas as pd
import uvicorn

from apps.api.main import Settings, create_app
from src.synthetic import generate_fixture
from src.train import train_model


def main():
    with tempfile.TemporaryDirectory(prefix='ids-e2e-') as directory:
        root = Path(directory)
        generate_fixture(root / 'synthetic.csv', rows=100)
        artifact = train_model(root / 'synthetic.csv', root / 'model', n_estimators=3, provenance='synthetic')
        destination = Path('apps/web/test-results/flows.csv')
        destination.parent.mkdir(parents=True, exist_ok=True)
        sample = artifact['explanation_sample']
        pd.concat([sample, sample], ignore_index=True).to_csv(destination, index=False)
        app = create_app(Settings(model_path=root / 'model/model.joblib', cors_origins=('http://127.0.0.1:5174',)))
        uvicorn.run(app, host='127.0.0.1', port=8001)


if __name__ == '__main__':
    main()
