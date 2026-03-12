from __future__ import annotations

from ai_observability.core.config import Settings
from ai_observability.core.metrics import (
    ACTIVE_INCIDENTS,
    TRACE_COST_TOTAL,
    TRACE_DURATION_MS,
    TRACE_INGESTED_TOTAL,
    TRACE_TOKENS_TOTAL,
)
from ai_observability.core.models import AITrace, TraceSummary
from ai_observability.core.redaction import redact_value
from ai_observability.core.sampling import should_sample
from ai_observability.reporting.triage import build_incident_report
from ai_observability.storage.sqlite_store import SQLiteStore


class TraceIngestionService:
    def __init__(self, settings: Settings, store: SQLiteStore) -> None:
        self.settings = settings
        self.store = store

    def ingest(self, trace: AITrace):
        if not should_sample(trace.trace_id, self.settings.sampling_rate):
            return None

        if self.settings.redaction_enabled:
            trace.user_metadata = redact_value(
                trace.user_metadata, self.settings.redaction_field_set
            )
            trace.request_metadata = redact_value(
                trace.request_metadata, self.settings.redaction_field_set
            )
            trace.response_metadata = redact_value(
                trace.response_metadata, self.settings.redaction_field_set
            )
            for span in trace.spans:
                span.attributes = redact_value(span.attributes, self.settings.redaction_field_set)
                for event in span.events:
                    event.attributes = redact_value(
                        event.attributes, self.settings.redaction_field_set
                    )

        trace.summary = self._build_summary(trace)
        self.store.upsert_trace(trace)
        incident = build_incident_report(trace)
        self.store.upsert_incident(incident)
        self._record_metrics(trace)
        return trace

    def _build_summary(self, trace: AITrace) -> TraceSummary:
        summary = TraceSummary(
            total_duration_ms=round(trace.duration_ms, 2),
            error_count=sum(1 for span in trace.spans if span.status in {"error", "timeout"}),
            span_count=len(trace.spans),
            model_call_count=sum(1 for span in trace.spans if span.kind == "model"),
            retrieval_count=sum(1 for span in trace.spans if span.kind == "retrieval"),
            tool_call_count=sum(1 for span in trace.spans if span.kind == "tool"),
            total_tokens=sum(span.token_usage.total_tokens for span in trace.spans),
            total_cost=round(sum(span.cost_usage.total_cost for span in trace.spans), 6),
            status=trace.status,
        )
        durations = sorted(trace.spans, key=lambda item: item.duration_ms, reverse=True)
        if durations and durations[0].status != "ok":
            summary.dominant_failure_stage = durations[0].name
        elif durations:
            summary.dominant_failure_stage = durations[0].name
        return summary

    def _record_metrics(self, trace: AITrace) -> None:
        labels = (trace.service, trace.environment, trace.status, trace.workflow_type)
        TRACE_INGESTED_TOTAL.labels(*labels).inc()
        TRACE_DURATION_MS.labels(trace.service, trace.environment, trace.workflow_type).observe(
            trace.summary.total_duration_ms
        )
        TRACE_TOKENS_TOTAL.labels(trace.service, trace.environment, trace.workflow_type).inc(
            trace.summary.total_tokens
        )
        TRACE_COST_TOTAL.labels(trace.service, trace.environment, trace.workflow_type).inc(
            trace.summary.total_cost
        )
        ACTIVE_INCIDENTS.labels(trace.service, trace.environment).set(
            1 if trace.status != "ok" else 0
        )
