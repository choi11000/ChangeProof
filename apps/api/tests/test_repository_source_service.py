import asyncio
import base64
from typing import Any

import httpx

from app.clients.github import GitHubClient
from app.schemas.dependency import SourceScope
from app.schemas.github import AnalysisWarningCode, GitHubRepositoryRef
from app.services.repository_source_service import RepositorySourceService


def _tree_response(entries: list[dict[str, Any]], truncated: bool = False) -> dict[str, Any]:
    return {"sha": "head-sha", "tree": entries, "truncated": truncated}


def _file_content(content: str, sha: str = "file-sha") -> dict[str, Any]:
    return {
        "sha": sha,
        "size": len(content.encode("utf-8")),
        "encoding": "base64",
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
    }


def test_collects_application_and_test_sources_at_head_sha() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        path = request.url.path
        if "git/trees/head-sha" in path:
            return httpx.Response(
                200,
                json=_tree_response(
                    [
                        {"path": "app/order_service.py", "type": "blob", "sha": "s1"},
                        {"path": "tests/test_order.py", "type": "blob", "sha": "s2"},
                        {"path": "README.md", "type": "blob", "sha": "s3"},
                        {"path": ".env", "type": "blob", "sha": "s4"},
                        {"path": "package-lock.json", "type": "blob", "sha": "s5"},
                    ]
                ),
            )
        if "contents/app/order_service.py" in path:
            return httpx.Response(200, json=_file_content("return order.legacy_status"))
        if "contents/tests/test_order.py" in path:
            return httpx.Response(200, json=_file_content("assert order.legacy_status"))
        raise AssertionError(f"Unexpected path: {path}")

    async def run():
        http_client = httpx.AsyncClient(
            base_url="https://api.github.test", transport=httpx.MockTransport(handler)
        )
        async with http_client:
            service = RepositorySourceService(GitHubClient(http_client))
            return await service.collect(
                GitHubRepositoryRef(owner="acme", repo="repo"),
                "head-sha",
                {"migrations/001.sql"},
            )

    tree, snapshot = asyncio.run(run())

    assert len(snapshot.documents) == 2
    paths = {doc.path for doc in snapshot.documents}
    assert paths == {"app/order_service.py", "tests/test_order.py"}

    app_doc = next(d for d in snapshot.documents if d.path == "app/order_service.py")
    assert app_doc.scope is SourceScope.APPLICATION
    assert app_doc.changed_in_pull_request is False

    test_doc = next(d for d in snapshot.documents if d.path == "tests/test_order.py")
    assert test_doc.scope is SourceScope.TEST
    assert snapshot.scan_complete is True


def test_tree_truncated_records_warning() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "git/trees/head-sha" in path:
            return httpx.Response(
                200,
                json=_tree_response(
                    [{"path": "app/service.py", "type": "blob", "sha": "s1"}],
                    truncated=True,
                ),
            )
        if "contents/app/service.py" in path:
            return httpx.Response(200, json=_file_content("code"))
        raise AssertionError(path)

    async def run():
        http_client = httpx.AsyncClient(
            base_url="https://api.github.test", transport=httpx.MockTransport(handler)
        )
        async with http_client:
            service = RepositorySourceService(GitHubClient(http_client))
            return await service.collect(
                GitHubRepositoryRef(owner="acme", repo="repo"), "head-sha", set()
            )

    _, snapshot = asyncio.run(run())

    assert snapshot.scan_complete is False
    assert any(w.code is AnalysisWarningCode.REPOSITORY_TREE_TRUNCATED for w in snapshot.warnings)
    assert any(w.code is AnalysisWarningCode.DEPENDENCY_SCAN_INCOMPLETE for w in snapshot.warnings)


def test_file_count_limit_is_enforced() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "git/trees/head-sha" in path:
            entries = [
                {"path": f"app/file_{i}.py", "type": "blob", "sha": f"s{i}"} for i in range(10)
            ]
            return httpx.Response(200, json=_tree_response(entries))
        return httpx.Response(200, json=_file_content("code"))

    async def run():
        http_client = httpx.AsyncClient(
            base_url="https://api.github.test", transport=httpx.MockTransport(handler)
        )
        async with http_client:
            service = RepositorySourceService(GitHubClient(http_client), max_source_files=3)
            return await service.collect(
                GitHubRepositoryRef(owner="acme", repo="repo"), "head-sha", set()
            )

    _, snapshot = asyncio.run(run())

    assert len(snapshot.documents) == 3
    assert snapshot.scan_complete is False
    assert any(w.code is AnalysisWarningCode.SOURCE_SCAN_LIMIT_REACHED for w in snapshot.warnings)


def test_total_bytes_limit_is_enforced() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "git/trees/head-sha" in path:
            entries = [
                {"path": f"app/file_{i}.py", "type": "blob", "sha": f"s{i}"} for i in range(5)
            ]
            return httpx.Response(200, json=_tree_response(entries))
        # 100 bytes each
        return httpx.Response(200, json=_file_content("x" * 100))

    async def run():
        http_client = httpx.AsyncClient(
            base_url="https://api.github.test", transport=httpx.MockTransport(handler)
        )
        async with http_client:
            service = RepositorySourceService(
                GitHubClient(http_client),
                max_total_source_bytes=250,
            )
            return await service.collect(
                GitHubRepositoryRef(owner="acme", repo="repo"), "head-sha", set()
            )

    _, snapshot = asyncio.run(run())

    # 2 files * 100 = 200 bytes fits in 250, 3rd exceeds
    assert len(snapshot.documents) == 2
    assert snapshot.scan_complete is False
    assert any(w.code is AnalysisWarningCode.SOURCE_SCAN_LIMIT_REACHED for w in snapshot.warnings)


def test_partial_file_failure_is_isolated() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "git/trees/head-sha" in path:
            return httpx.Response(
                200,
                json=_tree_response(
                    [
                        {"path": "app/ok.py", "type": "blob", "sha": "s1"},
                        {"path": "app/bad.py", "type": "blob", "sha": "s2"},
                    ]
                ),
            )
        if "contents/app/ok.py" in path:
            return httpx.Response(200, json=_file_content("ok"))
        if "contents/app/bad.py" in path:
            return httpx.Response(404)
        raise AssertionError(path)

    async def run():
        http_client = httpx.AsyncClient(
            base_url="https://api.github.test", transport=httpx.MockTransport(handler)
        )
        async with http_client:
            service = RepositorySourceService(GitHubClient(http_client))
            return await service.collect(
                GitHubRepositoryRef(owner="acme", repo="repo"), "head-sha", set()
            )

    _, snapshot = asyncio.run(run())

    assert len(snapshot.documents) == 1
    assert snapshot.documents[0].path == "app/ok.py"
    assert any(w.code is AnalysisWarningCode.SOURCE_CONTENT_UNAVAILABLE for w in snapshot.warnings)


def test_source_file_too_large() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "git/trees/head-sha" in path:
            return httpx.Response(
                200,
                json=_tree_response(
                    [{"path": "app/huge.py", "type": "blob", "sha": "s1"}],
                ),
            )
        if "contents/app/huge.py" in path:
            return httpx.Response(200, json={"size": 500_000, "sha": "s1"})
        raise AssertionError(path)

    async def run():
        http_client = httpx.AsyncClient(
            base_url="https://api.github.test", transport=httpx.MockTransport(handler)
        )
        async with http_client:
            service = RepositorySourceService(
                GitHubClient(http_client),
                max_source_file_bytes=1000,
            )
            return await service.collect(
                GitHubRepositoryRef(owner="acme", repo="repo"), "head-sha", set()
            )

    _, snapshot = asyncio.run(run())

    assert len(snapshot.documents) == 0
    assert any(w.code is AnalysisWarningCode.SOURCE_FILE_TOO_LARGE for w in snapshot.warnings)
