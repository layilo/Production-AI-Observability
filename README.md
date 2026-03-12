# Production AI Observability Platform

Production-grade AI observability, trace-driven debugging, incident triage, and regression dataset capture for AI-powered features. The repository runs in two modes:

- Demo mode: synthetic chat, RAG, and agent traces with realistic latency, token, cost, retry, and failure behavior.
- Real mode: OpenTelemetry-aligned instrumentation with OTLP HTTP export to Jaeger, collectors, or compatible backends.

## What It Provides
- End-to-end AI trace ingestion for prompts, model calls, retrieval, tools, guardrails, and downstream logic
- Privacy-aware redaction and configurable deterministic sampling
- Derived summaries for latency, token usage, cost, failure stage, and workflow composition
- Incident triage reports for production failures and degradations
- Prometheus metrics and example alert rules
- Example Grafana dashboard definition
- Docker, Compose, CI, and tests

## Repository Layout
- `src/ai_observability/api`: FastAPI service for ingestion, querying, metrics, export, and report rendering
- `src/ai_observability/instrumentation`: Trace builder helpers and OpenTelemetry setup
- `src/ai_observability/ingestion`: Redaction, sampling, summary derivation, persistence, and metrics updates
- `src/ai_observability/reporting`: Incident triage and HTML incident report rendering
- `src/ai_observability/sample_app`: Synthetic AI workflows for chat, RAG, and agentic execution
- `dashboards`: Example dashboard definition
- `alerts`: Prometheus scrape config and alert rules
- `incident_workflows`: Operational playbook for triage

## Architecture
1. Applications emit AI workflow traces using either:
   - the local `TraceBuilder` helpers for custom instrumentation, or
   - standard OpenTelemetry spans exported to an OTLP-compatible backend.
2. The API ingests normalized `AITrace` payloads through `POST /v1/traces`.
3. The ingestion service applies deterministic sampling, privacy redaction, summary derivation, incident scoring, and persistence.
4. Prometheus metrics expose service health and SRE-facing indicators.
5. Engineers query traces, triage incidents, export regression datasets, and render HTML reports.

## Quick Start

### 1. Local setup
```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e .[dev]
copy .env.example .env
```

### 2. Run the API
```bash
uvicorn ai_observability.api.main:app --reload
```

Health check:
```bash
curl http://localhost:8000/health
```

### 3. Generate demo data
```bash
python -m ai_observability.sample_app.demo --count 25
```

Or via API:
```bash
curl -X POST "http://localhost:8000/v1/demo/generate?count=25"
```

### 4. Inspect traces
```bash
curl http://localhost:8000/v1/traces?limit=5
curl http://localhost:8000/v1/metrics/summary
```

### 5. Render an incident report
1. Get an error trace ID from `/v1/traces?status=error`
2. Open `http://localhost:8000/v1/reports/incident/{trace_id}`

## Demo Mode
Demo mode produces synthetic workflows for:
- Chat summarization
- Retrieval-augmented generation
- Agent planning and tool use

These traces include:
- request, prompt, model, retrieval, tool, and agent-step spans
- token and cost accounting
- retries, degradations, and errors
- release and feature tagging for incident comparison

## Real Mode
Set:
```bash
AI_OBS_OTLP_ENABLED=true
AI_OBS_OTLP_ENDPOINT=http://localhost:4318/v1/traces
```

Then instrument your app:
```python
from opentelemetry import trace
from ai_observability.instrumentation.opentelemetry import configure_otel

configure_otel(
    service_name="my-ai-service",
    environment="prod",
    endpoint="http://localhost:4318/v1/traces",
    headers="",
)
tracer = trace.get_tracer("my-ai-service")
```

Use span attributes consistently:
- `ai.workflow_type`
- `ai.model`
- `ai.prompt_template`
- `ai.retrieval.documents_found`
- `ai.tool.name`
- `ai.token.input`
- `ai.token.output`
- `ai.cost.total`

See [examples/real_mode_client.py](/c:/Users/Aaron.Lam/Private/Repo/ai observe/Production-AI-Observability/examples/real_mode_client.py).

## API Endpoints
- `GET /health`
- `GET /metrics`
- `POST /v1/traces`
- `GET /v1/traces`
- `GET /v1/traces/{trace_id}`
- `GET /v1/metrics/summary`
- `GET /v1/incidents/triage/{trace_id}`
- `GET /v1/reports/incident/{trace_id}`
- `GET /v1/export/traces`
- `POST /v1/demo/generate`
- `POST /v1/sample/chat`
- `POST /v1/sample/rag`
- `POST /v1/sample/agent`

## Privacy and Sampling
- Redaction is controlled by `AI_OBS_REDACTION_ENABLED` and `AI_OBS_REDACTION_FIELDS`
- Sampling is deterministic by trace ID via `AI_OBS_SAMPLING_RATE`
- Sensitive request, response, and span attributes are replaced with `[REDACTED]`

## Docker and Local Observability Stack
```bash
docker compose up --build
```

Services:
- API: `http://localhost:8000`
- Jaeger: `http://localhost:16686`
- Prometheus: `http://localhost:9090`

## Incident Workflow
Use [incident_workflows/triage-playbook.md](/c:/Users/Aaron.Lam/Private/Repo/ai observe/Production-AI-Observability/incident_workflows/triage-playbook.md) during production failures.

Typical flow:
1. Alert fires for error rate, latency, or cost.
2. Query recent degraded traces.
3. Open incident triage report for the most representative trace.
4. Export traces to seed regression datasets and postmortems.

## Testing
```bash
ruff check .
pytest
```

## Future Extensions
- Add batch ingestion and Kafka sinks
- Attach offline evaluations to trace cohorts
- Correlate deployment events and feature flags
- Push incidents into PagerDuty, Jira, or Slack
