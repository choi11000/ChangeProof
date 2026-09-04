from app.schemas.execution import ExperimentVerdict
from app.schemas.remediation import (
    RemediationProofRequest,
    RemediationProofVerdict,
    RemediationStrategy,
)
from app.services.experiment_execution_service import ExperimentExecutionService
from app.services.remediation_proof_service import RemediationProofService


def test_api_remediation_proof_lifecycle():
    exec_service = ExperimentExecutionService()
    proof_service = RemediationProofService(execution_service=exec_service)

    req = RemediationProofRequest(fixture_id="api-contract/remove-user-email")
    proof = proof_service.prove(req)

    assert proof.domain == "API"
    assert proof.verdict == RemediationProofVerdict.PROVEN_FIXED
    assert proof.strategy == RemediationStrategy.PRESERVE_API_RESPONSE_FIELD_COMPATIBILITY
    assert proof.same_experiment is True
    assert proof.subject_changed is True
    assert proof.before.experiment_contract_digest == proof.after.experiment_contract_digest
    assert proof.before.subject_digest != proof.after.subject_digest
    assert proof.before.verdict == ExperimentVerdict.PROVEN_FAIL
    assert proof.after.verdict == ExperimentVerdict.PROVEN_PASS
    assert proof.before.step_results[2].observation_code == "API_MISSING_RESPONSE_FIELD"
