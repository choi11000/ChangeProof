from fastapi.testclient import TestClient

from app.api.analyses import get_pull_request_service
from app.clients.github import (
    GitHubApiUnavailable,
    GitHubAuthenticationError,
    GitHubPrivateRepositoryRestricted,
    GitHubPullRequestNotFound,
    GitHubRateLimitError,
    GitHubRepositoryNotFound,
)
from app.main import app
from app.schemas.github import GitHubRepositoryRef, PullRequestAnalysis, PullRequestMetadata
from app.services.pull_request_service import InvalidGitHubRepository


class StubService:
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error

    async def analyze(self, repository: str, pull_request: int):
        if self.error:
            raise self.error
        return self.result


def test_analysis_endpoint_returns_typed_result() -> None:
    result = PullRequestAnalysis(
        repository=GitHubRepositoryRef(owner="acme", repo="risky-saas"),
        pull_request=PullRequestMetadata(
            repository="acme/risky-saas",
            number=42,
            title="Drop legacy status",
            state="open",
            base_branch="main",
            head_branch="feature/drop",
            base_sha="base",
            head_sha="head",
            changed_files=0,
            html_url="https://github.com/acme/risky-saas/pull/42",
        ),
        changed_files=[],
        sql_files=[],
    )
    app.dependency_overrides[get_pull_request_service] = lambda: StubService(result=result)
    try:
        response = TestClient(app).post(
            "/api/v1/analyses/github-pr",
            json={"repository": "acme/risky-saas", "pull_request": 42},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["repository"] == {"owner": "acme", "repo": "risky-saas"}


def test_request_validation_rejects_non_positive_pr_number() -> None:
    response = TestClient(app).post(
        "/api/v1/analyses/github-pr",
        json={"repository": "acme/risky-saas", "pull_request": 0},
    )

    assert response.status_code == 422


def test_domain_errors_are_mapped_to_safe_http_statuses() -> None:
    cases = [
        (InvalidGitHubRepository("invalid repository"), 422),
        (GitHubRepositoryNotFound("repository not found"), 404),
        (GitHubPullRequestNotFound("pull request not found"), 404),
        (GitHubAuthenticationError("authentication failed"), 401),
        (GitHubRateLimitError(), 429),
        (GitHubApiUnavailable("upstream unavailable"), 502),
        (GitHubPrivateRepositoryRestricted(), 403),
    ]
    client = TestClient(app)
    for error, expected_status in cases:
        app.dependency_overrides[get_pull_request_service] = lambda error=error: StubService(
            error=error
        )
        response = client.post(
            "/api/v1/analyses/github-pr",
            json={"repository": "acme/risky-saas", "pull_request": 42},
        )
        assert response.status_code == expected_status
        assert "token" not in response.text.lower()
    app.dependency_overrides.clear()
