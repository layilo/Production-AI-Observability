from __future__ import annotations

from pathlib import Path

from jinja2 import Template

from ai_observability.core.models import AITrace, IncidentReport

TEMPLATE = Template(
    """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>AI Incident Report {{ report.trace_id }}</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 2rem; color: #1f2937; }
    h1, h2 { color: #111827; }
    .badge {
      display: inline-block;
      padding: 0.2rem 0.6rem;
      border-radius: 999px;
      background: #e5e7eb;
    }
    .critical { background: #fee2e2; color: #991b1b; }
    .high { background: #ffedd5; color: #9a3412; }
    .medium { background: #fef3c7; color: #92400e; }
    .low { background: #dcfce7; color: #166534; }
    pre { background: #f3f4f6; padding: 1rem; overflow: auto; }
  </style>
</head>
<body>
  <h1>AI Incident Report</h1>
  <p><span class="badge">{{ report.overall_status }}</span></p>
  <p>{{ report.headline }}</p>
  <h2>Trace Summary</h2>
  <pre>{{ trace.summary.model_dump_json(indent=2) }}</pre>
  <h2>Findings</h2>
  {% for finding in report.findings %}
  <h3>
    <span class="badge {{ finding.severity }}">{{ finding.severity }}</span>
    {{ finding.category }}
  </h3>
  <p>{{ finding.summary }}</p>
  <pre>{{ finding.evidence }}</pre>
  {% endfor %}
  <h2>Recommended Actions</h2>
  <ul>
    {% for action in report.recommended_actions %}
    <li>{{ action }}</li>
    {% endfor %}
  </ul>
</body>
</html>"""
)


def render_incident_report(trace: AITrace, report: IncidentReport, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(TEMPLATE.render(trace=trace, report=report), encoding="utf-8")
    return output_path
