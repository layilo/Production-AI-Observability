from ai_observability.core.config import Settings
from ai_observability.ingestion.service import TraceIngestionService
from ai_observability.sample_app.workflows import generate_chat_trace
from ai_observability.storage.sqlite_store import SQLiteStore


def test_ingestion_builds_summary_and_persists(tmp_path) -> None:
    settings = Settings(
        AI_OBS_DB_PATH=str(tmp_path / "test.db"),
        AI_OBS_ENVIRONMENT="test",
        AI_OBS_APP_NAME="test-service",
        AI_OBS_RELEASE="test",
    )
    store = SQLiteStore(f"sqlite:///{settings.db_file}")
    service = TraceIngestionService(settings, store)

    trace = generate_chat_trace(settings, induce_error=True)
    ingested = service.ingest(trace)

    assert ingested is not None
    assert ingested.summary.span_count >= 2
    assert ingested.summary.error_count >= 1
    persisted = store.get_trace(ingested.trace_id)
    assert persisted is not None
    assert persisted.status == "error"

