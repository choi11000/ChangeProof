import asyncio
import base64
from typing import Any

import httpx
import pytest

from app.analyzers.sql_migration import SqlMigrationParser
from app.clients.github import GitHubClient
from app.schemas.github import AnalysisWarningCode, ContentSource, FileCategory
from app.schemas.sql_change import SqlOperation
from app.services.pull_request_service import (
    InvalidGitHubRepository,
    PullRequestService,
    parse_repository_reference,
)


@pytest.mark.parametrize(
    "value",
    [
        "https://github.com/owner/repository",
        "https://github.com/owner/repository.git",
        "owner/repository",
    ],
)
def test_normalizes_repository_reference(value: str) -> None:
    result = parse_repository_reference(value)

    assert result.owner == "owner"
    assert result.repo == "repository"


@pytest.mark.parametrize(
    "value",
    [
        "https://gitlab.com/foo/bar",
        "http://github.com/foo/bar",
        "github.com",
        "foo",
        "https://github.com/",
        "https://github.com/foo/bar/extra",
        "https://github.com/foo/bar?token=secret",
    ],
)
def test_rejects_invalid_repository_reference(value: str) -> None:
    with pytest.raises(InvalidGitHubRepository):
        parse_repository_reference(value)


def test_mocked_pr_pipeline_classifies_and_parses_full_sql_content() -> None:
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        path = request.url.path
        if path == "/repos/acme/risky-saas":
            return httpx.Response(200, json={"full_name": "acme/risky-saas"})
        if path == "/repos/acme/risky-saas/pulls/42":
            return httpx.Response(200, json=_pull_request())
        if path == "/repos/acme/risky-saas/pulls/42/files":
            return httpx.Response(200, json=_changed_files())
        if path.endswith("/contents/migrations/005_drop_legacy_status.sql"):
            sql = "ALTER TABLE orders DROP COLUMN legacy_status;"
            return httpx.Response(200, json=_content(sql, "sql-sha"))
        raise AssertionError(f"Unexpected request: {request.url}")

    async def scenario():
        http_client = httpx.AsyncClient(
            base_url="https://api.github.test", transport=httpx.MockTransport(handler)
        )
        async with http_client:
            service = PullRequestService(GitHubClient(http_client), SqlMigrationParser())
            return await service.analyze("https://github.com/acme/risky-saas", 42)

    result = asyncio.run(scenario())

    assert result.pull_request.title == "Drop legacy order status"
    assert [item.category for item in result.changed_files] == [
        FileCategory.SQL_MIGRATION,
        FileCategory.APPLICATION,
    ]
    assert result.sql_files[0].content_source is ContentSource.HEAD
    change = result.sql_files[0].analysis.changes[0]
    assert change.operation is SqlOperation.DROP_COLUMN
    assert (change.table, change.column) == ("orders", "legacy_status")
    assert any("ref=head-sha" in request for request in requests)


def test_sql_file_failures_are_isolated() -> None:
    files = [
        _file("migrations/good.sql"),
        _file("migrations/bad.sql"),
        _file("migrations/large.sql"),
        _file("migrations/missing.sql"),
        _file("migrations/removed.sql", status="removed"),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/repos/acme/risky-saas":
            return httpx.Response(200, json={})
        if path.endswith("/pulls/42"):
            return httpx.Response(200, json={**_pull_request(), "changed_files": len(files)})
        if path.endswith("/pulls/42/files"):
            return httpx.Response(200, json=files)
        if path.endswith("/contents/migrations/good.sql"):
            return httpx.Response(200, json=_content("CREATE TABLE ok (id BIGINT);", "good"))
        if path.endswith("/contents/migrations/bad.sql"):
            return httpx.Response(200, json=_content("ALTER TABLE broken ALTER COLUMN;", "bad"))
        if path.endswith("/contents/migrations/large.sql"):
            return httpx.Response(200, json={"size": 2_000_000, "sha": "large"})
        if path.endswith("/contents/migrations/missing.sql"):
            return httpx.Response(404)
        if path.endswith("/contents/migrations/removed.sql"):
            assert request.url.params["ref"] == "base-sha"
            return httpx.Response(200, json=_content("DROP TABLE old;", "removed"))
        raise AssertionError(path)

    async def scenario():
        http_client = httpx.AsyncClient(
            base_url="https://api.github.test", transport=httpx.MockTransport(handler)
        )
        async with http_client:
            return await PullRequestService(
                GitHubClient(http_client), SqlMigrationParser()
            ).analyze("acme/risky-saas", 42)

    result = asyncio.run(scenario())

    assert len(result.sql_files) == 5
    assert result.sql_files[0].analysis is not None
    assert result.sql_files[1].error.startswith("Invalid PostgreSQL migration")
    assert result.sql_files[2].error == "SQL migration exceeds the 1 MiB analysis limit"
    assert result.sql_files[3].error == "GitHub file content is unavailable"
    assert result.sql_files[4].content_source is ContentSource.BASE
    assert result.sql_files[4].analysis is None
    assert {warning.code for warning in result.warnings} >= {
        AnalysisWarningCode.SQL_PARSE_ERROR,
        AnalysisWarningCode.SKIPPED_TOO_LARGE,
        AnalysisWarningCode.FILE_CONTENT_UNAVAILABLE,
        AnalysisWarningCode.REMOVED_SQL_NOT_ANALYZED,
        AnalysisWarningCode.PATCH_UNAVAILABLE,
    }


def _pull_request() -> dict[str, Any]:
    return {
        "number": 42,
        "title": "Drop legacy order status",
        "body": None,
        "state": "open",
        "base": {"ref": "main", "sha": "base-sha"},
        "head": {"ref": "feature/drop", "sha": "head-sha"},
        "user": {"login": "developer"},
        "changed_files": 2,
        "html_url": "https://github.com/acme/risky-saas/pull/42",
    }


def _changed_files() -> list[dict[str, Any]]:
    return [
        _file("migrations/005_drop_legacy_status.sql", patch="@@ -0,0 +1 @@"),
        _file("app/order_service.py", patch="@@ -1 +1 @@"),
    ]


def _file(path: str, status: str = "modified", patch: str | None = None) -> dict[str, Any]:
    return {
        "filename": path,
        "status": status,
        "additions": 1,
        "deletions": 1,
        "changes": 2,
        "patch": patch,
    }


def _content(sql: str, sha: str) -> dict[str, Any]:
    return {
        "sha": sha,
        "size": len(sql.encode()),
        "encoding": "base64",
        "content": base64.b64encode(sql.encode()).decode(),
    }
