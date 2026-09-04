import logging
import re
from urllib.parse import urlparse

from app.analyzers.api_dependency import ApiDependencyAnalyzer
from app.analyzers.dependency import (
    DependencyAnalyzer,
    build_change_facts,
    extract_dependency_targets,
    summarize_impact,
)
from app.analyzers.file_classifier import classify_file
from app.analyzers.openapi_parser import (
    OpenApiParseError,
    OpenApiParser,
    build_api_change_facts,
)
from app.analyzers.sql_migration import SqlMigrationParseError, SqlMigrationParser
from app.clients.github import GitHubClient, GitHubError, GitHubFileContentUnavailable
from app.core.config import get_settings
from app.core.redaction import redact_sql_change
from app.schemas.api_contract import ApiChange
from app.schemas.github import (
    AnalysisStep,
    AnalysisWarning,
    AnalysisWarningCode,
    ApiFileAnalysis,
    ChangedFile,
    ChangedFileStatus,
    ContentSource,
    FileCategory,
    GitHubRepositoryRef,
    PullRequestAnalysis,
    PullRequestMetadata,
    SqlAnalysisResult,
    SqlFileAnalysis,
)
from app.services.controlled_demo_policy import ControlledDemoPolicy
from app.services.failure_planning_service import FailurePlanningService
from app.services.repository_source_service import RepositorySourceService

logger = logging.getLogger(__name__)
REPOSITORY_PART = re.compile(r"^[A-Za-z0-9_.-]+$")


class InvalidGitHubRepository(ValueError):
    pass


def parse_repository_reference(value: str) -> GitHubRepositoryRef:
    normalized = value.strip().rstrip("/")
    if normalized.startswith("https://"):
        parsed = urlparse(normalized)
        if parsed.hostname != "github.com" or parsed.query or parsed.fragment:
            raise InvalidGitHubRepository("Repository must be a github.com URL or owner/repository")
        parts = parsed.path.strip("/").split("/")
    elif "://" not in normalized:
        parts = normalized.split("/")
    else:
        raise InvalidGitHubRepository("Repository must be a github.com URL or owner/repository")

    if len(parts) != 2:
        raise InvalidGitHubRepository("Repository must include an owner and repository name")
    owner, repo = parts
    if repo.endswith(".git"):
        repo = repo[:-4]
    if (
        not owner
        or not repo
        or not REPOSITORY_PART.fullmatch(owner)
        or not REPOSITORY_PART.fullmatch(repo)
    ):
        raise InvalidGitHubRepository("Repository owner or name is invalid")
    return GitHubRepositoryRef(owner=owner, repo=repo)


class PullRequestService:
    def __init__(
        self,
        github_client: GitHubClient,
        sql_parser: SqlMigrationParser,
        source_service: RepositorySourceService | None = None,
        dependency_analyzer: DependencyAnalyzer | None = None,
        planning_service: FailurePlanningService | None = None,
        demo_policy: ControlledDemoPolicy | None = None,
        openapi_parser: OpenApiParser | None = None,
        api_dependency_analyzer: ApiDependencyAnalyzer | None = None,
    ) -> None:
        self._github = github_client
        self._sql_parser = sql_parser
        self._source_service = source_service or RepositorySourceService(github_client)
        self._dependency_analyzer = dependency_analyzer or DependencyAnalyzer()
        self._planning_service = planning_service or FailurePlanningService()
        self._demo_policy = demo_policy or ControlledDemoPolicy(get_settings())
        self._openapi_parser = openapi_parser or OpenApiParser()
        self._api_dependency_analyzer = api_dependency_analyzer or ApiDependencyAnalyzer()

    async def analyze(self, repository_input: str, pull_request: int) -> PullRequestAnalysis:
        completed_steps: list[AnalysisStep] = []
        repository = parse_repository_reference(repository_input)
        await self._github.verify_repository(repository)
        metadata = await self._github.fetch_pull_request(repository, pull_request)
        completed_steps.append(AnalysisStep.FETCH_PR_METADATA)
        self._log_step(AnalysisStep.FETCH_PR_METADATA, repository.full_name, pull_request)

        files = await self._github.fetch_changed_files(repository, pull_request)
        completed_steps.append(AnalysisStep.FETCH_CHANGED_FILES)
        self._log_step(
            AnalysisStep.FETCH_CHANGED_FILES,
            repository.full_name,
            pull_request,
            changed_file_count=len(files),
        )
        classified = [classify_file(file) for file in files]
        completed_steps.append(AnalysisStep.CLASSIFY_FILES)
        self._log_step(
            AnalysisStep.CLASSIFY_FILES,
            repository.full_name,
            pull_request,
            classification_counts={
                category.value: sum(item.category is category for item in classified)
                for category in FileCategory
            },
        )

        warnings = [
            AnalysisWarning(
                code=AnalysisWarningCode.PATCH_UNAVAILABLE,
                path=file.path,
                message="GitHub did not provide a patch for this file",
            )
            for file in files
            if file.patch is None
        ]
        sql_files: list[SqlFileAnalysis] = []
        for item in classified:
            if item.category is not FileCategory.SQL_MIGRATION:
                continue
            analysis, file_warnings = await self._analyze_sql_file(repository, metadata, item.file)
            sql_files.append(analysis)
            warnings.extend(file_warnings)

        if any(item.category is FileCategory.SQL_MIGRATION for item in classified):
            completed_steps.append(AnalysisStep.FETCH_SQL_CONTENT)
        completed_steps.append(AnalysisStep.ANALYZE_SQL)
        self._log_step(
            AnalysisStep.ANALYZE_SQL,
            repository.full_name,
            pull_request,
            sql_success_count=sum(item.analysis is not None for item in sql_files),
            sql_failure_count=sum(item.error is not None for item in sql_files),
        )

        # Process OpenAPI files
        api_files: list[ApiFileAnalysis] = []
        api_changes: list[ApiChange] = []
        for item in classified:
            if item.category is not FileCategory.OPENAPI_SPEC:
                continue
            analysis, changes, file_warnings = await self._analyze_openapi_file(
                repository, metadata, item.file
            )
            api_files.append(analysis)
            api_changes.extend(changes)
            warnings.extend(file_warnings)

        if any(item.category is FileCategory.OPENAPI_SPEC for item in classified):
            completed_steps.append(AnalysisStep.FETCH_OPENAPI_CONTENT)
            completed_steps.append(AnalysisStep.ANALYZE_OPENAPI)
            self._log_step(
                AnalysisStep.ANALYZE_OPENAPI,
                repository.full_name,
                pull_request,
                api_success_count=sum(item.error is None for item in api_files),
                api_change_count=len(api_changes),
            )

        # Build change facts with stable IDs
        change_facts = build_change_facts(sql_files)
        if api_changes:
            api_facts = build_api_change_facts(
                api_changes,
                spec_file_path=api_files[0].path if api_files else "openapi.yaml",
            )
            change_facts.extend(api_facts)

        completed_steps.append(AnalysisStep.BUILD_CHANGE_FACTS)
        self._log_step(
            AnalysisStep.BUILD_CHANGE_FACTS,
            repository.full_name,
            pull_request,
            fact_count=len(change_facts),
        )

        # Extract dependency targets
        targets = extract_dependency_targets(sql_files, change_facts)

        completed_steps.append(AnalysisStep.EXTRACT_DEPENDENCY_TARGETS)
        self._log_step(
            AnalysisStep.EXTRACT_DEPENDENCY_TARGETS,
            repository.full_name,
            pull_request,
            target_count=len(targets),
        )

        # Fetch repository tree & application content at head_sha
        changed_paths = {file.path for file in files}
        tree, snapshot = await self._source_service.collect(
            repository, metadata.head_sha, changed_paths
        )
        completed_steps.append(AnalysisStep.FETCH_REPOSITORY_TREE)
        self._log_step(
            AnalysisStep.FETCH_REPOSITORY_TREE,
            repository.full_name,
            pull_request,
            tree_entry_count=len(tree.entries),
            truncated=tree.truncated,
        )

        completed_steps.append(AnalysisStep.FETCH_APPLICATION_CONTENT)
        self._log_step(
            AnalysisStep.FETCH_APPLICATION_CONTENT,
            repository.full_name,
            pull_request,
            source_document_count=len(snapshot.documents),
        )
        warnings.extend(snapshot.warnings)

        # Discover dependencies (database + API)
        evidences = self._dependency_analyzer.analyze(targets, snapshot.documents)
        if any(cf.domain == "API" for cf in change_facts):
            api_evidences = self._api_dependency_analyzer.analyze(change_facts, snapshot.documents)
            evidences.extend(api_evidences)

        completed_steps.append(AnalysisStep.DISCOVER_DEPENDENCIES)
        self._log_step(
            AnalysisStep.DISCOVER_DEPENDENCIES,
            repository.full_name,
            pull_request,
            evidence_count=len(evidences),
        )

        # Summarize impact
        impact_summary = summarize_impact(
            targets, evidences, scan_complete=snapshot.scan_complete
        )
        completed_steps.append(AnalysisStep.SUMMARIZE_IMPACT)
        self._log_step(
            AnalysisStep.SUMMARIZE_IMPACT,
            repository.full_name,
            pull_request,
            targets=impact_summary.targets,
            application_files_with_references=impact_summary.application_files_with_references,
            test_files_with_references=impact_summary.test_files_with_references,
            qualified_references=impact_summary.qualified_references,
            scan_complete=impact_summary.scan_complete,
        )

        # Phase 5: Generate failure hypotheses & compile executable experiment plans
        hypotheses, plans, plan_warnings, plan_steps = await self._planning_service.plan(
            change_facts,
            evidences,
            scan_complete=snapshot.scan_complete,
            existing_warnings=warnings,
            head_sha=metadata.head_sha,
        )
        warnings.extend(plan_warnings)
        for step in plan_steps:
            completed_steps.append(step)
            self._log_step(
                step,
                repository.full_name,
                pull_request,
                hypothesis_count=len(hypotheses),
                plan_count=len(plans),
            )

        # Evaluate exact server-controlled demo execution policy (no substring matching)
        demo_decision = self._demo_policy.evaluate(repository, metadata, change_facts)
        has_api_facts = any(cf.domain == "API" for cf in change_facts)
        domain = "API" if has_api_facts and not sql_files else "DATABASE"

        return PullRequestAnalysis(
            repository=repository,
            pull_request=metadata,
            changed_files=classified,
            sql_files=sql_files,
            api_files=api_files,
            domain=domain,
            change_facts=change_facts,
            dependency_targets=targets,
            dependency_evidence=evidences,
            impact_summary=impact_summary,
            failure_hypotheses=hypotheses,
            experiment_plans=plans,
            execution_allowed=demo_decision.allowed,
            controlled_fixture_id=demo_decision.fixture_id,
            execution_notice=demo_decision.notice,
            ai_usage=self._planning_service.last_usage,
            warnings=warnings,
            completed_steps=completed_steps,
        )

    async def _analyze_openapi_file(
        self,
        repository: GitHubRepositoryRef,
        metadata: PullRequestMetadata,
        file: ChangedFile,
    ) -> tuple[ApiFileAnalysis, list[ApiChange], list[AnalysisWarning]]:
        try:
            head_content = await self._github.fetch_file_content(
                repository, file.path, metadata.head_sha
            )
        except (GitHubError, GitHubFileContentUnavailable) as error:
            message = f"Failed to fetch head OpenAPI spec content: {error}"
            return (
                ApiFileAnalysis(path=file.path, status=file.status, error=message),
                [],
                [
                    AnalysisWarning(
                        code=AnalysisWarningCode.FILE_CONTENT_UNAVAILABLE,
                        path=file.path,
                        message=message,
                    )
                ],
            )

        base_text = ""
        try:
            base_content = await self._github.fetch_file_content(
                repository, file.path, metadata.base_sha
            )
            if base_content and base_content.content:
                base_text = base_content.content
        except (GitHubError, GitHubFileContentUnavailable):
            base_text = ""

        head_text = head_content.content or ""
        try:
            changes = self._openapi_parser.compare(base_text, head_text, spec_file_path=file.path)
        except OpenApiParseError as error:
            message = str(error)
            return (
                ApiFileAnalysis(
                    path=file.path,
                    status=file.status,
                    content_sha=head_content.sha,
                    error=message,
                ),
                [],
                [
                    AnalysisWarning(
                        code=AnalysisWarningCode.OPENAPI_PARSE_ERROR,
                        path=file.path,
                        message=message,
                    )
                ],
            )

        return (
            ApiFileAnalysis(
                path=file.path,
                status=file.status,
                content_sha=head_content.sha,
                changes=changes,
            ),
            changes,
            [],
        )

    async def _analyze_sql_file(
        self,
        repository: GitHubRepositoryRef,
        metadata: PullRequestMetadata,
        file: ChangedFile,
    ) -> tuple[SqlFileAnalysis, list[AnalysisWarning]]:
        source = (
            ContentSource.BASE if file.status is ChangedFileStatus.REMOVED else ContentSource.HEAD
        )
        revision = metadata.base_sha if source is ContentSource.BASE else metadata.head_sha
        try:
            content = await self._github.fetch_file_content(repository, file.path, revision)
        except (GitHubFileContentUnavailable, GitHubError) as error:
            message = str(error)
            return (
                SqlFileAnalysis(
                    path=file.path,
                    status=file.status,
                    content_source=source,
                    error=message,
                ),
                [
                    AnalysisWarning(
                        code=AnalysisWarningCode.FILE_CONTENT_UNAVAILABLE,
                        path=file.path,
                        message=message,
                    )
                ],
            )

        self._log_step(
            AnalysisStep.FETCH_SQL_CONTENT,
            repository.full_name,
            metadata.number,
            path=file.path,
        )
        if content.too_large:
            message = "SQL migration exceeds the 1 MiB analysis limit"
            return (
                SqlFileAnalysis(
                    path=file.path,
                    status=file.status,
                    content_sha=content.sha,
                    content_source=source,
                    error=message,
                ),
                [
                    AnalysisWarning(
                        code=AnalysisWarningCode.SKIPPED_TOO_LARGE,
                        path=file.path,
                        message=message,
                    )
                ],
            )
        if file.status is ChangedFileStatus.REMOVED:
            return (
                SqlFileAnalysis(
                    path=file.path,
                    status=file.status,
                    content_sha=content.sha,
                    content_source=source,
                ),
                [
                    AnalysisWarning(
                        code=AnalysisWarningCode.REMOVED_SQL_NOT_ANALYZED,
                        path=file.path,
                        message=(
                            "Removed migration was fetched from base but not treated "
                            "as executable SQL"
                        ),
                    )
                ],
            )
        try:
            changes = [
                redact_sql_change(change)
                for change in self._sql_parser.parse(content.content or "")
            ]
        except SqlMigrationParseError as error:
            message = str(error)
            return (
                SqlFileAnalysis(
                    path=file.path,
                    status=file.status,
                    content_sha=content.sha,
                    content_source=source,
                    error=message,
                ),
                [
                    AnalysisWarning(
                        code=AnalysisWarningCode.SQL_PARSE_ERROR,
                        path=file.path,
                        message=message,
                    )
                ],
            )
        return (
            SqlFileAnalysis(
                path=file.path,
                status=file.status,
                content_sha=content.sha,
                content_source=source,
                analysis=SqlAnalysisResult(changes=changes),
            ),
            [],
        )

    @staticmethod
    def _log_step(step: AnalysisStep, repository: str, pull_request: int, **facts) -> None:
        logger.info(
            "github_pr_analysis_step",
            extra={
                "step": step.value,
                "repository": repository,
                "pull_request": pull_request,
                **facts,
            },
        )
