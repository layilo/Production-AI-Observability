from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from ai_observability.core.config import Settings, get_settings
from ai_observability.core.models import AITrace, TraceQueryResult
from ai_observability.ingestion.service import TraceIngestionService
from ai_observability.instrumentation.opentelemetry import configure_otel, instrument_fastapi
from ai_observability.reporting.render import render_incident_report
from ai_observability.reporting.triage import build_incident_report
from ai_observability.sample_app.workflows import (
    generate_agent_trace,
    generate_chat_trace,
    generate_demo_traces,
    generate_rag_trace,
)
from ai_observability.storage.sqlite_store import SQLiteStore


def get_store(settings: Settings = Depends(get_settings)) -> SQLiteStore:
    return SQLiteStore(f"sqlite:///{settings.db_file}")


def get_ingestion_service(
    settings: Settings = Depends(get_settings),
    store: SQLiteStore = Depends(get_store),
) -> TraceIngestionService:
    return TraceIngestionService(settings, store)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    if settings.otlp_enabled:
        configure_otel(
            service_name=settings.app_name,
            environment=settings.environment,
            endpoint=settings.otlp_endpoint,
            headers=settings.otlp_headers,
        )
        instrument_fastapi(app)
    yield


app = FastAPI(
    title="Production AI Observability Platform",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name, "environment": settings.environment}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/v1/traces", response_model=AITrace)
def ingest_trace(
    trace: AITrace,
    service: TraceIngestionService = Depends(get_ingestion_service),
) -> AITrace:
    ingested = service.ingest(trace)
    if ingested is None:
        raise HTTPException(status_code=202, detail="Trace dropped by sampling policy.")
    return ingested


@app.get("/v1/traces", response_model=TraceQueryResult)
def list_traces(
    limit: int = Query(default=50, le=500),
    status: Optional[str] = None,
    store: SQLiteStore = Depends(get_store),
) -> TraceQueryResult:
    items = store.list_traces(limit=limit, status=status)
    return TraceQueryResult(items=items, total=len(items))


@app.get("/v1/traces/{trace_id}", response_model=AITrace)
def get_trace(trace_id: str, store: SQLiteStore = Depends(get_store)) -> AITrace:
    trace = store.get_trace(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found.")
    return trace


@app.get("/v1/metrics/summary")
def get_metrics_summary(store: SQLiteStore = Depends(get_store)) -> dict:
    return store.metrics_summary()


@app.get("/v1/incidents/triage/{trace_id}")
def get_incident(trace_id: str, store: SQLiteStore = Depends(get_store)) -> dict:
    trace = store.get_trace(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found.")
    report = build_incident_report(trace)
    return report.model_dump(mode="json")


@app.get("/v1/reports/incident/{trace_id}", response_class=HTMLResponse)
def render_incident(trace_id: str, store: SQLiteStore = Depends(get_store)) -> HTMLResponse:
    trace = store.get_trace(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found.")
    report = build_incident_report(trace)
    path = render_incident_report(trace, report, Path("artifacts") / f"incident-{trace_id}.html")
    return HTMLResponse(path.read_text(encoding="utf-8"))


@app.get("/v1/export/traces")
def export_traces(store: SQLiteStore = Depends(get_store)) -> Response:
    return Response(store.export_json(), media_type="application/json")


@app.post("/v1/demo/generate")
def generate_demo(
    count: int = Query(default=10, ge=1, le=100),
    service: TraceIngestionService = Depends(get_ingestion_service),
    settings: Settings = Depends(get_settings),
) -> dict:
    ingested = 0
    for trace in generate_demo_traces(settings, count=count):
        if service.ingest(trace):
            ingested += 1
    return {"requested": count, "ingested": ingested}


@app.post("/v1/sample/chat", response_model=AITrace)
def sample_chat(
    induce_error: bool = False,
    service: TraceIngestionService = Depends(get_ingestion_service),
    settings: Settings = Depends(get_settings),
) -> AITrace:
    return service.ingest(generate_chat_trace(settings, induce_error=induce_error))


@app.post("/v1/sample/rag", response_model=AITrace)
def sample_rag(
    service: TraceIngestionService = Depends(get_ingestion_service),
    settings: Settings = Depends(get_settings),
) -> AITrace:
    import random

    return service.ingest(generate_rag_trace(settings, random.Random()))


@app.post("/v1/sample/agent", response_model=AITrace)
def sample_agent(
    service: TraceIngestionService = Depends(get_ingestion_service),
    settings: Settings = Depends(get_settings),
) -> AITrace:
    import random

    return service.ingest(generate_agent_trace(settings, random.Random()))


def run() -> None:
    import uvicorn

    uvicorn.run("ai_observability.api.main:app", host="0.0.0.0", port=8000, reload=False)
