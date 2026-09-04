from unittest.mock import MagicMock

import pytest

from app.analyzers.experiment_verifier import ExperimentVerifier
from app.schemas.execution import (
    ExecuteExperimentRequest,
    ExperimentStepResult,
    ExperimentStepStatus,
    ExperimentVerdict,
)
from app.schemas.experiment import ExperimentStepType, ExperimentTemplate
from app.services.experiment_execution_service import (
    ExperimentExecutionService,
    UnknownFixtureError,
)


def test_service_executes_controlled_fixture_producing_proven_fail() -> None:
    mock_executor = MagicMock()
    mock_executor.execute_fixture.return_value = [
        ExperimentStepResult(
            order=1,
            type=ExperimentStepType.PREPARE_DATABASE,
            status=ExperimentStepStatus.PASSED,
            duration_ms=5,
        ),
        ExperimentStepResult(
            order=2,
            type=ExperimentStepType.LOAD_BASELINE_SCHEMA,
            status=ExperimentStepStatus.PASSED,
            duration_ms=5,
        ),
        ExperimentStepResult(
            order=3,
            type=ExperimentStepType.LOAD_SEED_DATA,
            status=ExperimentStepStatus.PASSED,
            duration_ms=5,
        ),
        ExperimentStepResult(
            order=4,
            type=ExperimentStepType.APPLY_MIGRATION,
            status=ExperimentStepStatus.PASSED,
            duration_ms=5,
        ),
        ExperimentStepResult(
            order=5,
            type=ExperimentStepType.RUN_READ_QUERY,
            status=ExperimentStepStatus.FAILED,
            duration_ms=5,
            sql_state="42703",
            message='column "legacy_status" does not exist',
        ),
        ExperimentStepResult(
            order=6,
            type=ExperimentStepType.CAPTURE_RESULT,
            status=ExperimentStepStatus.PASSED,
            duration_ms=1,
        ),
    ]

    service = ExperimentExecutionService(
        executor=mock_executor,
        verifier=ExperimentVerifier(),
    )
    request = ExecuteExperimentRequest(
        fixture_id="risky-saas/drop-legacy-status",
        experiment_plan_id="plan_test_01",
    )

    run = service.execute(request)
    assert run.experiment_plan_id == "plan_test_01"
    assert run.template is ExperimentTemplate.DROPPED_COLUMN_REFERENCE
    assert run.verdict is ExperimentVerdict.PROVEN_FAIL
    assert run.experiment_contract_digest.startswith("contract_")
    assert run.subject_digest.startswith("subject_")
    assert len(run.step_results) == 6
    assert "Failure reproduced in isolated PostgreSQL" in run.summary


def test_service_rejects_unknown_fixture() -> None:
    mock_executor = MagicMock()
    service = ExperimentExecutionService(executor=mock_executor)

    request = ExecuteExperimentRequest(fixture_id="malicious/unregistered-fixture")
    with pytest.raises(UnknownFixtureError, match="strictly restricted"):
        service.execute(request)
