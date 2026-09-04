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
    EXTERNAL_DEPENDENCY_BOTTLENECK = "EXTERNAL_DEPENDENCY_BOTTLENECK"
    OTHER = "OTHER"


class PerformanceScenarioType(StrEnum):
    SLOW_DOWNSTREAM = "SLOW_DOWNSTREAM"
    TIMEOUT_SPIKE = "TIMEOUT_SPIKE"
    BURST_CONCURRENCY = "BURST_CONCURRENCY"


class LoadIntensity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


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
    # Performance Scenario Dimensions (AI proposed bounded parameters)
    scenario_type: PerformanceScenarioType | None = None
    intensity: LoadIntensity | None = None
    risk_mechanism: str | None = None
    why_functional_test_misses_it: str | None = None
    stress_dimension: str | None = None


class HypothesisProposalResult(BaseModel):
    hypotheses: list[FailureHypothesis] = Field(default_factory=list)
