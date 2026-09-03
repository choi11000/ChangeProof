from datetime import UTC, datetime

import pytest

from app.executors.postgres_experiment import FixtureExecutionResult
from app.schemas.execution import (
    ExperimentRun,
    ExperimentStepResult,
    ExperimentStepStatus,
    ExperimentVerdict,
)
from app.schemas.experiment import ExperimentStepType, ExperimentTemplate
from app.schemas.remediation import (
    RemediationProofRequest,
    RemediationProofVerdict,
)
from app.services.experiment_execution_service import ExperimentExecutionService
from app.services.remediation_proof_service import (
    RemediationProofService,
    RemediationUnavailableError,
    evaluate_proof_pair,
)


class DeterministicFixtureExecutor:
    def execute_fixture(self, fixture, *, repo_root):
        remediated = "/remediations/" in fixture.migration_path.replace("\\", "/")
        statuses = {step: ExperimentStepStatus.PASSED for step in ExperimentStepType}
        sqlstates: dict[ExperimentStepType, str] = {}
        if not remediated and fixture.template is ExperimentTemplate.DROPPED_COLUMN_REFERENCE:
            statuses[ExperimentStepType.RUN_READ_QUERY] = ExperimentStepStatus.FAILED
            sqlstates[ExperimentStepType.RUN_READ_QUERY] = "42703"
        elif not remediated and fixture.template is ExperimentTemplate.DROPPED_TABLE_REFERENCE:
            statuses[ExperimentStepType.RUN_READ_QUERY] = ExperimentStepStatus.FAILED
            sqlstates[ExperimentStepType.RUN_READ_QUERY] = "42P01"
        elif not remediated and fixture.template is ExperimentTemplate.NOT_NULL_COMPATIBILITY:
            statuses[ExperimentStepType.APPLY_MIGRATION] = ExperimentStepStatus.FAILED
            statuses[ExperimentStepType.RUN_READ_QUERY] = ExperimentStepStatus.SKIPPED
            sqlstates[ExperimentStepType.APPLY_MIGRATION] = "23502"
        elif not remediated and fixture.template is ExperimentTemplate.ALTER_TYPE_COMPATIBILITY:
            statuses[ExperimentStepType.APPLY_MIGRATION] = ExperimentStepStatus.FAILED
            statuses[ExperimentStepType.RUN_READ_QUERY] = ExperimentStepStatus.SKIPPED
            sqlstates[ExperimentStepType.APPLY_MIGRATION] = "22001"
        results = [
            ExperimentStepResult(
                order=index,
                type=step,
                status=statuses[step],
                duration_ms=1,
                sql_state=sqlstates.get(step),
            )
            for index, step in enumerate(ExperimentStepType, start=1)
        ]
        return FixtureExecutionResult(results, True)


@pytest.mark.parametrize(
    "fixture_id",
    [
        "risky-saas/drop-legacy-status",
        "risky-saas/drop-payments",
        "risky-saas/set-not-null",
        "risky-saas/shrink-email",
    ],
)
def test_controlled_remediation_proves_fixed(fixture_id: str) -> None:
    execution = ExperimentExecutionService(DeterministicFixtureExecutor())
    proof = RemediationProofService(execution).prove(
        RemediationProofRequest(fixture_id=fixture_id)
    )
    assert proof.before.verdict is ExperimentVerdict.PROVEN_FAIL
    assert proof.after.verdict is ExperimentVerdict.PROVEN_PASS
    assert proof.same_experiment is True
    assert proof.subject_changed is True
    assert proof.verdict is RemediationProofVerdict.PROVEN_FIXED
    assert "same experiment passed" in proof.summary.lower()


def test_safe_additive_has_no_remediation() -> None:
    execution = ExperimentExecutionService(DeterministicFixtureExecutor())
    with pytest.raises(RemediationUnavailableError, match="No remediation"):
        RemediationProofService(execution).prove(
            RemediationProofRequest(fixture_id="risky-saas/safe-additive")
        )


def _run(verdict: ExperimentVerdict, contract: str, subject: str) -> ExperimentRun:
    now = datetime.now(UTC)
    return ExperimentRun(
        id="run_test",
        experiment_plan_id="plan_test",
        experiment_contract_digest=contract,
        subject_digest=subject,
        template=ExperimentTemplate.DROPPED_COLUMN_REFERENCE,
        verdict=verdict,
        started_at=now,
        finished_at=now,
        cleanup_succeeded=True,
        summary="test",
    )


def test_different_contract_cannot_produce_proven_fixed() -> None:
    verdict, same, changed = evaluate_proof_pair(
        _run(ExperimentVerdict.PROVEN_FAIL, "contract_a", "subject_a"),
        _run(ExperimentVerdict.PROVEN_PASS, "contract_b", "subject_b"),
    )
    assert verdict is RemediationProofVerdict.INCONCLUSIVE
    assert same is False
    assert changed is True


def test_unchanged_subject_cannot_produce_proven_fixed() -> None:
    verdict, same, changed = evaluate_proof_pair(
        _run(ExperimentVerdict.PROVEN_FAIL, "contract_a", "subject_a"),
        _run(ExperimentVerdict.PROVEN_PASS, "contract_a", "subject_a"),
    )
    assert verdict is RemediationProofVerdict.INCONCLUSIVE
    assert same is True
    assert changed is False


def test_failed_remediation_is_not_fixed() -> None:
    verdict, _, _ = evaluate_proof_pair(
        _run(ExperimentVerdict.PROVEN_FAIL, "contract_a", "subject_a"),
        _run(ExperimentVerdict.PROVEN_FAIL, "contract_a", "subject_b"),
    )
    assert verdict is RemediationProofVerdict.NOT_FIXED


def test_execution_error_propagates_to_proof() -> None:
    verdict, _, _ = evaluate_proof_pair(
        _run(ExperimentVerdict.EXECUTION_ERROR, "contract_a", "subject_a"),
        _run(ExperimentVerdict.PROVEN_PASS, "contract_a", "subject_b"),
    )
    assert verdict is RemediationProofVerdict.EXECUTION_ERROR
