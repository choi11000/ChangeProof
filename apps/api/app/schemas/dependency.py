from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas.api_contract import ApiChange
from app.schemas.performance import PerformanceChange
from app.schemas.sql_change import SqlChange


class DependencyTargetType(StrEnum):
    TABLE = "TABLE"
    COLUMN = "COLUMN"
    API_ENDPOINT = "API_ENDPOINT"
    API_FIELD = "API_FIELD"
    PERFORMANCE_ENDPOINT = "PERFORMANCE_ENDPOINT"


class ChangeFact(BaseModel):
    id: str
    domain: str = "DATABASE"
    sql_file_path: str = ""
    content_sha: str | None = None
    statement_index: int = Field(default=0, ge=0)
    change: SqlChange | None = None
    api_change: ApiChange | None = None
    performance_change: PerformanceChange | None = None


class DependencyTarget(BaseModel):
    type: DependencyTargetType
    table: str = ""
    column: str | None = None
    path: str | None = None
    field: str | None = None
    change_ids: list[str] = Field(default_factory=list)


class SourceScope(StrEnum):
    APPLICATION = "APPLICATION"
    TEST = "TEST"


class DependencyMatchKind(StrEnum):
    QUALIFIED_REFERENCE = "QUALIFIED_REFERENCE"
    TABLE_AND_COLUMN_CONTEXT = "TABLE_AND_COLUMN_CONTEXT"
    COLUMN_IDENTIFIER = "COLUMN_IDENTIFIER"
    TABLE_IDENTIFIER = "TABLE_IDENTIFIER"
    DIRECT_RESPONSE_FIELD_REFERENCE = "DIRECT_RESPONSE_FIELD_REFERENCE"


class DependencyEvidence(BaseModel):
    id: str
    target: DependencyTarget
    path: str
    line: int = Field(gt=0)
    match_kind: DependencyMatchKind
    excerpt: str
    source_scope: SourceScope
    source_sha: str | None = None
    changed_in_pull_request: bool = False


class ImpactSummary(BaseModel):
    targets: int = Field(ge=0)
    application_files_with_references: int = Field(ge=0)
    test_files_with_references: int = Field(ge=0)
    qualified_references: int = Field(ge=0)
    contextual_references: int = Field(ge=0)
    identifier_references: int = Field(ge=0)
    scan_complete: bool = True


class RepositoryTreeEntry(BaseModel):
    path: str
    sha: str | None = None
    type: str
    size: int | None = None


class RepositoryTree(BaseModel):
    entries: list[RepositoryTreeEntry]
    truncated: bool = False


class SourceDocument(BaseModel):
    path: str
    sha: str | None = None
    scope: SourceScope
    content: str
    changed_in_pull_request: bool = False
