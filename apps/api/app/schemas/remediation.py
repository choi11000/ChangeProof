from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.schemas.execution import ExperimentRun


class RemediationStrategy(StrEnum):
    PRESERVE_COLUMN_COMPATIBILITY = "PRESERVE_COLUMN_COMPATIBILITY"
    PRESERVE_TABLE_COMPATIBILITY = "PRESERVE_TABLE_COMPATIBILITY"
    BACKFILL_BEFORE_NOT_NULL = "BACKFILL_BEFORE_NOT_NULL"
    NORMALIZE_BEFORE_TYPE_CHANGE = "NORMALIZE_BEFORE_TYPE_CHANGE"


class RemediationProofVerdict(StrEnum):
    PROVEN_FIXED = "PROVEN_FIXED"
    NOT_FIXED = "NOT_FIXED"
    INCONCLUSIVE = "INCONCLUSIVE"
    EXECUTION_ERROR = "EXECUTION_ERROR"


class RemediationProofRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fixture_id: str


class RemediationProof(BaseModel):
    id: str
    fixture_id: str
    remediation_id: str
    strategy: RemediationStrategy
    description: str
    experiment_contract_digest: str
    before: ExperimentRun
    after: ExperimentRun
    verdict: RemediationProofVerdict
    same_experiment: bool
    subject_changed: bool
    summary: str
    scope_notice: str = (
        "This proof applies to this controlled experiment, not to the entire pull request "
        "or production system."
    )


class RemediationProofResponse(BaseModel):
    proof: RemediationProof
