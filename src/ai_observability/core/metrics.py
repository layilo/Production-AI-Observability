from prometheus_client import Counter, Gauge, Histogram

TRACE_INGESTED_TOTAL = Counter(
    "ai_observability_traces_ingested_total",
    "Total ingested AI traces",
    ["service", "environment", "status", "workflow_type"],
)
TRACE_DURATION_MS = Histogram(
    "ai_observability_trace_duration_ms",
    "Trace duration in milliseconds",
    ["service", "environment", "workflow_type"],
    buckets=(50, 100, 250, 500, 1000, 3000, 5000, 10000, 30000),
)
TRACE_TOKENS_TOTAL = Counter(
    "ai_observability_tokens_total",
    "Total AI tokens processed",
    ["service", "environment", "workflow_type"],
)
TRACE_COST_TOTAL = Counter(
    "ai_observability_cost_total",
    "Total estimated AI cost",
    ["service", "environment", "workflow_type"],
)
ACTIVE_INCIDENTS = Gauge(
    "ai_observability_active_incidents",
    "Current count of traces with error or degraded state",
    ["service", "environment"],
)
