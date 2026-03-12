from __future__ import annotations

import os
import time

import httpx
from opentelemetry import trace

from ai_observability.instrumentation.opentelemetry import configure_otel


def main() -> None:
    configure_otel(
        service_name="sample-real-client",
        environment=os.getenv("AI_OBS_ENVIRONMENT", "dev"),
        endpoint=os.getenv("AI_OBS_OTLP_ENDPOINT", "http://localhost:4318/v1/traces"),
        headers=os.getenv("AI_OBS_OTLP_HEADERS", ""),
    )
    tracer = trace.get_tracer("sample-real-client")
    with tracer.start_as_current_span("user.request") as span:
        span.set_attribute("ai.workflow_type", "chat")
        span.set_attribute("ai.feature", "incident-assistant")
        time.sleep(0.1)
        with httpx.Client(timeout=5.0) as client:
            response = client.get("http://localhost:8000/health")
            span.set_attribute("http.status_code", response.status_code)


if __name__ == "__main__":
    main()
