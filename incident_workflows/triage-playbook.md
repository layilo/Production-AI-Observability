# AI Incident Triage Playbook

## Trigger Conditions
- Alert fires for latency, error rate, cost spike, or incident backlog.
- Customer reports incorrect, unsafe, empty, or delayed AI responses.
- Release verification detects regression traces or evaluation failures.

## Triage Steps
1. Pull the latest impacted traces from `/v1/traces?status=error` or `/v1/traces?status=degraded`.
2. Open `/v1/incidents/triage/{trace_id}` for the highest-severity trace.
3. Confirm the first failing span and classify it as prompt, retrieval, tool, model, guardrail, or downstream dependency.
4. Compare the trace against the previous release and environment to isolate rollout-specific changes.
5. Export the trace and attach it to the incident ticket and regression dataset.
6. Decide mitigation: rollback, prompt hotfix, tool disablement, fallback model, traffic shaping, or sampling increase.

## Evidence Checklist
- Trace tree with timing and span status
- Prompt and retrieval metadata after redaction
- Model/token/cost summary
- Retry/fallback behavior
- Release, environment, and feature tags
- Related alerts and dashboard screenshots

## Postmortem Follow-Through
- Add the incident trace to the regression suite.
- Encode new alert thresholds if detection lag was too high.
- Update runbooks for the affected failure mode.
