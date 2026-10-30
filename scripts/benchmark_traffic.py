"""Opt-in, synthetic-only baseline of the production offline analysis lifecycle.

Run with ``python -m scripts.benchmark_traffic --output /tmp/traffic-baseline.json``.
Each case runs in a fresh process; no real dataset or repository model is read.
"""
import argparse
import csv
import gc
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import tempfile
import time
import tracemalloc


def peak_rss_bytes():
    """OS process lifetime high-water mark, not Python allocations or delta RSS."""
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == 'darwin' else value * 1024)


def write_input(path, schema, rows):
    """Write fixed, invented feature values with bounded generator memory.

    Deliberate repeated rows and missing values exercise inference, not accuracy.
    No metadata identifiers or saved held-out examples are copied into this file.
    """
    with path.open('w', newline='', encoding='utf-8') as output:
        writer = csv.writer(output)
        writer.writerow([*schema, 'Label'])
        for index in range(rows):
            values = [float((index % 97 + 1) * (column + 1)) for column in range(len(schema))]
            if index % 31 == 0:
                values[0] = ''
            if index % 47 == 0 and len(values) > 1:
                values[1] = 'inf'
            writer.writerow([*values, 'SYNTHETIC ONLY'])


def run_case(model_path, *, rows, directory):
    """Measure ingestion and result access, excluding model/input setup and HTTP upload.

    model_path must be a trusted synthetic Joblib artifact (Pickle executes code).
    CLI supplies only its own ephemeral model. Tests supply their fitted fixture.
    """
    from apps.api.analyses import AnalysisStore
    if not 1 <= rows <= AnalysisStore.max_rows:
        raise ValueError(f'rows must be between 1 and {AnalysisStore.max_rows}; baseline never lifts quotas')
    from fastapi.testclient import TestClient
    from apps.api.main import Settings, create_app

    with tempfile.TemporaryDirectory(prefix='traffic-case-', dir=directory) as folder:
        input_path = Path(folder) / 'SYNTHETIC.csv'
        with TestClient(create_app(Settings(model_path=Path(model_path)))) as client:
            artifact = client.app.state.artifact
            if artifact is None or artifact['metadata']['provenance'] != 'synthetic':
                raise ValueError('Benchmark requires a trusted synthetic model')
            write_input(input_path, artifact['feature_schema'], rows)
            store = client.app.state.analyses
            stages = {}
            gc.collect()
            rss_before = peak_rss_bytes()
            tracemalloc.start()
            try:
                started = time.perf_counter()
                stage = started
                with input_path.open('rb') as source:
                    summary = store.create(source, artifact, input_path.name, client.app.state.model_identifier)
                stages['ingestion'] = time.perf_counter() - stage
                base = f'/api/v1/analyses/{summary.id}'
                if summary.total_flows != rows:
                    raise AssertionError('Incorrect ingested row count')

                stage = time.perf_counter()
                queries = [
                    '/flows?page_size=100&sort=probability&direction=desc',
                    '/flows?prediction=DDoS&probability_min=0.2&probability_max=0.8',
                    f'/flows?row_number={rows}', f'/flows/{rows}',
                ]
                for query in queries:
                    response = client.get(base + query)
                    response.raise_for_status()
                stages['queries'] = time.perf_counter() - stage
                max_error = 0.0
                for label, route in [('local_shap', f'/flows/{rows}/explanation'),
                                     ('global_shap', '/explanations/global?sample_size=50')]:
                    stage = time.perf_counter()
                    response = client.get(base + route)
                    response.raise_for_status()
                    body = response.json()
                    error = body.get('max_reconstruction_error', body.get('reconstruction_error'))
                    if error is None:
                        raise AssertionError('Missing SHAP reconstruction check')
                    max_error = max(max_error, error)
                    stages[label] = time.perf_counter() - stage

                stage = time.perf_counter()
                response = client.get(base + '/export')
                response.raise_for_status()
                exported = response.content
                stages['export'] = time.perf_counter() - stage
                elapsed = time.perf_counter() - started
                _, python_peak = tracemalloc.get_traced_memory()
                rss_peak = peak_rss_bytes()
            finally:
                tracemalloc.stop()
            # Verification is outside timed/allocation intervals; check every row.
            export_rows = 0
            for export_rows, record in enumerate(csv.DictReader(response.text.splitlines()), 1):
                if int(record['row_number']) != export_rows:
                    raise AssertionError('Export changed row order')
            if export_rows != rows:
                raise AssertionError('Incomplete export')
            storage_bytes = sum(path.stat().st_size for path in store.root.iterdir() if path.is_file())
            result = {
                'rows': rows, 'feature_count': len(artifact['feature_schema']),
                'input_bytes': input_path.stat().st_size, 'storage_bytes': storage_bytes,
                'export_bytes': len(exported), 'export_rows': export_rows,
                'export_sha256': hashlib.sha256(exported).hexdigest(),
                'total_seconds': elapsed, 'stage_seconds': stages,
                'rows_per_second': rows / stages['ingestion'],
                'python_peak_bytes': python_peak,
                'process_peak_rss_before_bytes': rss_before, 'process_peak_rss_bytes': rss_peak,
                'max_shap_reconstruction_error': max_error,
            }
            client.delete(base).raise_for_status()
            if store.sessions or list(store.root.iterdir()):
                raise AssertionError('Deletion leaked analysis storage')
            return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rows', nargs='+', type=int, default=[1000, 10000, 50000])
    parser.add_argument('--repeats', type=int, default=1)
    parser.add_argument('--output', type=Path)
    # Internal worker interface: parent always supplies a synthetic temporary model.
    parser.add_argument('--worker-model', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.repeats < 1 or any(not 1 <= count <= 50000 for count in args.rows):
        parser.error('rows must be 1..50000 and repeats must be positive; baseline retains current limits')
    with tempfile.TemporaryDirectory(prefix='ids-traffic-benchmark-') as folder:
        root = Path(folder)
        if args.worker_model:
            print(json.dumps(run_case(args.worker_model, rows=args.rows[0], directory=root)))
            return
        from src.synthetic import generate_fixture
        from src.train import train_model
        # Explicit opt-in setup; never trains or overwrites the repository model.
        generate_fixture(root / 'SYNTHETIC-training.csv', rows=400)
        train_model(root / 'SYNTHETIC-training.csv', root / 'model',
                    n_estimators=100, provenance='synthetic')
        cases = []
        for count in args.rows:
            for repeat in range(args.repeats):
                print(f'Synthetic lifecycle: rows={count}, repeat={repeat + 1}', file=sys.stderr)
                completed = subprocess.run([
                    sys.executable, '-m', 'scripts.benchmark_traffic', '--rows', str(count),
                    '--worker-model', str(root / 'model/model.joblib'),
                ], capture_output=True, text=True, check=True)
                case = json.loads(completed.stdout)
                case['repeat'] = repeat + 1
                cases.append(case)
        report = {
            'kind': 'synthetic software baseline; not detection accuracy or capacity certification',
            'environment': {
                'platform': platform.platform(), 'machine': platform.machine(),
                'python': platform.python_version(), 'logical_cpus': os.cpu_count(),
                'packages': {name: version(name) for name in
                             ['numpy', 'pandas', 'scikit-learn', 'shap', 'fastapi', 'httpx']},
                'command': [sys.executable, '-m', 'scripts.benchmark_traffic', *sys.argv[1:]],
                'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                'working_tree_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], text=True)),
                'thread_environment': {key: os.environ.get(key) for key in
                                       ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS']},
            },
            'model': {'provenance': 'synthetic', 'training_input_rows': 400, 'seed': 42,
                      'n_estimators': 100, 'max_depth': 12, 'n_jobs': -1},
            'measurement': {
                'timed': 'store.create including preflight; HTTP in-process queries, local/global SHAP, export',
                'excluded': 'startup imports, model fitting/loading, input generation, HTTP upload, export verification, deletion',
                'cold_start': 'first local SHAP includes lazy SHAP imports/JIT; each case uses a fresh process',
                'python_peak': 'tracemalloc during timed stages; includes tracing overhead in elapsed time',
                'rss_peak': 'OS process lifetime high-water RSS, includes imports and model loading; not a delta',
                'storage': 'completed analysis files only; excludes input CSV, model and in-memory predictions/offsets',
                'throughput': 'rows / ingestion seconds; total_seconds also includes result access',
            },
            'cases': cases,
        }
        rendered = json.dumps(report, indent=2) + '\n'
        if args.output:
            args.output.write_text(rendered, encoding='utf-8')
        else:
            print(rendered, end='')


if __name__ == '__main__':
    main()
