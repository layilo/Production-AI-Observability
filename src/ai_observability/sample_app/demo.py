from __future__ import annotations

import argparse

from ai_observability.core.config import get_settings
from ai_observability.ingestion.service import TraceIngestionService
from ai_observability.sample_app.workflows import generate_demo_traces
from ai_observability.storage.sqlite_store import SQLiteStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic AI observability traces.")
    parser.add_argument("--count", type=int, default=10, help="Number of traces to generate.")
    args = parser.parse_args()

    settings = get_settings()
    store = SQLiteStore(f"sqlite:///{settings.db_file}")
    service = TraceIngestionService(settings, store)
    for trace in generate_demo_traces(settings, count=args.count):
        service.ingest(trace)
    print(f"Generated and ingested {args.count} demo traces into {settings.db_file}")


if __name__ == "__main__":
    main()

