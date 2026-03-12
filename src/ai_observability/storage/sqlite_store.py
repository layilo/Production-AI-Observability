from __future__ import annotations

from typing import Any, Optional

import orjson
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    desc,
    select,
)
from sqlalchemy.engine import Engine

from ai_observability.core.models import AITrace, IncidentReport

metadata = MetaData()

traces_table = Table(
    "traces",
    metadata,
    Column("trace_id", String, primary_key=True),
    Column("service", String, nullable=False),
    Column("environment", String, nullable=False),
    Column("release", String, nullable=False),
    Column("workflow_type", String, nullable=False),
    Column("status", String, nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("ended_at", DateTime(timezone=True), nullable=True),
    Column("duration_ms", Float, nullable=False),
    Column("total_tokens", Integer, nullable=False),
    Column("total_cost", Float, nullable=False),
    Column("payload", JSON, nullable=False),
)

incidents_table = Table(
    "incidents",
    metadata,
    Column("trace_id", String, primary_key=True),
    Column("overall_status", String, nullable=False),
    Column("generated_at", DateTime(timezone=True), nullable=False),
    Column("payload", JSON, nullable=False),
)


class SQLiteStore:
    def __init__(self, db_url: str) -> None:
        self.engine: Engine = create_engine(db_url, future=True)
        metadata.create_all(self.engine)

    def upsert_trace(self, trace: AITrace) -> None:
        payload = trace.model_dump(mode="json")
        row = {
            "trace_id": trace.trace_id,
            "service": trace.service,
            "environment": trace.environment,
            "release": trace.release,
            "workflow_type": trace.workflow_type,
            "status": trace.status,
            "started_at": trace.started_at,
            "ended_at": trace.ended_at,
            "duration_ms": trace.summary.total_duration_ms,
            "total_tokens": trace.summary.total_tokens,
            "total_cost": trace.summary.total_cost,
            "payload": payload,
        }
        with self.engine.begin() as conn:
            conn.execute(traces_table.delete().where(traces_table.c.trace_id == trace.trace_id))
            conn.execute(traces_table.insert().values(**row))

    def upsert_incident(self, report: IncidentReport) -> None:
        payload = report.model_dump(mode="json")
        with self.engine.begin() as conn:
            conn.execute(
                incidents_table.delete().where(incidents_table.c.trace_id == report.trace_id)
            )
            conn.execute(
                incidents_table.insert().values(
                    trace_id=report.trace_id,
                    overall_status=report.overall_status,
                    generated_at=report.generated_at,
                    payload=payload,
                )
            )

    def list_traces(self, limit: int = 50, status: Optional[str] = None) -> list[AITrace]:
        stmt = select(traces_table.c.payload).order_by(desc(traces_table.c.started_at)).limit(limit)
        if status:
            stmt = stmt.where(traces_table.c.status == status)
        with self.engine.begin() as conn:
            rows = conn.execute(stmt).all()
        return [AITrace.model_validate(row.payload) for row in rows]

    def get_trace(self, trace_id: str) -> Optional[AITrace]:
        stmt = select(traces_table.c.payload).where(traces_table.c.trace_id == trace_id)
        with self.engine.begin() as conn:
            row = conn.execute(stmt).first()
        return AITrace.model_validate(row.payload) if row else None

    def get_incident(self, trace_id: str) -> Optional[IncidentReport]:
        stmt = select(incidents_table.c.payload).where(incidents_table.c.trace_id == trace_id)
        with self.engine.begin() as conn:
            row = conn.execute(stmt).first()
        return IncidentReport.model_validate(row.payload) if row else None

    def metrics_summary(self) -> dict[str, Any]:
        with self.engine.begin() as conn:
            rows = conn.execute(select(traces_table.c.payload)).all()
        traces = [AITrace.model_validate(row.payload) for row in rows]
        total_traces = len(traces)
        total_cost = round(sum(trace.summary.total_cost for trace in traces), 6)
        total_tokens = sum(trace.summary.total_tokens for trace in traces)
        errors = sum(1 for trace in traces if trace.status != "ok")
        avg_latency = round(
            sum(trace.summary.total_duration_ms for trace in traces) / total_traces,
            2,
        ) if total_traces else 0.0
        by_workflow: dict[str, int] = {}
        for trace in traces:
            by_workflow[trace.workflow_type] = by_workflow.get(trace.workflow_type, 0) + 1
        return {
            "total_traces": total_traces,
            "error_rate": round(errors / total_traces, 4) if total_traces else 0.0,
            "avg_latency_ms": avg_latency,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "by_workflow": by_workflow,
        }

    def export_json(self) -> bytes:
        with self.engine.begin() as conn:
            rows = conn.execute(select(traces_table.c.payload)).all()
        return orjson.dumps([row.payload for row in rows], option=orjson.OPT_INDENT_2)
