import uuid

from app.fixtures.experiment_registry import get_controlled_fixture
from app.fixtures.remediation_registry import get_controlled_remediation
from app.schemas.execution import ExecuteExperimentRequest, ExperimentRun, ExperimentVerdict
from app.schemas.remediation import (
    RemediationProof,
    RemediationProofRequest,
    RemediationProofVerdict,
)
from app.services.experiment_execution_service import ExperimentExecutionService


class RemediationUnavailableError(ValueError):
    """Raised when no allowlisted remediation is available for a fixture."""


def evaluate_proof_pair(
    before: ExperimentRun, after: ExperimentRun
) -> tuple[RemediationProofVerdict, bool, bool]:
    same_experiment = (
        before.experiment_contract_digest == after.experiment_contract_digest
    )
    subject_changed = before.subject_digest != after.subject_digest
    if (
        before.verdict is ExperimentVerdict.EXECUTION_ERROR
        or after.verdict is ExperimentVerdict.EXECUTION_ERROR
    ):
        return RemediationProofVerdict.EXECUTION_ERROR, same_experiment, subject_changed
    if before.cleanup_succeeded is False or after.cleanup_succeeded is False:
        return RemediationProofVerdict.INCONCLUSIVE, same_experiment, subject_changed
    if not same_experiment or not subject_changed:
        return RemediationProofVerdict.INCONCLUSIVE, same_experiment, subject_changed
    if (
        before.verdict is ExperimentVerdict.PROVEN_FAIL
        and after.verdict is ExperimentVerdict.PROVEN_PASS
    ):
        return RemediationProofVerdict.PROVEN_FIXED, same_experiment, subject_changed
    if (
        before.verdict is ExperimentVerdict.PROVEN_FAIL
        and after.verdict is ExperimentVerdict.PROVEN_FAIL
    ):
        return RemediationProofVerdict.NOT_FIXED, same_experiment, subject_changed
    return RemediationProofVerdict.INCONCLUSIVE, same_experiment, subject_changed


class RemediationProofService:
    def __init__(self, execution_service: ExperimentExecutionService) -> None:
        self.execution_service = execution_service

    def prove(self, request: RemediationProofRequest) -> RemediationProof:
        fixture = get_controlled_fixture(request.fixture_id)
        remediation = get_controlled_remediation(request.fixture_id)
        if fixture is None or remediation is None:
            raise RemediationUnavailableError(
                "No remediation is required or available for this controlled experiment."
            )

        before = self.execution_service.execute(
            ExecuteExperimentRequest(fixture_id=fixture.id)
        )
        after = self.execution_service.execute_controlled_fixture(
            fixture,
            subject_variant="remediated",
            migration_path=remediation.remediated_migration_path,
        )
        verdict, same_experiment, subject_changed = evaluate_proof_pair(before, after)
        return RemediationProof(
            id=f"proof_{uuid.uuid4().hex[:12]}",
            fixture_id=fixture.id,
            remediation_id=remediation.id,
            strategy=remediation.strategy,
            description=remediation.description,
            experiment_contract_digest=before.experiment_contract_digest,
            before=before,
            after=after,
            verdict=verdict,
            same_experiment=same_experiment,
            subject_changed=subject_changed,
            summary=self._summary(verdict),
        )

    @staticmethod
    def _summary(verdict: RemediationProofVerdict) -> str:
        if verdict is RemediationProofVerdict.PROVEN_FIXED:
            return (
                "Failure reproduced before remediation. The same experiment passed after "
                "remediation."
            )
        if verdict is RemediationProofVerdict.NOT_FIXED:
            return "The same experiment still failed after the controlled remediation."
        if verdict is RemediationProofVerdict.EXECUTION_ERROR:
            return "Remediation proof could not complete because sandbox execution failed."
        return "Remediation proof is inconclusive because its proof invariants were not met."
