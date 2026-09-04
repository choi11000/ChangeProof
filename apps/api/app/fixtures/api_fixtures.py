import hashlib
import json
from dataclasses import dataclass
from typing import Any

from app.schemas.execution import ExperimentVerdict
from app.schemas.experiment import ExperimentTemplate
from app.schemas.remediation import RemediationStrategy


@dataclass(frozen=True)
class ControlledApiFixture:
    id: str
    name: str
    template: ExperimentTemplate
    method: str
    path: str
    target_field: str
    expected_status: int
    baseline_payload: dict[str, Any]
    changed_payload: dict[str, Any]
    remediated_payload: dict[str, Any]
    remediation_strategy: RemediationStrategy
    remediation_description: str
    expected_verdict: ExperimentVerdict = ExperimentVerdict.PROVEN_FAIL

    def compute_contract_digest(self) -> str:
        canonical = json.dumps(
            {
                "domain": "API",
                "template": self.template,
                "method": self.method,
                "path": self.path,
                "target_field": self.target_field,
                "expected_status": self.expected_status,
                "probe": f"READ_RESPONSE_FIELD({self.target_field})",
            },
            sort_keys=True,
        )
        return f"contract_{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]}"

    def compute_subject_digest(self, variant: str = "changed") -> str:
        payload = self.remediated_payload if variant == "remediated" else self.changed_payload
        canonical = json.dumps(
            {
                "variant": variant,
                "payload": payload,
            },
            sort_keys=True,
        )
        return f"subject_api_{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]}"


CONTROLLED_API_FIXTURES: dict[str, ControlledApiFixture] = {
    "api-contract/remove-user-email": ControlledApiFixture(
        id="api-contract/remove-user-email",
        name="Remove user email response field referenced in consumer client",
        template=ExperimentTemplate.API_RESPONSE_FIELD_COMPATIBILITY,
        method="GET",
        path="/users/1",
        target_field="email",
        expected_status=200,
        baseline_payload={"id": 1, "email": "alice@example.com"},
        changed_payload={"id": 1},
        remediated_payload={"id": 1, "email": "alice@example.com"},
        remediation_strategy=RemediationStrategy.PRESERVE_API_RESPONSE_FIELD_COMPATIBILITY,
        remediation_description=(
            "Preserve the removed 'email' response field during the client compatibility window."
        ),
        expected_verdict=ExperimentVerdict.PROVEN_FAIL,
    )
}


def get_controlled_api_fixture(fixture_id: str) -> ControlledApiFixture | None:
    return CONTROLLED_API_FIXTURES.get(fixture_id)
