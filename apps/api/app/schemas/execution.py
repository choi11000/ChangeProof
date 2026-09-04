from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.experiment import ExperimentStepType, ExperimentTemplate


class ExperimentVerdict(StrEnum):
    PROVEN_FAIL = "PROVEN_FAIL"
    PROVEN_PASS = "PROVEN_PASS"
    INCONCLUSIVE = "INCONCLUSIVE"
    EXECUTION_ERROR = "EXECUTION_ERROR"


class ExperimentStepStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ExperimentStepResult(BaseModel):
    order: int
    type: ExperimentStepType
    status: ExperimentStepStatus
    duration_ms: int = Field(ge=0)
    sql_state: str | None = None
    observation_code: str | None = None
    json_pointer: str | None = None
    http_status: int | None = None
    error_type: str | None = None
    message: str | None = None
    scalar_value: int | str | bool | None = None
    row_count: int | None = None


class ExperimentRun(BaseModel):
    id: str
    experiment_plan_id: str
    experiment_contract_digest: str
    subject_digest: str
    template: ExperimentTemplate
    domain: str = "DATABASE"
    verdict: ExperimentVerdict
    started_at: datetime
    finished_at: datetime
    step_results: list[ExperimentStepResult] = Field(default_factory=list)
    cleanup_succeeded: bool | None = None
    summary: str


class ExecuteExperimentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fixture_id: str
    experiment_plan_id: str | None = None


class ExecuteExperimentResponse(BaseModel):
    run: ExperimentRun
