import asyncio
import base64
from typing import Any

import httpx
import pytest

from app.analyzers.sql_migration import SqlMigrationParser
from app.clients.github import GitHubClient
from app.schemas.dependency import DependencyMatchKind
from app.schemas.github import (
    AnalysisStep,
    AnalysisWarningCode,
    ContentSource,
    FileCategory,
)
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
        if "git/trees/head-sha" in path:
            return httpx.Response(
                200,
                json={
                    "sha": "head-sha",
                    "tree": [
                        {"path": "app/order_service.py", "type": "blob", "sha": "s1"},
                    ],
                    "truncated": False,
                },
            )
        if path.endswith("/contents/app/order_service.py"):
            return httpx.Response(
                200,
                json=_content("return order.legacy_status\n", "app-sha"),
            )
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
    assert len(result.dependency_targets) == 1
    assert len(result.dependency_evidence) == 1
    assert result.dependency_evidence[0].match_kind is DependencyMatchKind.QUALIFIED_REFERENCE


def test_dependency_discovery_finds_unchanged_application_references() -> None:
    """Acceptance test: PR only touches SQL migration; repo tree has unchanged application file."""
    sql_content = "ALTER TABLE orders DROP COLUMN legacy_status;"
    app_code = (
        "from dataclasses import dataclass\n"
        "\n"
        "@dataclass\n"
        "class Order:\n"
        "    id: int\n"
        "    legacy_status: str\n"
        "\n"
        "def serialize_order(order: Order) -> dict:\n"
        "    return {'id': order.id, 'status': order.legacy_status}\n"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/repos/acme/risky-saas":
            return httpx.Response(200, json={"full_name": "acme/risky-saas"})
        if path == "/repos/acme/risky-saas/pulls/42":
            return httpx.Response(200, json=_pull_request())
        if path == "/repos/acme/risky-saas/pulls/42/files":
            # Only the migration is changed in this PR!
            return httpx.Response(
                200,
                json=[_file("migrations/001_drop_legacy_status.sql", patch="@@ -0,0 +1 @@")],
            )
        if path.endswith("/contents/migrations/001_drop_legacy_status.sql"):
            return httpx.Response(200, json=_content(sql_content, "sql-sha"))
        if "git/trees/head-sha" in path:
            return httpx.Response(
                200,
                json={
                    "sha": "head-sha",
                    "tree": [
                        {
                            "path": "migrations/001_drop_legacy_status.sql",
                            "type": "blob",
                            "sha": "sql-sha",
                        },
                        {"path": "app/order_service.py", "type": "blob", "sha": "app-sha"},
                    ],
                    "truncated": False,
                },
            )
        if path.endswith("/contents/app/order_service.py"):
            return httpx.Response(200, json=_content(app_code, "app-sha"))
        raise AssertionError(f"Unexpected request: {request.url}")

    async def scenario():
        http_client = httpx.AsyncClient(
            base_url="https://api.github.test", transport=httpx.MockTransport(handler)
        )
        async with http_client:
            service = PullRequestService(GitHubClient(http_client), SqlMigrationParser())
            return await service.analyze("https://github.com/acme/risky-saas", 42)

    result = asyncio.run(scenario())

    assert len(result.change_facts) == 1
    assert result.change_facts[0].id.startswith("change_")
    assert len(result.dependency_targets) == 1
    target = result.dependency_targets[0]
    assert (target.table, target.column) == ("orders", "legacy_status")
    assert target.change_ids == [result.change_facts[0].id]

    # Critical Phase 4 verification:
    # app/order_service.py was NOT in PR changed files, but its reference is discovered!
    assert len(result.dependency_evidence) >= 1
    qualified_evidence = next(
        e for e in result.dependency_evidence
        if e.match_kind is DependencyMatchKind.QUALIFIED_REFERENCE and e.line == 9
    )
    assert qualified_evidence.path == "app/order_service.py"
    assert qualified_evidence.changed_in_pull_request is False
    assert qualified_evidence.id.startswith("ev_")
    assert "order.legacy_status" in qualified_evidence.excerpt

    assert result.impact_summary is not None
    assert result.impact_summary.application_files_with_references == 1
    assert result.impact_summary.scan_complete is True

    # Check all completed steps
    expected_steps = [
        AnalysisStep.FETCH_PR_METADATA,
        AnalysisStep.FETCH_CHANGED_FILES,
        AnalysisStep.CLASSIFY_FILES,
        AnalysisStep.FETCH_SQL_CONTENT,
        AnalysisStep.ANALYZE_SQL,
        AnalysisStep.BUILD_CHANGE_FACTS,
        AnalysisStep.EXTRACT_DEPENDENCY_TARGETS,
        AnalysisStep.FETCH_REPOSITORY_TREE,
        AnalysisStep.FETCH_APPLICATION_CONTENT,
        AnalysisStep.DISCOVER_DEPENDENCIES,
        AnalysisStep.SUMMARIZE_IMPACT,
    ]
    assert any(w.code is AnalysisWarningCode.AI_NOT_CONFIGURED for w in result.warnings)
    assert result.failure_hypotheses == []
    assert result.experiment_plans == []
    assert result.completed_steps == expected_steps


def test_pull_request_service_end_to_end_with_failure_planning() -> None:
    from app.clients.openai_client import FailurePlanningContext
    from app.schemas.experiment import ExperimentStatus, ExperimentTemplate
    from app.schemas.hypothesis import (
        FailureCategory,
        FailureHypothesis,
        HypothesisProposalResult,
        HypothesisStatus,
    )
    from app.services.failure_planning_service import FailurePlanningService

    class GeneratorMock:
        is_configured = True

        async def generate(self, context: FailurePlanningContext) -> HypothesisProposalResult:
            cid = context.changes[0].id
            eid = context.evidence[0].id
            return HypothesisProposalResult(
                hypotheses=[
                    FailureHypothesis(
                        id="hyp_001",
                        category=FailureCategory.SCHEMA_CONTRACT_BREAK,
                        title="Dropped column remains referenced",
                        statement=(
                            "orders.legacy_status is dropped but referenced in "
                            "order_service.py"
                        ),
                        change_ids=[cid],
                        evidence_ids=[eid],
                        rationale="order_service.py references dropped column",
                        expected_failure_mode="UndefinedColumn",
                        assumptions=["orders table contains rows"],
                        experiment_template=ExperimentTemplate.DROPPED_COLUMN_REFERENCE,
                        status=HypothesisStatus.UNVERIFIED,
                    )
                ]
            )

    diff_content = "ALTER TABLE orders DROP COLUMN legacy_status;"
    app_code = "return order.legacy_status"

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/repos/acme/risky-saas":
            return httpx.Response(200, json={"full_name": "acme/risky-saas"})
        if path == "/repos/acme/risky-saas/pulls/42":
            return httpx.Response(200, json=_pull_request())
        if path == "/repos/acme/risky-saas/pulls/42/files":
            return httpx.Response(200, json=[_file("migrations/001.sql", patch=diff_content)])
        if path.endswith("/contents/migrations/001.sql"):
            return httpx.Response(200, json=_content(diff_content, "mig-sha"))
        if "git/trees/head-sha" in path:
            return httpx.Response(
                200,
                json={
                    "sha": "head-sha",
                    "tree": [
                        {"path": "migrations/001.sql", "type": "blob", "sha": "mig-sha"},
                        {"path": "app/order_service.py", "type": "blob", "sha": "app-sha"},
                    ],
                    "truncated": False,
                },
            )
        if path.endswith("/contents/app/order_service.py"):
            return httpx.Response(200, json=_content(app_code, "app-sha"))
        raise AssertionError(f"Unexpected request: {request.url}")

    async def scenario():
        http_client = httpx.AsyncClient(
            base_url="https://api.github.test", transport=httpx.MockTransport(handler)
        )
        async with http_client:
            planning = FailurePlanningService(generator=GeneratorMock())
            service = PullRequestService(
                GitHubClient(http_client),
                SqlMigrationParser(),
                planning_service=planning,
            )
            return await service.analyze("https://github.com/acme/risky-saas", 42)

    result = asyncio.run(scenario())

    assert len(result.failure_hypotheses) == 1
    hyp = result.failure_hypotheses[0]
    assert hyp.id == "hyp_001"
    assert hyp.status is HypothesisStatus.UNVERIFIED

    assert len(result.experiment_plans) == 1
    plan = result.experiment_plans[0]
    assert plan.status is ExperimentStatus.NOT_EXECUTED
    assert plan.template is ExperimentTemplate.DROPPED_COLUMN_REFERENCE

    expected_steps = [
        AnalysisStep.FETCH_PR_METADATA,
        AnalysisStep.FETCH_CHANGED_FILES,
        AnalysisStep.CLASSIFY_FILES,
        AnalysisStep.FETCH_SQL_CONTENT,
        AnalysisStep.ANALYZE_SQL,
        AnalysisStep.BUILD_CHANGE_FACTS,
        AnalysisStep.EXTRACT_DEPENDENCY_TARGETS,
        AnalysisStep.FETCH_REPOSITORY_TREE,
        AnalysisStep.FETCH_APPLICATION_CONTENT,
        AnalysisStep.DISCOVER_DEPENDENCIES,
        AnalysisStep.SUMMARIZE_IMPACT,
        AnalysisStep.GENERATE_FAILURE_HYPOTHESES,
        AnalysisStep.VALIDATE_HYPOTHESES,
        AnalysisStep.COMPILE_EXPERIMENT_PLANS,
    ]
    assert result.completed_steps == expected_steps


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
        if "git/trees/head-sha" in path:
            return httpx.Response(
                200,
                json={"sha": "head-sha", "tree": [], "truncated": False},
            )
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


def test_mocked_pr_pipeline_analyzes_openapi_spec() -> None:
    base_openapi = """
openapi: "3.0.0"
info:
  title: Users API
  version: "1.0.0"
paths:
  /users/{id}:
    get:
      responses:
        "200":
          content:
            application/json:
              schema:
                type: object
                properties:
                  id: {type: integer}
                  email: {type: string}
"""
    head_openapi = """
openapi: "3.0.0"
info:
  title: Users API
  version: "1.0.0"
paths:
  /users/{id}:
    get:
      responses:
        "200":
          content:
            application/json:
              schema:
                type: object
                properties:
                  id: {type: integer}
"""
    client_code = "return response['email']\n"

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/repos/acme/user-service":
            return httpx.Response(200, json={"full_name": "acme/user-service"})
        if path == "/repos/acme/user-service/pulls/10":
            return httpx.Response(
                200,
                json={
                    "number": 10,
                    "title": "Remove email from User response",
                    "body": "Breaking change",
                    "state": "open",
                    "base": {"ref": "main", "sha": "base-sha"},
                    "head": {"ref": "feature/api", "sha": "head-sha"},
                    "user": {"login": "dev"},
                    "changed_files": 1,
                    "html_url": "https://github.com/acme/user-service/pull/10",
                },
            )
        if path == "/repos/acme/user-service/pulls/10/files":
            return httpx.Response(
                200,
                json=[
                    _file("openapi.yaml", status="modified", patch="@@ -10,1 +10,0 @@"),
                ],
            )
        if path == "/repos/acme/user-service/contents/openapi.yaml":
            ref = request.url.params.get("ref")
            if ref == "base-sha":
                return httpx.Response(200, json=_content(base_openapi, "sha-base-spec"))
            if ref == "head-sha":
                return httpx.Response(200, json=_content(head_openapi, "sha-head-spec"))
        if "git/trees/head-sha" in path:
            return httpx.Response(
                200,
                json={
                    "sha": "head-sha",
                    "tree": [
                        {"path": "client/user_client.py", "type": "blob", "sha": "c1"},
                    ],
                    "truncated": False,
                },
            )
        if path.endswith("/contents/client/user_client.py"):
            return httpx.Response(200, json=_content(client_code, "sha-client"))
        return httpx.Response(404, json={"message": f"Not found: {path}"})

    async def scenario():
        http_client = httpx.AsyncClient(
            base_url="https://api.github.test", transport=httpx.MockTransport(handler)
        )
        async with http_client:
            service = PullRequestService(GitHubClient(http_client), SqlMigrationParser())
            return await service.analyze("https://github.com/acme/user-service", 10)

    result = asyncio.run(scenario())

    assert result.domain == "API"
    assert len(result.api_files) == 1
    assert result.api_files[0].path == "openapi.yaml"
    assert len(result.api_files[0].changes) == 1
    assert result.api_files[0].changes[0].field_name == "email"

    assert len(result.change_facts) == 1
    assert result.change_facts[0].domain == "API"
    assert result.change_facts[0].api_change.field_name == "email"

    assert len(result.dependency_evidence) == 1
    assert result.dependency_evidence[0].target.field == "email"
    assert result.dependency_evidence[0].path == "client/user_client.py"
