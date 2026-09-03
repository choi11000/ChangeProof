from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas.sql_change import SqlChange


class GitHubRepositoryRef(BaseModel):
    owner: str
    repo: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.repo}"


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


class AnalysisWarningCode(StrEnum):
    PATCH_UNAVAILABLE = "PATCH_UNAVAILABLE"
    FILE_CONTENT_UNAVAILABLE = "FILE_CONTENT_UNAVAILABLE"
    SKIPPED_TOO_LARGE = "SKIPPED_TOO_LARGE"
    REMOVED_SQL_NOT_ANALYZED = "REMOVED_SQL_NOT_ANALYZED"
    SQL_PARSE_ERROR = "SQL_PARSE_ERROR"


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


class PullRequestAnalysis(BaseModel):
    repository: GitHubRepositoryRef
    pull_request: PullRequestMetadata
    changed_files: list[ClassifiedFile]
    sql_files: list[SqlFileAnalysis]
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
