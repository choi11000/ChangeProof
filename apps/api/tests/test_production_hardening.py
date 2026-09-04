import logging

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.analyses import get_pull_request_service
from app.api.health import get_readiness_checker
from app.core.config import Settings
from app.main import app


class RaisingAnalysisService:
    async def analyze(self, *_args):
        raise RuntimeError(
            "postgresql://admin:super-secret@internal-db.example/private database exploded"
        )


class Readiness:
    def __init__(self, ready: bool) -> None:
        self.ready = ready

    def sandbox_ready(self) -> bool:
        return self.ready


def test_unexpected_errors_are_sanitized_and_correlated(caplog) -> None:
    app.dependency_overrides[get_pull_request_service] = RaisingAnalysisService
    try:
        with caplog.at_level(logging.ERROR):
            response = TestClient(app, raise_server_exceptions=False).post(
                "/api/v1/analyses/github-pr",
                json={"repository": "acme/public", "pull_request": 1},
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 500
    assert response.headers["X-Request-ID"] in response.json()["detail"]
    assert "super-secret" not in response.text
    assert "internal-db" not in response.text
    assert any(
        response.headers["X-Request-ID"] == getattr(record, "request_id", None)
        for record in caplog.records
    )
    assert "super-secret" not in caplog.text


def test_cors_allows_configured_origin_and_rejects_unknown() -> None:
    client = TestClient(app)
    allowed = client.options(
        "/api/v1/health",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )
    rejected = client.options(
        "/api/v1/health",
        headers={"Origin": "https://unknown.example", "Access-Control-Request-Method": "GET"},
    )
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "access-control-allow-origin" not in rejected.headers


def test_production_configuration_validation() -> None:
    with pytest.raises(ValidationError, match="CORS_ALLOWED_ORIGINS"):
        Settings(app_env="production", cors_allowed_origins="")
    with pytest.raises(ValidationError, match="public-repository-only"):
        Settings(app_env="production", github_public_repositories_only=False)
    with pytest.raises(ValidationError, match="wildcard"):
        Settings(cors_allowed_origins="*")
    assert Settings(app_env="development", github_public_repositories_only=False)


def test_liveness_and_readiness_contract() -> None:
    client = TestClient(app)
    assert client.get("/api/v1/health/live").json() == {"status": "ok"}
    app.dependency_overrides[get_readiness_checker] = lambda: Readiness(True)
    try:
        ready = client.get("/api/v1/health/ready")
    finally:
        app.dependency_overrides.clear()
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready", "sandbox": "ready"}

    app.dependency_overrides[get_readiness_checker] = lambda: Readiness(False)
    try:
        unavailable = client.get("/api/v1/health/ready")
    finally:
        app.dependency_overrides.clear()
    assert unavailable.status_code == 503
    assert unavailable.json() == {"status": "not_ready", "sandbox": "unavailable"}
