FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY dashboards /app/dashboards
COPY alerts /app/alerts
COPY incident_workflows /app/incident_workflows

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "ai_observability.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
