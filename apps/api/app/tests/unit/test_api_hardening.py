from fastapi.testclient import TestClient

from app.main import app


def test_api_v1_alias_preserves_health_contract() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_security_headers_are_present_by_default() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "camera=()" in response.headers["permissions-policy"]


def test_request_size_limit_rejects_oversized_body() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/query",
            headers={"content-length": str(80 * 1024 * 1024)},
            content=b"{}",
        )
    assert response.status_code == 413
