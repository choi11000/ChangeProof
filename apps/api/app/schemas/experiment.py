from enum import StrEnum

from pydantic import BaseModel, Field


class ExperimentTemplate(StrEnum):
    MIGRATION_APPLY = "MIGRATION_APPLY"
    DROPPED_COLUMN_REFERENCE = "DROPPED_COLUMN_REFERENCE"
    DROPPED_TABLE_REFERENCE = "DROPPED_TABLE_REFERENCE"
    NOT_NULL_COMPATIBILITY = "NOT_NULL_COMPATIBILITY"
    ALTER_TYPE_COMPATIBILITY = "ALTER_TYPE_COMPATIBILITY"


class ExperimentStatus(StrEnum):
    PLANNED = "PLANNED"
    NOT_EXECUTED = "NOT_EXECUTED"


class ExperimentStepType(StrEnum):
    PREPARE_DATABASE = "PREPARE_DATABASE"
    LOAD_BASELINE_SCHEMA = "LOAD_BASELINE_SCHEMA"
    LOAD_SEED_DATA = "LOAD_SEED_DATA"
    APPLY_MIGRATION = "APPLY_MIGRATION"
    RUN_READ_QUERY = "RUN_READ_QUERY"
    CAPTURE_RESULT = "CAPTURE_RESULT"


class ExperimentStep(BaseModel):
    order: int = Field(ge=1)
    type: ExperimentStepType
    description: str
    sql: str | None = None


class ExperimentPlan(BaseModel):
    id: str
    hypothesis_id: str
    template: ExperimentTemplate
    change_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    steps: list[ExperimentStep] = Field(default_factory=list)
    expected_observation: str
    status: ExperimentStatus = ExperimentStatus.NOT_EXECUTED
