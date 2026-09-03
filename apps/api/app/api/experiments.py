from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.core.rate_limit import enforce_experiment_rate_limit
from app.core.sandbox_gate import SandboxExecutionGate, get_sandbox_gate
from app.executors.postgres_experiment import PostgresExperimentExecutor
from app.schemas.execution import (
    ExecuteExperimentRequest,
    ExecuteExperimentResponse,
)
from app.services.experiment_execution_service import (
    ExperimentExecutionService,
    UnknownFixtureError,
)

router = APIRouter(prefix="/experiments", tags=["experiments"])


def get_experiment_execution_service(
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> ExperimentExecutionService:
    executor = PostgresExperimentExecutor(settings.sandbox_database_url)
    return ExperimentExecutionService(executor)


@router.post(
    "/execute",
    response_model=ExecuteExperimentResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute controlled experiment fixture in isolated PostgreSQL sandbox",
)
def execute_experiment(
    payload: ExecuteExperimentRequest,
    _rate_limit: None = Depends(enforce_experiment_rate_limit),  # noqa: B008
    gate: SandboxExecutionGate = Depends(get_sandbox_gate),  # noqa: B008
    service: ExperimentExecutionService = Depends(get_experiment_execution_service),  # noqa: B008
) -> ExecuteExperimentResponse:
    try:
        with gate.slot():
            run = service.execute(payload)
        return ExecuteExperimentResponse(run=run)
    except UnknownFixtureError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
