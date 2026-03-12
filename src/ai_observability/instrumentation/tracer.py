from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Optional

from ai_observability.core.models import (
    AIEvent,
    AISpan,
    AITrace,
    CostUsage,
    ErrorDetail,
    TokenUsage,
    utc_now,
)


class TraceBuilder:
    def __init__(
        self,
        *,
        service: str,
        environment: str,
        release: str,
        workflow_type: str,
        user_metadata: Optional[dict[str, Any]] = None,
        request_metadata: Optional[dict[str, Any]] = None,
        tags: Optional[dict[str, str]] = None,
    ) -> None:
        self.trace = AITrace(
            service=service,
            environment=environment,
            release=release,
            workflow_type=workflow_type,
            user_metadata=user_metadata or {},
            request_metadata=request_metadata or {},
            tags=tags or {},
        )

    @contextmanager
    def span(
        self,
        name: str,
        kind: str,
        parent_span_id: Optional[str] = None,
        attributes: Optional[dict[str, Any]] = None,
    ) -> Iterator[AISpan]:
        span = AISpan(
            name=name,
            kind=kind,
            parent_span_id=parent_span_id,
            attributes=attributes or {},
        )
        self.trace.spans.append(span)
        try:
            yield span
            if span.end_time is None:
                span.end_time = utc_now()
        except Exception as exc:  # pragma: no cover - defensive path
            span.status = "error"
            span.error = ErrorDetail(type=exc.__class__.__name__, message=str(exc), retryable=False)
            span.end_time = utc_now()
            self.trace.status = "error"
            raise

    def add_event(self, event_type: str, attributes: Optional[dict[str, Any]] = None) -> None:
        self.trace.events.append(AIEvent(event_type=event_type, attributes=attributes or {}))

    def record_error(self, span: AISpan, message: str, error_type: str = "RuntimeError") -> None:
        span.status = "error"
        span.error = ErrorDetail(type=error_type, message=message, retryable=False)
        self.trace.status = "error"

    def finalize(
        self,
        *,
        response_metadata: Optional[dict[str, Any]] = None,
    ) -> AITrace:
        if response_metadata:
            self.trace.response_metadata = response_metadata
        self.trace.ended_at = utc_now()
        return self.trace


def set_token_usage(span: AISpan, input_tokens: int, output_tokens: int) -> None:
    total = input_tokens + output_tokens
    span.token_usage = TokenUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total,
    )


def set_cost_usage(span: AISpan, input_cost: float, output_cost: float) -> None:
    total = input_cost + output_cost
    span.cost_usage = CostUsage(
        input_cost=input_cost,
        output_cost=output_cost,
        total_cost=total,
    )
