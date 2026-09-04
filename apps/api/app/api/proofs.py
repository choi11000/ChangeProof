from fastapi import APIRouter, Depends, HTTPException, status

from app.api.experiments import get_experiment_execution_service
from app.core.rate_limit import enforce_proof_rate_limit
from app.core.sandbox_gate import SandboxExecutionGate, get_sandbox_gate
from app.schemas.remediation import RemediationProofRequest, RemediationProofResponse
from app.services.experiment_execution_service import ExperimentExecutionService
from app.services.remediation_proof_service import (
    RemediationProofService,
    RemediationUnavailableError,
)

router = APIRouter(prefix="/proofs", tags=["proofs"])


def get_remediation_proof_service(
    execution_service: ExperimentExecutionService = Depends(  # noqa: B008
        get_experiment_execution_service
    ),
) -> RemediationProofService:
    return RemediationProofService(execution_service)


@router.post(
    "/remediation",
    response_model=RemediationProofResponse,
    status_code=status.HTTP_200_OK,
    summary="Authoritatively verify an allowlisted remediation with the same experiment",
)
def prove_remediation(
    payload: RemediationProofRequest,
    _rate_limit: None = Depends(enforce_proof_rate_limit),  # noqa: B008
    gate: SandboxExecutionGate = Depends(get_sandbox_gate),  # noqa: B008
    service: RemediationProofService = Depends(get_remediation_proof_service),  # noqa: B008
) -> RemediationProofResponse:
    try:
        # The before/after pair owns one logical slot, avoiding nested acquisition deadlocks.
        with gate.slot():
            return RemediationProofResponse(proof=service.prove(payload))
    except RemediationUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
