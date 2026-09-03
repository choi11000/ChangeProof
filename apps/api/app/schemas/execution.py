from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

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
    error_type: str | None = None
    message: str | None = None
    scalar_value: int | str | bool | None = None
    row_count: int | None = None


class ExperimentRun(BaseModel):
    id: str
    experiment_plan_id: str
    plan_digest: str
    template: ExperimentTemplate
    verdict: ExperimentVerdict
    started_at: datetime
    finished_at: datetime
    step_results: list[ExperimentStepResult] = Field(default_factory=list)
    summary: str


class ExecuteExperimentRequest(BaseModel):
    fixture_id: str
    experiment_plan_id: str | None = None
    plan_digest: str | None = None


class ExecuteExperimentResponse(BaseModel):
    run: ExperimentRun
