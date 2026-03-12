from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class CostUsage(BaseModel):
    input_cost: float = 0.0
    output_cost: float = 0.0
    total_cost: float = 0.0


class ErrorDetail(BaseModel):
    type: str
    message: str
    retryable: bool = False
    stack: Optional[str] = None


class AIEvent(BaseModel):
    event_type: str
    timestamp: datetime = Field(default_factory=utc_now)
    attributes: dict[str, Any] = Field(default_factory=dict)


class AISpan(BaseModel):
    span_id: str = Field(default_factory=lambda: uuid4().hex)
    parent_span_id: Optional[str] = None
    name: str
    kind: Literal[
        "request",
        "prompt",
        "model",
        "retrieval",
        "tool",
        "agent_step",
        "http",
        "db",
        "guardrail",
        "workflow",
    ]
    start_time: datetime = Field(default_factory=utc_now)
    end_time: Optional[datetime] = None
    status: Literal["ok", "error", "timeout", "degraded"] = "ok"
    attributes: dict[str, Any] = Field(default_factory=dict)
    events: list[AIEvent] = Field(default_factory=list)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    cost_usage: CostUsage = Field(default_factory=CostUsage)
    retry_count: int = 0
    error: Optional[ErrorDetail] = None

    @property
    def duration_ms(self) -> float:
        end = self.end_time or utc_now()
        return max((end - self.start_time).total_seconds() * 1000, 0.0)


class TraceSummary(BaseModel):
    total_duration_ms: float = 0.0
    error_count: int = 0
    span_count: int = 0
    model_call_count: int = 0
    retrieval_count: int = 0
    tool_call_count: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    status: Literal["ok", "error", "degraded"] = "ok"
    dominant_failure_stage: Optional[str] = None


class AITrace(BaseModel):
    trace_id: str = Field(default_factory=lambda: uuid4().hex)
    request_id: str = Field(default_factory=lambda: uuid4().hex)
    service: str
    environment: str
    release: str
    workflow_type: Literal["chat", "rag", "agent", "summarization", "classification", "custom"]
    status: Literal["ok", "error", "degraded"] = "ok"
    started_at: datetime = Field(default_factory=utc_now)
    ended_at: Optional[datetime] = None
    user_metadata: dict[str, Any] = Field(default_factory=dict)
    request_metadata: dict[str, Any] = Field(default_factory=dict)
    response_metadata: dict[str, Any] = Field(default_factory=dict)
    spans: list[AISpan] = Field(default_factory=list)
    events: list[AIEvent] = Field(default_factory=list)
    summary: TraceSummary = Field(default_factory=TraceSummary)
    tags: dict[str, str] = Field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        end = self.ended_at or utc_now()
        return max((end - self.started_at).total_seconds() * 1000, 0.0)


class IncidentFinding(BaseModel):
    severity: Literal["low", "medium", "high", "critical"]
    category: str
    summary: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class IncidentReport(BaseModel):
    trace_id: str
    generated_at: datetime = Field(default_factory=utc_now)
    overall_status: Literal["healthy", "warning", "incident"] = "healthy"
    headline: str
    findings: list[IncidentFinding] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    release: str
    environment: str


class TraceQueryResult(BaseModel):
    items: list[AITrace]
    total: int
