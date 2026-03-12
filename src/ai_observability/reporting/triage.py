from __future__ import annotations

from ai_observability.core.models import AITrace, IncidentFinding, IncidentReport


def build_incident_report(trace: AITrace) -> IncidentReport:
    findings: list[IncidentFinding] = []
    overall_status = "healthy"

    error_spans = [span for span in trace.spans if span.status in {"error", "timeout"}]
    degraded_spans = [span for span in trace.spans if span.status == "degraded"]
    model_spans = [span for span in trace.spans if span.kind == "model"]
    tool_spans = [span for span in trace.spans if span.kind == "tool"]
    retrieval_spans = [span for span in trace.spans if span.kind == "retrieval"]

    if error_spans:
        overall_status = "incident"
        first_error = error_spans[0]
        findings.append(
            IncidentFinding(
                severity="critical" if first_error.kind == "model" else "high",
                category=f"{first_error.kind}_failure",
                summary=f"Failure detected in span '{first_error.name}'.",
                evidence={
                    "error_type": first_error.error.type if first_error.error else "unknown",
                    "error_message": first_error.error.message if first_error.error else "unknown",
                    "span_id": first_error.span_id,
                },
            )
        )

    if degraded_spans and overall_status != "incident":
        overall_status = "warning"
        findings.append(
            IncidentFinding(
                severity="medium",
                category="degradation",
                summary=f"{len(degraded_spans)} degraded spans detected.",
                evidence={"span_names": [span.name for span in degraded_spans]},
            )
        )

    slow_spans = [span for span in trace.spans if span.duration_ms > 4000]
    if slow_spans:
        findings.append(
            IncidentFinding(
                severity="medium",
                category="latency",
                summary="One or more spans exceeded the 4s latency threshold.",
                evidence={
                    "slow_spans": {span.name: round(span.duration_ms, 2) for span in slow_spans}
                },
            )
        )
        if overall_status == "healthy":
            overall_status = "warning"

    total_tokens = sum(span.token_usage.total_tokens for span in model_spans)
    if total_tokens > 10000:
        findings.append(
            IncidentFinding(
                severity="medium",
                category="token_bloat",
                summary="Model token usage exceeded the 10k token threshold.",
                evidence={"total_model_tokens": total_tokens},
            )
        )

    if retrieval_spans and any(
        span.attributes.get("documents_found", 0) == 0 for span in retrieval_spans
    ):
        findings.append(
            IncidentFinding(
                severity="high",
                category="retrieval_quality",
                summary="At least one retrieval step returned zero documents.",
                evidence={"retrieval_spans": [span.name for span in retrieval_spans]},
            )
        )
        if overall_status == "healthy":
            overall_status = "warning"

    if tool_spans and any(span.retry_count > 0 for span in tool_spans):
        findings.append(
            IncidentFinding(
                severity="low",
                category="tool_retries",
                summary="Tool retries occurred during workflow execution.",
                evidence={
                    "retried_tools": [
                        {"name": span.name, "retry_count": span.retry_count}
                        for span in tool_spans
                        if span.retry_count > 0
                    ]
                },
            )
        )

    if not findings:
        findings.append(
            IncidentFinding(
                severity="low",
                category="healthy",
                summary="No material issues detected in the trace.",
            )
        )

    headline = {
        "healthy": "Trace completed without material reliability concerns.",
        "warning": "Trace completed with degradations requiring follow-up.",
        "incident": "Trace shows a production incident requiring triage.",
    }[overall_status]

    recommended_actions = [
        "Inspect the trace tree to confirm the first failing or slow span.",
        "Compare the incident against traces from the previous release and environment.",
        "Add the trace to the regression dataset if it represents a novel failure mode.",
    ]
    if error_spans:
        recommended_actions.insert(
            0, "Review prompt, model, and tool inputs for the first error span."
        )

    return IncidentReport(
        trace_id=trace.trace_id,
        overall_status=overall_status,
        headline=headline,
        findings=findings,
        recommended_actions=recommended_actions,
        release=trace.release,
        environment=trace.environment,
    )
