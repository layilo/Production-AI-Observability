from __future__ import annotations

import random
import time
from typing import Any

from ai_observability.core.config import Settings
from ai_observability.core.models import AIEvent, AITrace
from ai_observability.instrumentation.tracer import TraceBuilder, set_cost_usage, set_token_usage


def _sleep_ms(duration_ms: int) -> None:
    time.sleep(duration_ms / 1000)


def _costs(settings: Settings, input_tokens: int, output_tokens: int) -> tuple[float, float]:
    input_cost = (input_tokens / 1000) * settings.cost_per_1k_input_tokens
    output_cost = (output_tokens / 1000) * settings.cost_per_1k_output_tokens
    return round(input_cost, 6), round(output_cost, 6)


def generate_chat_trace(settings: Settings, *, induce_error: bool = False) -> AITrace:
    builder = TraceBuilder(
        service=settings.app_name,
        environment=settings.environment,
        release=settings.release,
        workflow_type="chat",
        user_metadata={"user_id": "demo-user", "user_email": "person@example.com"},
        request_metadata={"prompt": "Summarize last night's incident and propose next steps."},
        tags={"mode": "demo"},
    )
    builder.add_event("request_received", {"channel": "api"})
    with builder.span("chat.request", "request", attributes={"route": "/sample/chat"}) as root:
        _sleep_ms(30)
        with builder.span(
            "chat.prompt_builder",
            "prompt",
            parent_span_id=root.span_id,
        ) as prompt_span:
            _sleep_ms(25)
            prompt_span.attributes.update(
                {"template": "incident-summary-v2", "input": "sensitive data"}
            )
        with builder.span("chat.model_call", "model", parent_span_id=root.span_id) as model_span:
            _sleep_ms(80)
            set_token_usage(model_span, 1200, 240)
            input_cost, output_cost = _costs(settings, 1200, 240)
            set_cost_usage(model_span, input_cost, output_cost)
            model_span.attributes.update({"model": "gpt-4.1-mini", "temperature": 0.2})
            if induce_error:
                builder.record_error(model_span, "Upstream model timeout", "TimeoutError")
        root.end_time = model_span.end_time
    trace = builder.finalize(
        response_metadata={"completion": "Demo completion", "status_code": 200}
    )
    if induce_error:
        trace.status = "error"
    return trace


def generate_rag_trace(settings: Settings, rng: random.Random) -> AITrace:
    builder = TraceBuilder(
        service=settings.app_name,
        environment=settings.environment,
        release=settings.release,
        workflow_type="rag",
        user_metadata={"user_id": f"user-{rng.randint(10, 99)}"},
        request_metadata={"prompt": "Why did the billing assistant fail for enterprise tenants?"},
        tags={"mode": "demo", "feature": "billing-assistant"},
    )
    with builder.span("rag.request", "request", attributes={"route": "/sample/rag"}) as root:
        _sleep_ms(rng.randint(20, 80))
        with builder.span(
            "rag.retrieve_context",
            "retrieval",
            parent_span_id=root.span_id,
        ) as retrieval:
            _sleep_ms(rng.randint(30, 120))
            docs = rng.choice([0, 2, 4, 8])
            retrieval.attributes.update({"vector_store": "pgvector", "documents_found": docs})
            if docs == 0:
                retrieval.status = "degraded"
        with builder.span("rag.model_call", "model", parent_span_id=root.span_id) as model_span:
            _sleep_ms(rng.randint(90, 200))
            input_tokens = rng.randint(2000, 5000)
            output_tokens = rng.randint(200, 900)
            set_token_usage(model_span, input_tokens, output_tokens)
            input_cost, output_cost = _costs(settings, input_tokens, output_tokens)
            set_cost_usage(model_span, input_cost, output_cost)
            model_span.attributes.update({"model": "gpt-4.1", "retrieval_augmented": True})
        root.end_time = model_span.end_time
    trace = builder.finalize(
        response_metadata={"completion": "Root cause summary", "grounded": True}
    )
    if any(span.status != "ok" for span in trace.spans):
        trace.status = "degraded"
    return trace


def generate_agent_trace(settings: Settings, rng: random.Random) -> AITrace:
    builder = TraceBuilder(
        service=settings.app_name,
        environment=settings.environment,
        release=settings.release,
        workflow_type="agent",
        user_metadata={"user_id": f"agent-user-{rng.randint(100, 999)}"},
        request_metadata={
            "prompt": "Investigate customer refund anomaly and open a ticket if needed."
        },
        tags={"mode": "demo", "feature": "support-agent"},
    )
    with builder.span("agent.request", "request", attributes={"route": "/sample/agent"}) as root:
        _sleep_ms(rng.randint(20, 70))
        with builder.span("agent.plan", "agent_step", parent_span_id=root.span_id) as plan_span:
            _sleep_ms(rng.randint(40, 120))
            plan_span.attributes.update({"planner": "react", "step_count": 3})
        with builder.span("agent.lookup_orders", "tool", parent_span_id=root.span_id) as tool_span:
            _sleep_ms(rng.randint(50, 150))
            tool_span.attributes.update({"tool_name": "orders_api", "endpoint": "/orders/search"})
            if rng.random() < 0.35:
                tool_span.retry_count = 1
                tool_span.events.append(
                    AIEvent(
                        event_type="retry",
                        attributes={"reason": "HTTP 503 from orders_api"},
                    )
                )
        with builder.span("agent.model_reason", "model", parent_span_id=root.span_id) as model_span:
            _sleep_ms(rng.randint(120, 280))
            input_tokens = rng.randint(3000, 7000)
            output_tokens = rng.randint(300, 1200)
            set_token_usage(model_span, input_tokens, output_tokens)
            input_cost, output_cost = _costs(settings, input_tokens, output_tokens)
            set_cost_usage(model_span, input_cost, output_cost)
            model_span.attributes.update({"model": "gpt-4.1", "tool_enabled": True})
            if rng.random() < 0.2:
                builder.record_error(
                    model_span,
                    "Guardrail triggered due to unsafe action proposal",
                    "GuardrailError",
                )
        root.end_time = model_span.end_time
    trace = builder.finalize(
        response_metadata={
            "completion": "Ticket created",
            "ticket_id": f"INC-{rng.randint(1000, 9999)}",
        }
    )
    if any(span.status == "error" for span in trace.spans):
        trace.status = "error"
    elif any(span.status != "ok" for span in trace.spans):
        trace.status = "degraded"
    return trace


def generate_demo_traces(settings: Settings, count: int = 10) -> list[AITrace]:
    rng = random.Random(settings.demo_seed)
    traces: list[AITrace] = []
    generators: list[tuple[str, Any]] = [
        ("chat", lambda: generate_chat_trace(settings, induce_error=rng.random() < 0.15)),
        ("rag", lambda: generate_rag_trace(settings, rng)),
        ("agent", lambda: generate_agent_trace(settings, rng)),
    ]
    for index in range(count):
        _, generator = generators[index % len(generators)]
        traces.append(generator())
    return traces
