import pytest
from app.analyzers.experiment_verifier import ExperimentVerifier
from app.core.config import Settings
from app.fixtures.shiftsafe_fixtures import (
    ControlledPerformanceFixture,
    DownstreamMode,
    get_controlled_performance_fixture,
)
from app.schemas.dependency import ChangeFact
from app.schemas.execution import (
    ExecuteExperimentRequest,
    ExperimentStepResult,
    ExperimentStepStatus,
    ExperimentVerdict,
)
from app.schemas.experiment import ExperimentStepType, ExperimentTemplate
from app.schemas.github import GitHubRepositoryRef, PullRequestMetadata
from app.schemas.performance import (
    PerformanceChange,
    PerformanceChangeType,
    PerformanceExperimentConfig,
    PerformanceMetrics,
    PerformanceObservationCode,
)
from app.schemas.remediation import (
    RemediationProofRequest,
    RemediationProofVerdict,
    RemediationStrategy,
)
from app.services.controlled_demo_policy import ControlledDemoPolicy
from app.services.experiment_execution_service import ExperimentExecutionService
from app.services.remediation_proof_service import RemediationProofService


def test_experiment_verifier_performance_bottleneck():
    verifier = ExperimentVerifier()
    step_results = [
        ExperimentStepResult(
            order=1,
            type=ExperimentStepType.INITIALIZE_LOAD_ENVIRONMENT,
            status=ExperimentStepStatus.PASSED,
            duration_ms=5,
        ),
        ExperimentStepResult(
            order=2,
            type=ExperimentStepType.RUN_CONCURRENT_LOAD,
            status=ExperimentStepStatus.PASSED,
            duration_ms=2000,
        ),
        ExperimentStepResult(
            order=3,
            type=ExperimentStepType.CAPTURE_PERFORMANCE_METRICS,
            status=ExperimentStepStatus.FAILED,
            duration_ms=5,
            observation_code=PerformanceObservationCode.DOWNSTREAM_QUEUE_AMPLIFICATION,
        ),
    ]

    verdict, summary = verifier.evaluate(
        ExperimentTemplate.EXTERNAL_DEPENDENCY_LATENCY, step_results
    )
    assert verdict == ExperimentVerdict.PROVEN_FAIL
    assert "queue amplification" in summary.lower()


def test_experiment_verifier_performance_healthy():
    verifier = ExperimentVerifier()
    step_results = [
        ExperimentStepResult(
            order=1,
            type=ExperimentStepType.INITIALIZE_LOAD_ENVIRONMENT,
            status=ExperimentStepStatus.PASSED,
            duration_ms=5,
        ),
        ExperimentStepResult(
            order=2,
            type=ExperimentStepType.RUN_CONCURRENT_LOAD,
            status=ExperimentStepStatus.PASSED,
            duration_ms=500,
        ),
        ExperimentStepResult(
            order=3,
            type=ExperimentStepType.CAPTURE_PERFORMANCE_METRICS,
            status=ExperimentStepStatus.PASSED,
            duration_ms=5,
            observation_code=PerformanceObservationCode.PERFORMANCE_HEALTHY,
        ),
    ]

    verdict, summary = verifier.evaluate(
        ExperimentTemplate.EXTERNAL_DEPENDENCY_LATENCY, step_results
    )
    assert verdict == ExperimentVerdict.PROVEN_PASS
    assert "passed" in summary.lower()


def test_experiment_verifier_performance_missing_steps():
    verifier = ExperimentVerifier()
    step_results = [
        ExperimentStepResult(
            order=1,
            type=ExperimentStepType.INITIALIZE_LOAD_ENVIRONMENT,
            status=ExperimentStepStatus.PASSED,
            duration_ms=5,
        ),
    ]

    verdict, summary = verifier.evaluate(
        ExperimentTemplate.EXTERNAL_DEPENDENCY_LATENCY, step_results
    )
    assert verdict == ExperimentVerdict.INCONCLUSIVE


def test_experiment_execution_service_and_remediation_proof():
    execution_service = ExperimentExecutionService()
    remediation_service = RemediationProofService(execution_service)

    # 1. Execute candidate run
    run = execution_service.execute(
        ExecuteExperimentRequest(fixture_id="shiftsafe/dashboard-weather-dependency")
    )
    assert run.domain == "PERFORMANCE"
    assert run.template == ExperimentTemplate.EXTERNAL_DEPENDENCY_LATENCY
    assert run.experiment_contract_digest.startswith("perf_contract_")
    assert run.performance_metrics is not None

    # 2. Execute remediation proof
    proof = remediation_service.prove(
        RemediationProofRequest(fixture_id="shiftsafe/dashboard-weather-dependency")
    )
    assert proof.domain == "PERFORMANCE"
    assert proof.same_experiment is True
    assert proof.subject_changed is True
    assert proof.verdict == RemediationProofVerdict.PROVEN_FIXED
    assert proof.strategy == RemediationStrategy.CACHE_AND_COALESCE_EXTERNAL_CALL


def test_controlled_demo_policy_performance_repo():
    settings = Settings(
        controlled_perf_demo_repository="choi11000/changeproof-load-demo",
        controlled_perf_demo_pr=1,
        controlled_perf_demo_head_sha="a1b2c3d4e5f67890abcdef1234567890abcdef12",
    )
    policy = ControlledDemoPolicy(settings)

    repo = GitHubRepositoryRef(owner="choi11000", repo="changeproof-load-demo")
    metadata = PullRequestMetadata(
        repository="choi11000/changeproof-load-demo",
        number=1,
        title="Add weather client to dashboard",
        state="open",
        base_branch="main",
        head_branch="demo/weather-dependency",
        head_sha="a1b2c3d4e5f67890abcdef1234567890abcdef12",
        base_sha="0000000000000000000000000000000000000000",
        changed_files=1,
        html_url="https://github.com/choi11000/changeproof-load-demo/pull/1",
    )
    fact = ChangeFact(
        id="perf_1",
        domain="PERFORMANCE",
        performance_change=PerformanceChange(
            change_type=PerformanceChangeType.EXTERNAL_CALL_ADDED_TO_REQUEST_PATH,
            endpoint="GET /dashboard",
            source_file="app/dashboard.py",
            line=20,
            downstream_symbol="weather_client.get_current",
        ),
    )

    decision = policy.evaluate(repo, metadata, [fact])
    assert decision.allowed is True
    assert decision.fixture_id == "shiftsafe/dashboard-weather-dependency"
