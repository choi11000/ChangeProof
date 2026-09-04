from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas.experiment import ExperimentTemplate


class HypothesisStatus(StrEnum):
    PROPOSED = "PROPOSED"
    UNVERIFIED = "UNVERIFIED"


class FailureCategory(StrEnum):
    SCHEMA_CONTRACT_BREAK = "SCHEMA_CONTRACT_BREAK"
    MIGRATION_COMPATIBILITY = "MIGRATION_COMPATIBILITY"
    NULLABILITY_COMPATIBILITY = "NULLABILITY_COMPATIBILITY"
    TYPE_COMPATIBILITY = "TYPE_COMPATIBILITY"
    TABLE_CONTRACT_BREAK = "TABLE_CONTRACT_BREAK"
    API_CONTRACT_BREAK = "API_CONTRACT_BREAK"
    OTHER = "OTHER"


class FailureHypothesis(BaseModel):
    id: str
    domain: str = "DATABASE"
    category: FailureCategory
    title: str
    statement: str
    change_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    rationale: str
    expected_failure_mode: str
    assumptions: list[str] = Field(default_factory=list)
    experiment_template: ExperimentTemplate
    status: HypothesisStatus = HypothesisStatus.UNVERIFIED


class HypothesisProposalResult(BaseModel):
    hypotheses: list[FailureHypothesis] = Field(default_factory=list)
