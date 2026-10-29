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
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    import pandas as pd

import numpy as np
from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import Response as CSVResponse
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
    predictions: "pd.DataFrame"
    offsets: list[int]
    path: Path
    size: int
    deadline: float


class AnalysisStore:
    max_upload_bytes = 200 * 1024 * 1024
    max_rows = 50_000
    max_columns = 256
    max_cells = 5_000_000
    upload_timeout = 300
    max_sessions = 5
    max_disk_bytes = 512 * 1024 * 1024
    ttl = 3600

    def __init__(self):
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
                    session.path.unlink(missing_ok=True)
                    del self.sessions[id]
                    self.expired = (self.expired + [id])[-128:]

    async def sweep(self):
        while True:
            await asyncio.sleep(60)
            self.cleanup()

    def close(self):
        with self.lock:
            self.sessions.clear()
            shutil.rmtree(self.root, ignore_errors=True)

    def get(self, id):
        self.cleanup()
        if id not in self.sessions:
            if id in self.expired:
                raise AnalysisError(410, 'analysis_expired', 'Analysis expired. Upload the CSV again.')
            raise AnalysisError(404, 'analysis_not_found', 'Analysis not found or no longer available. Upload the CSV again.')
        return self.sessions[id]

    def preflight(self, source):
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

    def create(self, source, artifact, filename, model_identifier):
        from src.data_loader import read_csv
        from src.predict import predict_batch, validate_features
        self.preflight(source)
        try:
            frame = read_csv(source, max_rows=self.max_rows)
            predictions, notes = predict_batch(artifact, frame)
            features, _ = validate_features(artifact, frame)
        except ValueError as exc:
            # Parser exceptions can include raw input. Only schema errors expose column names.
            message = str(exc)
            if not message.startswith(('Missing required feature', 'Non-numeric values', 'At least one flow', 'CSV exceeds')):
                message = 'Invalid CSV: use UTF-8, unique nonempty headers and well-formed comma-separated data rows.'
            raise AnalysisError(422, 'invalid_csv', message) from None
        id = secrets.token_urlsafe(24)
        path = self.root / (id + '.jsonl')
        offsets = []
        with self.lock:
            self.cleanup()
            budget = self.max_disk_bytes - sum(s.size for s in self.sessions.values())
            try:
                with path.open('wb') as output:
                    for values in features.itertuples(index=False, name=None):
                        row = {name: (None if np.isnan(value) else float(value))
                               for name, value in zip(features.columns, values)}
                        data = (json.dumps(row, allow_nan=False, separators=(',', ':')) + '\n').encode()
                        if output.tell() + len(data) > budget:
                            raise AnalysisError(503, 'storage_full', 'Local analysis storage is full. Delete an analysis and retry.')
                        offsets.append(output.tell())
                        output.write(data)
                created = time.time()
                ddos = int((predictions.prediction == 'DDoS').sum())
                summary = AnalysisSummary(id=id, total_flows=len(predictions), benign_count=len(predictions)-ddos,
                    ddos_count=ddos, ddos_percentage=100*ddos/len(predictions), model_identifier=model_identifier,
                    model_provenance=artifact['metadata']['provenance'], dataset_filename=filename,
                    created_at=datetime.fromtimestamp(created, timezone.utc),
                    expires_at=datetime.fromtimestamp(created+self.ttl, timezone.utc), **notes)
                self.sessions[id] = Session(summary, predictions, offsets, path, path.stat().st_size, time.monotonic()+self.ttl)
                return summary
            except BaseException:
                path.unlink(missing_ok=True)
                raise


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
                            raise AnalysisError(413, 'upload_too_large', 'CSV exceeds the 200 MB upload limit.')
                        source.write(chunk)
            except TimeoutError:
                raise AnalysisError(408, 'upload_timeout', 'CSV upload timed out after five minutes. Retry the upload.') from None
            source.seek(0)
            # Filename is display-only, never a filesystem path or export header.
            safe_name = filename.replace('\\', '/').split('/')[-1]
            safe_name = ''.join(c for c in safe_name if c.isprintable()) or 'flows.csv'
            return await run_in_threadpool(store.create, source, artifact, safe_name, request.app.state.model_identifier)
        finally:
            if source is not None:
                source.close()
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
            rows = store.get(id).predictions
            mask = rows.ddos_probability.between(probability_min, probability_max)
            if prediction:
                mask &= rows.prediction == prediction
            if row_number is not None:
                mask &= rows.row_number == row_number
            rows = rows.loc[mask]
            if sort == 'probability':
                rows = rows.sort_values(['ddos_probability', 'row_number'], ascending=[direction == 'asc', True])
            else:
                rows = rows.sort_values('row_number', ascending=direction == 'asc')
            return FlowPage(items=rows.iloc[(page-1)*page_size:page*page_size].to_dict(orient='records'),
                            total=len(rows), page=page, page_size=page_size)

    @api.get('/{id}/flows/{row_number}', response_model=FlowDetail, operation_id='getAnalysisFlow')
    def detail(id: str, row_number: int, request: Request):
        store = request.app.state.analyses
        with store.lock:
            session = store.get(id)
            if not 1 <= row_number <= len(session.offsets):
                raise AnalysisError(404, 'flow_not_found', 'Flow row not found.')
            with session.path.open('rb') as source:
                source.seek(session.offsets[row_number-1])
                features = json.loads(source.readline())
            return FlowDetail(**session.predictions.iloc[row_number-1].to_dict(), features=features)

    @api.get('/{id}/export', operation_id='exportAnalysis', response_class=CSVResponse,
             responses={200: {'content': {'text/csv': {'schema': {'type': 'string'}}}}})
    def export(id: str, request: Request):
        store = request.app.state.analyses
        with store.lock:
            data = store.get(id).predictions.to_csv(index=False)
        return CSVResponse(data, media_type='text/csv', headers={'Content-Disposition': 'attachment; filename="predictions.csv"'})

    @api.delete('/{id}', status_code=204, operation_id='deleteAnalysis')
    def delete(id: str, request: Request):
        store = request.app.state.analyses
        with store.lock:
            session = store.get(id)
            session.path.unlink(missing_ok=True)
            del store.sessions[id]
        return Response(status_code=204)

    return api
