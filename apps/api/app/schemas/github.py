from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas.ai import AIUsageMetadata
from app.schemas.api_contract import ApiChange
from app.schemas.dependency import (
    ChangeFact,
    DependencyEvidence,
    DependencyTarget,
    ImpactSummary,
)
from app.schemas.experiment import ExperimentPlan
from app.schemas.hypothesis import FailureHypothesis
from app.schemas.sql_change import SqlChange


class GitHubRepositoryRef(BaseModel):
    owner: str
    repo: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.repo}"


class GitHubRepositoryMetadata(BaseModel):
    full_name: str
    private: bool
    visibility: str | None = None
    archived: bool = False


class PullRequestMetadata(BaseModel):
    repository: str
    number: int = Field(gt=0)
    title: str
    body: str | None = None
    state: str
    base_branch: str
    head_branch: str
    base_sha: str
    head_sha: str
    author: str | None = None
    changed_files: int = Field(ge=0)
    html_url: str


class ChangedFileStatus(StrEnum):
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    REMOVED = "REMOVED"
    RENAMED = "RENAMED"


class ChangedFile(BaseModel):
    path: str
    previous_path: str | None = None
    status: ChangedFileStatus
    additions: int = Field(ge=0)
    deletions: int = Field(ge=0)
    changes: int = Field(ge=0)
    patch: str | None = None


class FileCategory(StrEnum):
    SQL_MIGRATION = "SQL_MIGRATION"
    DATABASE_SCHEMA = "DATABASE_SCHEMA"
    OPENAPI_SPEC = "OPENAPI_SPEC"
    APPLICATION = "APPLICATION"
    CONFIG = "CONFIG"
    TEST = "TEST"
    DOCUMENTATION = "DOCUMENTATION"
    OTHER = "OTHER"


class ContentPolicy(StrEnum):
    ALLOW = "ALLOW"
    SKIP_SECRET = "SKIP_SECRET"
    SKIP_BINARY = "SKIP_BINARY"
    SKIP_LARGE_LOCKFILE = "SKIP_LARGE_LOCKFILE"


class ClassifiedFile(BaseModel):
    file: ChangedFile
    category: FileCategory
    reason: str
    content_policy: ContentPolicy = ContentPolicy.ALLOW


class ContentSource(StrEnum):
    HEAD = "HEAD"
    BASE = "BASE"


class SqlAnalysisResult(BaseModel):
    changes: list[SqlChange]


class SqlFileAnalysis(BaseModel):
    path: str
    status: ChangedFileStatus
    content_sha: str | None = None
    content_source: ContentSource
    analysis: SqlAnalysisResult | None = None
    error: str | None = None


class ApiFileAnalysis(BaseModel):
    path: str
    status: ChangedFileStatus
    content_sha: str | None = None
    changes: list[ApiChange] = Field(default_factory=list)
    error: str | None = None


class AnalysisWarningCode(StrEnum):
    PATCH_UNAVAILABLE = "PATCH_UNAVAILABLE"
    FILE_CONTENT_UNAVAILABLE = "FILE_CONTENT_UNAVAILABLE"
    SKIPPED_TOO_LARGE = "SKIPPED_TOO_LARGE"
    REMOVED_SQL_NOT_ANALYZED = "REMOVED_SQL_NOT_ANALYZED"
    SQL_PARSE_ERROR = "SQL_PARSE_ERROR"
    OPENAPI_PARSE_ERROR = "OPENAPI_PARSE_ERROR"
    REPOSITORY_TREE_TRUNCATED = "REPOSITORY_TREE_TRUNCATED"
    SOURCE_SCAN_LIMIT_REACHED = "SOURCE_SCAN_LIMIT_REACHED"
    SOURCE_FILE_TOO_LARGE = "SOURCE_FILE_TOO_LARGE"
    SOURCE_CONTENT_UNAVAILABLE = "SOURCE_CONTENT_UNAVAILABLE"
    DEPENDENCY_SCAN_INCOMPLETE = "DEPENDENCY_SCAN_INCOMPLETE"
    AI_NOT_CONFIGURED = "AI_NOT_CONFIGURED"
    AI_REQUEST_FAILED = "AI_REQUEST_FAILED"
    AI_RATE_LIMITED = "AI_RATE_LIMITED"
    AI_OUTPUT_INVALID = "AI_OUTPUT_INVALID"
    HYPOTHESIS_GENERATION_SKIPPED = "HYPOTHESIS_GENERATION_SKIPPED"


class AnalysisWarning(BaseModel):
    code: AnalysisWarningCode
    message: str
    path: str | None = None


class AnalysisStep(StrEnum):
    FETCH_PR_METADATA = "FETCH_PR_METADATA"
    FETCH_CHANGED_FILES = "FETCH_CHANGED_FILES"
    CLASSIFY_FILES = "CLASSIFY_FILES"
    FETCH_SQL_CONTENT = "FETCH_SQL_CONTENT"
    ANALYZE_SQL = "ANALYZE_SQL"
    FETCH_OPENAPI_CONTENT = "FETCH_OPENAPI_CONTENT"
    ANALYZE_OPENAPI = "ANALYZE_OPENAPI"
    BUILD_CHANGE_FACTS = "BUILD_CHANGE_FACTS"
    EXTRACT_DEPENDENCY_TARGETS = "EXTRACT_DEPENDENCY_TARGETS"
    FETCH_REPOSITORY_TREE = "FETCH_REPOSITORY_TREE"
    FETCH_APPLICATION_CONTENT = "FETCH_APPLICATION_CONTENT"
    DISCOVER_DEPENDENCIES = "DISCOVER_DEPENDENCIES"
    SUMMARIZE_IMPACT = "SUMMARIZE_IMPACT"
    GENERATE_FAILURE_HYPOTHESES = "GENERATE_FAILURE_HYPOTHESES"
    VALIDATE_HYPOTHESES = "VALIDATE_HYPOTHESES"
    COMPILE_EXPERIMENT_PLANS = "COMPILE_EXPERIMENT_PLANS"


class PullRequestAnalysis(BaseModel):
    repository: GitHubRepositoryRef
    pull_request: PullRequestMetadata
    changed_files: list[ClassifiedFile]
    sql_files: list[SqlFileAnalysis]
    api_files: list[ApiFileAnalysis] = Field(default_factory=list)
    domain: str = "DATABASE"
    change_facts: list[ChangeFact] = Field(default_factory=list)
    dependency_targets: list[DependencyTarget] = Field(default_factory=list)
    dependency_evidence: list[DependencyEvidence] = Field(default_factory=list)
    impact_summary: ImpactSummary | None = None
    failure_hypotheses: list[FailureHypothesis] = Field(default_factory=list)
    experiment_plans: list[ExperimentPlan] = Field(default_factory=list)
    execution_allowed: bool = False
    controlled_fixture_id: str | None = None
    execution_notice: str | None = None
    ai_usage: AIUsageMetadata | None = None
    warnings: list[AnalysisWarning] = Field(default_factory=list)
    completed_steps: list[AnalysisStep] = Field(default_factory=list)


class AnalyzeGitHubPullRequest(BaseModel):
    repository: str = Field(min_length=1)
    pull_request: int = Field(gt=0)


class GitHubFileContent(BaseModel):
    path: str
    sha: str | None = None
    size: int = Field(ge=0)
    content: str | None = None
    too_large: bool = False
