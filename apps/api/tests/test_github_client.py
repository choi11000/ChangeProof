import asyncio
import base64
from collections.abc import Callable, Coroutine
from typing import Any

import httpx
import pytest

from app.clients.github import (
    GitHubApiUnavailable,
    GitHubAuthenticationError,
    GitHubClient,
    GitHubFileContentUnavailable,
    GitHubPullRequestNotFound,
    GitHubRateLimitError,
    GitHubRepositoryNotFound,
    build_github_http_client,
)
from app.schemas.github import ChangedFileStatus, GitHubRepositoryRef

repository = GitHubRepositoryRef(owner="acme", repo="risky-saas")


def run(coroutine: Coroutine[Any, Any, Any]) -> Any:
    return asyncio.run(coroutine)


def response_handler(
    handler: Callable[[httpx.Request], httpx.Response],
) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url="https://api.github.test",
        transport=httpx.MockTransport(handler),
    )


def test_fetch_pull_request_metadata() -> None:
    async def scenario() -> None:
        client = response_handler(
            lambda request: httpx.Response(
                200,
                json={
                    "number": 42,
                    "title": "Drop legacy status",
                    "body": "Cleanup",
                    "state": "open",
                    "base": {"ref": "main", "sha": "base-sha"},
                    "head": {"ref": "feature/drop", "sha": "head-sha"},
                    "user": {"login": "octocat"},
                    "changed_files": 2,
                    "html_url": "https://github.com/acme/risky-saas/pull/42",
                },
            )
        )
        async with client:
            result = await GitHubClient(client).fetch_pull_request(repository, 42)
        assert result.repository == "acme/risky-saas"
        assert result.base_sha == "base-sha"
        assert result.author == "octocat"

    run(scenario())


def test_fetch_changed_files_preserves_patch_and_rename() -> None:
    async def scenario() -> None:
        client = response_handler(
            lambda request: httpx.Response(
                200,
                json=[
                    {
                        "filename": "migrations/001.sql",
                        "previous_filename": "db/001.sql",
                        "status": "renamed",
                        "additions": 2,
                        "deletions": 1,
                        "changes": 3,
                        "patch": "@@ -1 +1 @@",
                    }
                ],
            )
        )
        async with client:
            result = await GitHubClient(client).fetch_changed_files(repository, 42)
        assert result[0].status is ChangedFileStatus.RENAMED
        assert result[0].previous_path == "db/001.sql"
        assert result[0].patch == "@@ -1 +1 @@"

    run(scenario())


def test_fetch_file_content_decodes_head_revision() -> None:
    requested_ref = None

    async def scenario() -> None:
        nonlocal requested_ref

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal requested_ref
            requested_ref = request.url.params["ref"]
            content = base64.b64encode(b"DROP TABLE payments;").decode()
            return httpx.Response(
                200,
                json={
                    "path": "migrations/001.sql",
                    "sha": "abc",
                    "size": 20,
                    "encoding": "base64",
                    "content": content,
                },
            )

        client = response_handler(handler)
        async with client:
            result = await GitHubClient(client).fetch_file_content(
                repository, "migrations/001.sql", "head-sha"
            )
        assert result.content == "DROP TABLE payments;"
        assert result.sha == "abc"

    run(scenario())
    assert requested_ref == "head-sha"


def test_large_file_is_not_decoded() -> None:
    async def scenario() -> None:
        client = response_handler(
            lambda request: httpx.Response(200, json={"sha": "large", "size": 101})
        )
        async with client:
            result = await GitHubClient(client).fetch_file_content(
                repository, "migrations/large.sql", "head", max_bytes=100
            )
        assert result.too_large is True
        assert result.content is None

    run(scenario())


@pytest.mark.parametrize(
    ("status_code", "headers", "error_type"),
    [
        (401, {}, GitHubAuthenticationError),
        (403, {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "123"}, GitHubRateLimitError),
        (403, {}, GitHubAuthenticationError),
        (429, {}, GitHubRateLimitError),
        (503, {}, GitHubApiUnavailable),
        (422, {}, GitHubApiUnavailable),
    ],
)
def test_maps_github_http_errors(status_code, headers, error_type) -> None:
    async def scenario() -> None:
        client = response_handler(lambda request: httpx.Response(status_code, headers=headers))
        async with client:
            with pytest.raises(error_type):
                await GitHubClient(client).verify_repository(repository)

    run(scenario())


def test_distinguishes_repository_pr_and_file_not_found() -> None:
    async def scenario() -> None:
        client = response_handler(lambda request: httpx.Response(404))
        github = GitHubClient(client)
        async with client:
            with pytest.raises(GitHubRepositoryNotFound):
                await github.verify_repository(repository)
            with pytest.raises(GitHubPullRequestNotFound):
                await github.fetch_pull_request(repository, 42)
            with pytest.raises(GitHubFileContentUnavailable):
                await github.fetch_file_content(repository, "missing.sql", "head")

    run(scenario())


def test_timeout_is_mapped_without_exposing_request_details() -> None:
    async def scenario() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("secret upstream detail", request=request)

        client = response_handler(handler)
        async with client:
            with pytest.raises(GitHubApiUnavailable, match="GitHub API is unavailable"):
                await GitHubClient(client).verify_repository(repository)

    run(scenario())


def test_build_client_adds_token_only_to_request_headers() -> None:
    client = build_github_http_client("test-token")

    assert client.headers["Authorization"] == "Bearer test-token"
    assert client.follow_redirects is True
    assert "test-token" not in repr(GitHubClient(client))
    run(client.aclose())
