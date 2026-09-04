from app.analyzers.experiment_compiler import ExperimentCompiler
from app.analyzers.experiment_verifier import ExperimentVerifier
from app.executors.api_experiment import ApiExperimentExecutor
from app.fixtures.api_fixtures import ControlledApiFixture
from app.schemas.api_contract import ApiChange, ApiChangeType, ApiObservationCode
from app.schemas.dependency import (
    ChangeFact,
    DependencyEvidence,
    DependencyMatchKind,
    DependencyTarget,
    DependencyTargetType,
    SourceScope,
)
from app.schemas.execution import ExperimentStepStatus, ExperimentVerdict
from app.schemas.experiment import ExperimentTemplate
from app.schemas.hypothesis import FailureCategory, FailureHypothesis, HypothesisStatus
from app.schemas.remediation import RemediationStrategy


def test_api_experiment_compilation():
    compiler = ExperimentCompiler()
    change_fact = ChangeFact(
        id="api:GET:/users/{id}:200:application/json:response:email:REMOVE_RESPONSE_FIELD",
        domain="API",
        target=DependencyTarget(
            type=DependencyTargetType.API_FIELD,
            table="",
            path="/users/{id}",
            field="email",
        ),
        api_change=ApiChange(
            change_type=ApiChangeType.REMOVE_RESPONSE_FIELD,
            method="GET",
            path="/users/{id}",
            status_code=200,
            media_type="application/json",
            field_name="email",
            schema_name="User",
            json_pointer="#/components/schemas/User/properties/email",
            destructive=True,
        ),
    )
    evidence = DependencyEvidence(
        id="evi_api_1",
        target=DependencyTarget(
            type=DependencyTargetType.API_FIELD,
            table="",
            path="/users/{id}",
            field="email",
        ),
        path="client/user_client.py",
        line=12,
        excerpt='response["email"].lower()',
        match_kind=DependencyMatchKind.DIRECT_RESPONSE_FIELD_REFERENCE,
        source_scope=SourceScope.APPLICATION,
        changed_in_pull_request=False,
    )

    hypothesis = FailureHypothesis(
        id="hyp_api_1",
        domain="API",
        category=FailureCategory.API_CONTRACT_BREAK,
        title="Removed response field email breaking consumer",
        statement="Consumer client expects response field email",
        change_ids=[change_fact.id],
        evidence_ids=[evidence.id],
        rationale="Client directly reads email from response",
        expected_failure_mode="KeyError on email",
        experiment_template=ExperimentTemplate.API_RESPONSE_FIELD_COMPATIBILITY,
        status=HypothesisStatus.UNVERIFIED,
    )

    plan = compiler.compile(
        hypothesis=hypothesis,
        changes=[change_fact],
        evidence=[evidence],
    )

    assert plan is not None
    assert plan.template == ExperimentTemplate.API_RESPONSE_FIELD_COMPATIBILITY
    assert len(plan.steps) == 4
    step_types = [s.type.value for s in plan.steps]
    assert "PREPARE_API_ENVIRONMENT" in step_types
    assert "SEND_HTTP_REQUEST" in step_types
    assert "PROBE_RESPONSE_FIELD" in step_types
    assert "CAPTURE_API_RESULT" in step_types


def test_api_experiment_executor_failure_and_pass():
    executor = ApiExperimentExecutor()
    fixture = ControlledApiFixture(
        id="api-contract/remove-user-email",
        name="Remove user email response field",
        template=ExperimentTemplate.API_RESPONSE_FIELD_COMPATIBILITY,
        method="GET",
        path="/users/1",
        target_field="email",
        expected_status=200,
        baseline_payload={"id": 1, "email": "alice@example.com"},
        changed_payload={"id": 1},
        remediated_payload={"id": 1, "email": "alice@example.com"},
        remediation_strategy=RemediationStrategy.PRESERVE_API_RESPONSE_FIELD_COMPATIBILITY,
        remediation_description="Preserve email field",
    )

    # 1. Execute against CHANGED subject -> Should fail with API_MISSING_RESPONSE_FIELD
    steps_fail = executor.execute_fixture(fixture, variant="changed")
    assert len(steps_fail) == 4
    probe_fail = steps_fail[2]
    assert probe_fail.status == ExperimentStepStatus.FAILED
    assert probe_fail.observation_code == ApiObservationCode.API_MISSING_RESPONSE_FIELD
    assert probe_fail.json_pointer == "/email"
    assert probe_fail.http_status == 200

    verifier = ExperimentVerifier()
    verdict_fail, msg_fail = verifier.evaluate(
        ExperimentTemplate.API_RESPONSE_FIELD_COMPATIBILITY, steps_fail
    )
    assert verdict_fail == ExperimentVerdict.PROVEN_FAIL
    assert "API_MISSING_RESPONSE_FIELD" in msg_fail

    # 2. Execute against REMEDIATED subject -> Should succeed
    steps_pass = executor.execute_fixture(fixture, variant="remediated")
    assert len(steps_pass) == 4
    probe_pass = steps_pass[2]
    assert probe_pass.status == ExperimentStepStatus.PASSED
    assert probe_pass.observation_code == ApiObservationCode.API_PROBE_PASSED
    assert probe_pass.http_status == 200

    verdict_pass, msg_pass = verifier.evaluate(
        ExperimentTemplate.API_RESPONSE_FIELD_COMPATIBILITY, steps_pass
    )
    assert verdict_pass == ExperimentVerdict.PROVEN_PASS
