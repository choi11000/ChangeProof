from datetime import UTC, datetime
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.api.experiments import get_experiment_execution_service
from app.main import app
from app.schemas.execution import (
    ExperimentRun,
    ExperimentStepResult,
    ExperimentStepStatus,
    ExperimentVerdict,
)
from app.schemas.experiment import ExperimentStepType, ExperimentTemplate
from app.services.experiment_execution_service import (
    ExperimentExecutionService,
    UnknownFixtureError,
)

client = TestClient(app)


def test_api_execute_experiment_success() -> None:
    mock_service = MagicMock(spec=ExperimentExecutionService)
    now = datetime.now(UTC)
    mock_run = ExperimentRun(
        id="run_abc123",
        experiment_plan_id="plan_test_01",
        experiment_contract_digest="contract_abc123",
        subject_digest="subject_def456",
        template=ExperimentTemplate.DROPPED_COLUMN_REFERENCE,
        verdict=ExperimentVerdict.PROVEN_FAIL,
        started_at=now,
        finished_at=now,
        step_results=[
            ExperimentStepResult(
                order=1,
                type=ExperimentStepType.PREPARE_DATABASE,
                status=ExperimentStepStatus.PASSED,
                duration_ms=5,
            ),
            ExperimentStepResult(
                order=5,
                type=ExperimentStepType.RUN_READ_QUERY,
                status=ExperimentStepStatus.FAILED,
                duration_ms=10,
                sql_state="42703",
                message='column "legacy_status" does not exist',
            ),
        ],
        summary="Failure reproduced in isolated PostgreSQL.",
    )
    mock_service.execute.return_value = mock_run

    app.dependency_overrides[get_experiment_execution_service] = lambda: mock_service
    try:
        resp = client.post(
            "/api/v1/experiments/execute",
            json={
                "fixture_id": "risky-saas/drop-legacy-status",
                "experiment_plan_id": "plan_test_01",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["run"]["verdict"] == "PROVEN_FAIL"
        assert data["run"]["experiment_contract_digest"] == "contract_abc123"
        assert data["run"]["subject_digest"] == "subject_def456"
        assert len(data["run"]["step_results"]) == 2
    finally:
        app.dependency_overrides.clear()


def test_api_execute_experiment_unknown_fixture_returns_400() -> None:
    mock_service = MagicMock(spec=ExperimentExecutionService)
    mock_service.execute.side_effect = UnknownFixtureError("Unknown fixture")

    app.dependency_overrides[get_experiment_execution_service] = lambda: mock_service
    try:
        resp = client.post(
            "/api/v1/experiments/execute",
            json={"fixture_id": "unknown/fixture"},
        )
        assert resp.status_code == 400
        assert "Unknown fixture" in resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_api_rejects_client_controlled_digest() -> None:
    response = client.post(
        "/api/v1/experiments/execute",
        json={"fixture_id": "risky-saas/drop-legacy-status", "plan_digest": "forged"},
    )
    assert response.status_code == 422
