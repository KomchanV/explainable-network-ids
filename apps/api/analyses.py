"""Bounded, single-worker offline analysis resources; no uploaded identifiers retained."""
import asyncio
import csv
from io import TextIOWrapper
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import secrets
import shutil
import tempfile
import threading
import time
from typing import Literal
import os
import sqlite3

from apps.api import result_storage as storage

import numpy as np
from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import Response as CSVResponse, StreamingResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool


class AnalysisError(Exception):
    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message


class FlowPrediction(BaseModel):
    row_number: int
    prediction: Literal['BENIGN', 'DDoS']
    ddos_probability: float = Field(ge=0, le=1, description='Uncalibrated model output, not confidence or severity.')


class AnalysisSummary(BaseModel):
    id: str
    total_flows: int
    benign_count: int
    ddos_count: int
    ddos_percentage: float
    model_identifier: str
    model_provenance: Literal['synthetic', 'cic-ids2017', 'unspecified']
    dataset_filename: str
    created_at: datetime
    expires_at: datetime
    ignored_columns: list[str]
    imputed_cells: int


class FlowPage(BaseModel):
    items: list[FlowPrediction]
    total: int
    page: int
    page_size: int


class FlowDetail(FlowPrediction):
    features: dict[str, float | None]


@dataclass
class Session:
    summary: AnalysisSummary
    schema: tuple[str, ...]
    path: Path
    size: int
    deadline: float


class AnalysisStore:
    max_upload_bytes = 200 * 1024 * 1024
    max_rows = 100_000
    max_columns = 256
    max_cells = 25_600_000
    upload_timeout = 300
    max_sessions = 5
    max_disk_bytes = 512 * 1024 * 1024
    ttl = 3600
    batch_rows = 10_000
    processing_timeout = 600
    export_timeout = 300
    max_exports = 2

    def __init__(self):
        # Finite operator configuration; no runtime/client-controlled limits.
        for name in ('max_upload_bytes', 'max_rows', 'max_columns', 'max_cells',
                     'max_sessions', 'max_disk_bytes', 'ttl', 'batch_rows',
                     'upload_timeout', 'processing_timeout', 'export_timeout', 'max_exports'):
            key = 'IDS_ANALYSIS_' + name.upper()
            value = int(os.environ.get(key, getattr(self, name)))
            if value <= 0 or (name == 'batch_rows' and value > 100_000):
                raise ValueError(f'{key} must be positive; batch_rows must not exceed 100000.')
            setattr(self, name, value)
        self.upload_bytes = 0
        self.exports: set[storage.ExportLease] = set()
        self.root = Path(tempfile.mkdtemp(prefix='ids-analyses-'))
        self.sessions: dict[str, Session] = {}
        self.expired: list[str] = []
        self.lock = threading.RLock()
        # One ingestion per process bounds parser/inference memory and temporary disk.
        self.ingestion = threading.Lock()
        self.explanation = threading.Lock()

    def cleanup(self):
        with self.lock:
            for id, session in list(self.sessions.items()):
                if time.monotonic() >= session.deadline or self.ttl == 0:
                    del self.sessions[id]
                    self.reap(session)
                    self.expired = (self.expired + [id])[-128:]

    async def sweep(self):
        while True:
            await asyncio.sleep(60)
            self.cleanup()

    def close(self):
        with self.lock:
            for lease in list(self.exports):
                lease.close()
            self.sessions.clear()
            shutil.rmtree(self.root, ignore_errors=True)

    def get(self, id):
        self.cleanup()
        if id not in self.sessions:
            if id in self.expired:
                raise AnalysisError(410, 'analysis_expired', 'Analysis expired. Upload the CSV again.')
            raise AnalysisError(404, 'analysis_not_found', 'Analysis not found or no longer available. Upload the CSV again.')
        return self.sessions[id]

    def preflight(self, source, checkpoint=lambda: None):
        """Bound parser dimensions without transforming values or model features."""
        source.seek(0)
        text = TextIOWrapper(source, encoding='utf-8-sig', newline='')
        try:
            header_line = text.readline(65_537)
            if len(header_line) > 65_536:
                raise ValueError('CSV header exceeds 64 KiB.')
            header = next(csv.reader([header_line], strict=True), [])
            if len(header) > self.max_columns:
                raise ValueError(f'CSV exceeds the {self.max_columns} column limit.')
            def lines():
                while line := text.readline(1_048_577):
                    checkpoint()
                    if len(line) > 1_048_576:
                        raise ValueError('CSV physical line exceeds 1 MiB.')
                    yield line
            count = 0
            for row in csv.reader(lines(), strict=True):
                if not row or (len(row) == 1 and not row[0].strip()):
                    continue
                if len(row) > len(header):
                    raise ValueError('CSV row contains more fields than the header.')
                count += 1
                if count > self.max_rows:
                    raise ValueError(f'CSV exceeds the {self.max_rows:,} row limit. Use the CLI for larger files.')
                if count * len(header) > self.max_cells:
                    raise ValueError(f'CSV exceeds the {self.max_cells:,} cell limit. Remove unused extra columns.')
        except (ValueError, UnicodeError, csv.Error) as exc:
            message = str(exc) if str(exc).startswith('CSV exceeds') else 'Invalid CSV: use UTF-8 with a single-line header, bounded records and well-formed comma-separated rows.'
            raise AnalysisError(422, 'invalid_csv', message) from None
        finally:
            text.detach()
            source.seek(0)

    def disk_usage(self):
        # Named SQLite/journal files plus the unlinked upload TemporaryFile.
        return self.upload_bytes + sum(path.stat().st_size for path in self.root.iterdir() if path.is_file())

    def reap(self, session):
        if (session.summary.id not in self.sessions
                and not any(lease.session is session for lease in self.exports)):
            session.path.unlink(missing_ok=True)

    def delete(self, id):
        session = self.get(id)
        del self.sessions[id]
        self.reap(session)

    def export(self, id):
        with self.lock:
            session = self.get(id)
            if len(self.exports) >= self.max_exports:
                raise AnalysisError(503, 'export_busy', 'Local export limit reached. Retry after an export finishes.')
            lease = storage.ExportLease(self, session)
            self.exports.add(lease)
            return lease

    def create(self, source, artifact, filename, model_identifier):
        from src.data_loader import iter_csv_chunks
        from src.predict import predict_batch, validate_features
        deadline = time.monotonic() + self.processing_timeout
        def checkpoint():
            if time.monotonic() >= deadline:
                raise AnalysisError(408, 'processing_timeout', 'Analysis processing deadline exceeded. Use a smaller CSV.')
        source.seek(0, 2)
        source_bytes = source.tell()
        source.seek(0)
        if source_bytes > self.max_upload_bytes:
            raise AnalysisError(413, 'upload_too_large', 'CSV exceeds the configured upload byte limit.')
        self.preflight(source, checkpoint)
        id = secrets.token_urlsafe(24)
        path = self.root / (id + '.sqlite')
        connection = None
        try:
            with self.lock:
                self.cleanup()
                if len(self.sessions) >= self.max_sessions:
                    raise AnalysisError(503, 'session_limit', 'Local session limit reached. Delete an analysis and retry.')
                budget = self.max_disk_bytes - self.disk_usage() - max(0, source_bytes - self.upload_bytes)
                connection = storage.connect(path)
                storage.initialize(connection, budget)
            total = ddos = imputed = 0
            ignored = []
            for frame in iter_csv_chunks(source, batch_size=self.batch_rows,
                                         max_rows=self.max_rows, checkpoint=checkpoint):
                predictions, notes = predict_batch(artifact, frame)
                features, _ = validate_features(artifact, frame)
                checkpoint()
                def records():
                    for offset, (values, predicted) in enumerate(zip(
                            features.itertuples(index=False, name=None),
                            predictions.itertuples(index=False, name=None)), 1):
                        numeric = [None if np.isnan(value) else float(value) for value in values]
                        yield (total + offset, int(predicted[1] == 'DDoS'), float(predicted[2]),
                               json.dumps(numeric, allow_nan=False, separators=(',', ':')))
                with connection:
                    connection.executemany('INSERT INTO flows VALUES (?,?,?,?)', records())
                total += len(predictions)
                ddos += int((predictions.prediction == 'DDoS').sum())
                imputed += notes['imputed_cells']
                ignored = notes['ignored_columns']
                # Release the previous batch before the iterator parses the next.
                del frame, features, predictions
            checkpoint()
            connection.close()
            connection = None
            created = time.time()
            summary = AnalysisSummary(id=id, total_flows=total, benign_count=total-ddos,
                ddos_count=ddos, ddos_percentage=100*ddos/total, model_identifier=model_identifier,
                model_provenance=artifact['metadata']['provenance'], dataset_filename=filename,
                created_at=datetime.fromtimestamp(created, timezone.utc),
                expires_at=datetime.fromtimestamp(created+self.ttl, timezone.utc),
                ignored_columns=ignored, imputed_cells=imputed)
            with self.lock:
                self.sessions[id] = Session(summary, tuple(artifact['feature_schema']), path,
                    path.stat().st_size, time.monotonic()+self.ttl)
            return summary
        except ValueError as exc:
            message = str(exc)
            if not message.startswith(('Missing required feature', 'Non-numeric values', 'At least one flow', 'CSV exceeds')):
                message = 'Invalid CSV: use UTF-8, unique nonempty headers and well-formed comma-separated data rows.'
            raise AnalysisError(422, 'invalid_csv', message) from None
        except (sqlite3.Error, OSError):
            raise AnalysisError(503, 'storage_full', 'Local analysis storage is full or unavailable. Delete an analysis and retry.') from None
        finally:
            if connection is not None:
                connection.close()
            if id not in self.sessions:
                for partial in self.root.glob(path.name + '*'):
                    partial.unlink(missing_ok=True)


class ExportResponse(StreamingResponse):
    def __init__(self, lease):
        self.lease = lease
        super().__init__(lease.chunks(), media_type='text/csv', headers={
            'Content-Disposition': 'attachment; filename="predictions.csv"'})

    async def __call__(self, scope, receive, send):
        try:
            async with asyncio.timeout(max(0, self.lease.deadline - time.monotonic())):
                await super().__call__(scope, receive, send)
        finally:
            self.lease.close()


def router(artifact_for, error_model):
    api = APIRouter(prefix='/api/v1/analyses', responses={
        code: {'model': error_model} for code in (404, 408, 410, 413, 415, 422, 503)})

    @api.post('', response_model=AnalysisSummary, status_code=201, operation_id='createAnalysis',
        openapi_extra={'requestBody': {'required': True, 'content': {'text/csv': {
            'schema': {'type': 'string', 'format': 'binary'}}}}})
    async def create(request: Request, filename: str = Query(default='flows.csv', max_length=255)):
        artifact = artifact_for(request)
        if request.headers.get('content-type', '').split(';')[0].lower() != 'text/csv':
            raise AnalysisError(415, 'unsupported_media_type', 'Upload a CSV using Content-Type: text/csv.')
        store = request.app.state.analyses
        if not store.ingestion.acquire(blocking=False):
            raise AnalysisError(503, 'analysis_busy', 'Another CSV is being processed. Retry after it finishes.')
        source = None
        try:
            with store.lock:
                store.cleanup()
                if len(store.sessions) >= store.max_sessions:
                    raise AnalysisError(503, 'session_limit', 'Local session limit reached. Delete an analysis and retry.')
            source = tempfile.TemporaryFile(dir=store.root)
            size = 0
            try:
                async with asyncio.timeout(store.upload_timeout):
                    async for chunk in request.stream():
                        size += len(chunk)
                        if size > store.max_upload_bytes:
                            raise AnalysisError(413, 'upload_too_large', 'CSV exceeds the configured upload byte limit.')
                        with store.lock:
                            if store.disk_usage() + len(chunk) > store.max_disk_bytes:
                                raise AnalysisError(503, 'storage_full', 'Local analysis storage is full. Delete an analysis and retry.')
                            source.write(chunk)
                            store.upload_bytes = size
            except TimeoutError:
                raise AnalysisError(408, 'upload_timeout', 'CSV upload timed out after five minutes. Retry the upload.') from None
            source.seek(0)
            # Filename is display-only, never a filesystem path or export header.
            safe_name = filename.replace('\\', '/').split('/')[-1]
            safe_name = ''.join(c for c in safe_name if c.isprintable()) or 'flows.csv'
            task = asyncio.create_task(run_in_threadpool(store.create, source, artifact, safe_name, request.app.state.model_identifier))
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                # Do not close the source/release ingestion while its worker runs.
                await asyncio.shield(task)
                raise
        except OSError:
            raise AnalysisError(503, 'storage_full', 'Local analysis storage is full or unavailable. Delete an analysis and retry.') from None
        finally:
            if source is not None:
                source.close()
            store.upload_bytes = 0
            store.ingestion.release()

    @api.get('/{id}', response_model=AnalysisSummary, operation_id='getAnalysis')
    def summary(id: str, request: Request):
        store = request.app.state.analyses
        with store.lock:
            return store.get(id).summary

    @api.get('/{id}/flows', response_model=FlowPage, operation_id='listAnalysisFlows')
    def flows(id: str, request: Request, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
              prediction: Literal['BENIGN', 'DDoS'] | None = None,
              probability_min: float = Query(0, ge=0, le=1), probability_max: float = Query(1, ge=0, le=1),
              sort: Literal['row_number', 'probability'] = 'row_number', direction: Literal['asc', 'desc'] = 'asc',
              row_number: int | None = Query(None, ge=1)):
        if probability_min > probability_max:
            raise AnalysisError(422, 'invalid_range', 'Minimum probability must not exceed maximum probability.')
        store = request.app.state.analyses
        with store.lock:
            session = store.get(id)
            where, params = ['probability BETWEEN ? AND ?'], [probability_min, probability_max]
            if prediction:
                where.append('prediction = ?')
                params.append(int(prediction == 'DDoS'))
            if row_number is not None:
                if row_number > session.summary.total_flows:
                    return FlowPage(items=[], total=0, page=page, page_size=page_size)
                where.append('row_number = ?')
                params.append(row_number)
            clause = ' AND '.join(where)
            # Only enum-derived SQL syntax is interpolated; all input values bind.
            order = ('probability' if sort == 'probability' else 'row_number')
            order += ' DESC' if direction == 'desc' else ' ASC'
            if sort == 'probability':
                order += ', row_number ASC'
            scan = ('INDEXED BY probability_' + direction) if sort == 'probability' else 'NOT INDEXED'
            with storage.reading(session.path) as connection:
                total = connection.execute('SELECT count(*) FROM flows WHERE '+clause, params).fetchone()[0]
                offset = (page-1)*page_size
                rows = [] if offset >= total else connection.execute(f'SELECT {storage.COLUMNS} FROM flows {scan} WHERE {clause} ORDER BY {order} LIMIT ? OFFSET ?',
                    [*params, page_size, offset]).fetchall()
            return FlowPage(items=[storage.prediction(row) for row in rows], total=total, page=page, page_size=page_size)

    @api.get('/{id}/flows/{row_number}', response_model=FlowDetail, operation_id='getAnalysisFlow')
    def detail(id: str, row_number: int, request: Request):
        store = request.app.state.analyses
        with store.lock:
            session = store.get(id)
            if not 1 <= row_number <= session.summary.total_flows:
                raise AnalysisError(404, 'flow_not_found', 'Flow row not found.')
            with storage.reading(session.path) as connection:
                row = connection.execute(f'SELECT {storage.COLUMNS}, features FROM flows WHERE row_number=?', (row_number,)).fetchone()
            if row is None:
                raise AnalysisError(404, 'flow_not_found', 'Flow row not found.')
            return FlowDetail(**storage.prediction(row), features=dict(zip(session.schema, json.loads(row[3]))))

    @api.get('/{id}/export', operation_id='exportAnalysis', response_class=CSVResponse,
             responses={200: {'content': {'text/csv': {'schema': {'type': 'string'}}}}})
    def export(id: str, request: Request):
        store = request.app.state.analyses
        return ExportResponse(store.export(id))

    @api.delete('/{id}', status_code=204, operation_id='deleteAnalysis')
    def delete(id: str, request: Request):
        store = request.app.state.analyses
        with store.lock:
            store.delete(id)
        return Response(status_code=204)

    return api
