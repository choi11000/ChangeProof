from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.api.proofs import get_remediation_proof_service
from app.main import app
from app.services.remediation_proof_service import (
    RemediationProofService,
    RemediationUnavailableError,
)

client = TestClient(app)


def test_remediation_proof_api_rejects_client_evidence() -> None:
    response = client.post(
        "/api/v1/proofs/remediation",
        json={"fixture_id": "risky-saas/drop-legacy-status", "before_verdict": "PROVEN_FAIL"},
    )
    assert response.status_code == 422


def test_remediation_proof_api_reports_unavailable() -> None:
    service = MagicMock(spec=RemediationProofService)
    service.prove.side_effect = RemediationUnavailableError("No remediation required")
    app.dependency_overrides[get_remediation_proof_service] = lambda: service
    try:
        response = client.post(
            "/api/v1/proofs/remediation",
            json={"fixture_id": "risky-saas/safe-additive"},
        )
        assert response.status_code == 400
        assert "No remediation required" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
