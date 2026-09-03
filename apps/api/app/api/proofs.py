from fastapi import APIRouter, Depends, HTTPException, status

from app.api.experiments import get_experiment_execution_service
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
    service: RemediationProofService = Depends(get_remediation_proof_service),  # noqa: B008
) -> RemediationProofResponse:
    try:
        return RemediationProofResponse(proof=service.prove(payload))
    except RemediationUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
