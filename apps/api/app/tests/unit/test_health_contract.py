from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_returns_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_endpoint_returns_demo_state() -> None:
    with TestClient(app) as client:
        response = client.get("/health/readiness")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ready", "needs_documents"}
    assert body["database"] == "ok"
    assert isinstance(body["documents"], int)
    assert isinstance(body["indexed_documents"], int)
    assert isinstance(body["active_chunks"], int)
    assert isinstance(body["vector_store_available"], bool)
    assert isinstance(body["ollama_available"], bool)
    assert body["local_first"] is True
    assert body["local_backend"] is True
    assert body["cloud_api_required"] is False
    assert body["external_provider_enabled"] is False
    assert body["primary_inference"] == "local_offline"
    assert body["runtime_profile"] in {"balanced", "low_memory", "cpu_offline"}
    assert isinstance(body["low_memory_mode"], bool)
    if body["runtime_profile"] in {"low_memory", "cpu_offline"}:
        assert body["low_memory_mode"] is True
    assert body["ollama_runtime"]["keep_alive"]
    assert body["ollama_runtime"]["num_ctx"] <= 4096
    assert body["ollama_runtime"]["num_predict"] <= 1024
    assert body["ollama_runtime"]["embedding_batch_size"] >= 1
