from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_runtime_status() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "ChangeProof API",
        "environment": "development",
    }


def test_root_points_to_api_documentation() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"service": "ChangeProof API", "docs": "/docs"}
