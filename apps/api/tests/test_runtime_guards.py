from fastapi.testclient import TestClient
from starlette.requests import Request

from app.api.analyses import get_pull_request_service
from app.core.config import Settings
from app.core.rate_limit import FixedWindowRateLimiter, client_identity, get_rate_limiter
from app.core.sandbox_gate import SandboxBusyError, SandboxExecutionGate
from app.main import app
from app.services.pull_request_service import InvalidGitHubRepository


def test_rate_limiter_accepts_below_limit_rejects_above_and_resets() -> None:
    now = [0.0]
    limiter = FixedWindowRateLimiter(window_seconds=60, max_entries=10, clock=lambda: now[0])
    assert limiter.check("analysis:a", 2) is None
    assert limiter.check("analysis:a", 2) is None
    assert limiter.check("analysis:a", 2) == 60
    assert limiter.check("analysis:b", 2) is None
    now[0] = 61
    assert limiter.check("analysis:a", 2) is None


def test_rate_limit_store_is_bounded() -> None:
    limiter = FixedWindowRateLimiter(max_entries=2)
    for client in ("a", "b", "c"):
        limiter.check(client, 1)
    assert limiter.entry_count == 2


def test_endpoint_rate_limit_returns_429_and_retry_after(monkeypatch) -> None:
    class InvalidService:
        async def analyze(self, *_args):
            raise InvalidGitHubRepository("invalid")

    monkeypatch.setattr("app.core.rate_limit.get_settings", lambda: Settings(analysis_rate_limit=1))
    get_rate_limiter.cache_clear()
    app.dependency_overrides[get_pull_request_service] = InvalidService
    client = TestClient(app)
    try:
        first = client.post(
            "/api/v1/analyses/github-pr",
            json={"repository": "acme/public", "pull_request": 1},
        )
        second = client.post(
            "/api/v1/analyses/github-pr",
            json={"repository": "acme/public", "pull_request": 1},
        )
    finally:
        app.dependency_overrides.clear()
        get_rate_limiter.cache_clear()
    assert first.status_code == 422
    assert second.status_code == 429
    assert int(second.headers["Retry-After"]) >= 1


def _request(headers: list[tuple[bytes, bytes]]) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/",
            "headers": headers,
            "client": ("198.51.100.10", 1234),
        }
    )


def test_proxy_header_is_only_used_when_explicitly_trusted(monkeypatch) -> None:
    request = _request([(b"x-forwarded-for", b"203.0.113.4, 10.0.0.1")])
    monkeypatch.setattr(
        "app.core.rate_limit.get_settings", lambda: Settings(trust_proxy_headers=False)
    )
    assert client_identity(request) == "198.51.100.10"
    monkeypatch.setattr(
        "app.core.rate_limit.get_settings", lambda: Settings(trust_proxy_headers=True)
    )
    assert client_identity(request) == "203.0.113.4"


def test_sandbox_gate_busy_and_releases_after_success_and_exception() -> None:
    gate = SandboxExecutionGate(1)
    with gate.slot():
        try:
            with gate.slot():
                raise AssertionError("unreachable")
        except SandboxBusyError:
            pass
    with gate.slot():
        pass
    try:
        with gate.slot():
            raise RuntimeError("failure")
    except RuntimeError:
        pass
    with gate.slot():
        pass
