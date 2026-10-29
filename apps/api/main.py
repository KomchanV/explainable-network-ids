"""HTTP adapter for the unchanged offline IDS engine.

Only a server operator can configure the trusted Joblib path. Requests never
select, upload, or deserialize models. Run from the repository root.
"""
from contextlib import asynccontextmanager
from dataclasses import dataclass
import logging
import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat
from starlette.exceptions import HTTPException

VERSION = '0.2.0-alpha.1'
ROOT = Path(__file__).resolve().parents[2]
logger = logging.getLogger('uvicorn.error')


@dataclass(frozen=True)
class Settings:
    model_path: Path = ROOT / 'models/model.joblib'
    cors_origins: tuple[str, ...] = ('http://localhost:5173', 'http://127.0.0.1:5173')

    @classmethod
    def from_env(cls):
        path = Path(os.environ.get('IDS_MODEL_PATH', 'models/model.joblib')).expanduser()
        origins = os.environ.get('IDS_CORS_ORIGINS', ','.join(cls.cors_origins))
        return cls(model_path=path if path.is_absolute() else ROOT / path,
                   cors_origins=tuple(origin.strip() for origin in origins.split(',') if origin.strip()))


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: Literal['ok']
    version: str
    model_available: bool


class ModelResponse(BaseModel):
    format_version: int
    classifier: Literal['RandomForestClassifier']
    feature_schema: list[str]
    label_mapping: dict[str, int]
    provenance: Literal['synthetic', 'cic-ids2017', 'unspecified']
    dataset_filename: str
    dataset_sha256: str | None
    train_rows: int
    test_rows: int
    random_state: int


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    rows: list[dict[str, FiniteFloat | str | None]] = Field(min_length=1, max_length=1000)


class Prediction(BaseModel):
    row_number: int
    prediction: Literal['BENIGN', 'DDoS']
    ddos_probability: float = Field(ge=0, le=1)


class PredictResponse(BaseModel):
    predictions: list[Prediction]
    ignored_columns: list[str]
    imputed_cells: int


class ModelUnavailable(Exception):
    pass


def error_response(status, code, message, headers=None):
    return JSONResponse(status_code=status, headers=headers,
                        content=ErrorResponse(error=ErrorDetail(code=code, message=message)).model_dump())


def create_app(settings: Settings | None = None):
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app):
        # Load once per worker, off the import/OpenAPI-generation path. No fitting.
        from src.predict import load_artifact
        app.state.artifact = None
        try:
            app.state.artifact = load_artifact(settings.model_path)
            logger.info('Trusted IDS artifact loaded; provenance=%s',
                        app.state.artifact['metadata']['provenance'])
        except (OSError, ValueError):
            logger.warning('IDS model unavailable; health remains accessible', exc_info=True)
        yield
        app.state.artifact = None

    app = FastAPI(title='Explainable Network IDS API', version=VERSION,
                  description='Offline academic BENIGN/DDoS classifier. No live traffic monitoring.',
                  lifespan=lifespan,
                  responses={500: {'model': ErrorResponse}})
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                       allow_credentials=False, allow_methods=['GET', 'POST'],
                       allow_headers=['Content-Type'])

    @app.exception_handler(ModelUnavailable)
    async def unavailable(request, exc):
        return error_response(503, 'model_unavailable',
                              'The trusted model is unavailable. Contact the server operator.')

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        # Do not echo raw flow values or local server paths into errors/logs.
        return error_response(422, 'validation_error', 'Request does not match the API schema.')

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return error_response(exc.status_code, 'http_error', str(exc.detail), exc.headers)

    @app.exception_handler(Exception)
    async def unexpected(request, exc):
        logger.error('Unhandled API error', exc_info=exc)
        return error_response(500, 'internal_error', 'An unexpected server error occurred.')

    def artifact_for(request):
        artifact = getattr(request.app.state, 'artifact', None)
        if artifact is None:
            raise ModelUnavailable()
        return artifact

    @app.get('/health', response_model=HealthResponse, operation_id='getHealth')
    def health(request: Request):
        return HealthResponse(status='ok', version=VERSION,
                              model_available=getattr(request.app.state, 'artifact', None) is not None)

    @app.get('/model', response_model=ModelResponse, operation_id='getModel',
             responses={503: {'model': ErrorResponse}})
    def model(request: Request):
        artifact = artifact_for(request)
        metadata = artifact['metadata']
        return ModelResponse(format_version=artifact['format_version'],
                             classifier='RandomForestClassifier',
                             feature_schema=artifact['feature_schema'], label_mapping=artifact['label_mapping'],
                             provenance=metadata['provenance'], dataset_filename=metadata['dataset_filename'],
                             dataset_sha256=metadata.get('dataset_sha256'), train_rows=metadata['train_rows'],
                             test_rows=metadata['test_rows'], random_state=metadata['random_state'])

    @app.post('/predict', response_model=PredictResponse, operation_id='predictFlows',
              responses={422: {'model': ErrorResponse}, 503: {'model': ErrorResponse}})
    def predict(payload: PredictRequest, request: Request):
        import pandas as pd
        from src.predict import predict_batch
        artifact = artifact_for(request)
        try:
            predictions, notes = predict_batch(artifact, pd.DataFrame(payload.rows))
        except ValueError as exc:
            return error_response(422, 'invalid_features', str(exc))
        return PredictResponse(predictions=predictions.to_dict(orient='records'), **notes)

    return app


app = create_app()
