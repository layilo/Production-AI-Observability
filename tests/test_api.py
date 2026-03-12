from fastapi.testclient import TestClient

from ai_observability.api.main import app, get_ingestion_service, get_store
from ai_observability.core.config import Settings
from ai_observability.ingestion.service import TraceIngestionService
from ai_observability.storage.sqlite_store import SQLiteStore


def build_client(tmp_path) -> TestClient:
    settings = Settings(
        AI_OBS_DB_PATH=str(tmp_path / "api.db"),
        AI_OBS_ENVIRONMENT="test",
        AI_OBS_APP_NAME="api-test-service",
        AI_OBS_RELEASE="test",
    )
    store = SQLiteStore(f"sqlite:///{settings.db_file}")
    service = TraceIngestionService(settings, store)

    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_ingestion_service] = lambda: service
    return TestClient(app)


def test_demo_generate_and_query(tmp_path) -> None:
    client = build_client(tmp_path)

    generate = client.post("/v1/demo/generate?count=5")
    assert generate.status_code == 200
    assert generate.json()["ingested"] == 5

    listed = client.get("/v1/traces?limit=10")
    assert listed.status_code == 200
    payload = listed.json()
    assert payload["total"] == 5
    assert len(payload["items"]) == 5

