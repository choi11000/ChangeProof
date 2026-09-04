import asyncio

from app.executors.performance_experiment import (
    PerformanceExperimentExecutor,
    calculate_percentile,
)
from app.fixtures.shiftsafe_fixtures import (
    ControlledPerformanceFixture,
    DownstreamMode,
)
from app.schemas.execution import ExperimentStepStatus
from app.schemas.experiment import ExperimentStepType, ExperimentTemplate
from app.schemas.performance import (
    PerformanceExperimentConfig,
    PerformanceObservationCode,
)
from app.schemas.remediation import RemediationStrategy


def test_calculate_percentile():
    values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    assert calculate_percentile(values, 50) == 55
    assert calculate_percentile(values, 95) == 96
    assert calculate_percentile([], 95) == 0


def test_performance_executor_runs_fast_fixture():
    fixture = ControlledPerformanceFixture(
        id="test/fast",
        name="Test Fast",
        template=ExperimentTemplate.EXTERNAL_DEPENDENCY_LATENCY,
        method="GET",
        path="/dashboard",
        config=PerformanceExperimentConfig(
            concurrency=5,
            request_count=10,
            timeout_ms=1000,
            downstream_mode=DownstreamMode.FAST,
            downstream_latency_ms=10,
            downstream_capacity=10,
        ),
        remediation_strategy=RemediationStrategy.CACHE_AND_COALESCE_EXTERNAL_CALL,
        remediation_description="Test remediation",
    )

    executor = PerformanceExperimentExecutor()
    results = asyncio.run(executor.execute_fixture_async(fixture, variant="remediated"))

    assert len(results) == 4
    assert results[0].type == ExperimentStepType.INITIALIZE_LOAD_ENVIRONMENT
    assert results[0].status == ExperimentStepStatus.PASSED

    assert results[1].type == ExperimentStepType.FUNCTIONAL_CHECK
    assert results[1].status == ExperimentStepStatus.PASSED

    assert results[2].type == ExperimentStepType.RUN_CONCURRENT_LOAD
    assert results[2].status == ExperimentStepStatus.PASSED
    assert results[2].performance_metrics is not None
    assert results[2].performance_metrics.request_count == 10

    assert results[3].type == ExperimentStepType.CAPTURE_PERFORMANCE_METRICS
    assert results[3].status == ExperimentStepStatus.PASSED
    assert results[3].observation_code == PerformanceObservationCode.PERFORMANCE_HEALTHY


def test_performance_executor_synchronous_wrapper():
    fixture = ControlledPerformanceFixture(
        id="test/sync",
        name="Test Sync",
        template=ExperimentTemplate.EXTERNAL_DEPENDENCY_LATENCY,
        method="GET",
        path="/dashboard",
        config=PerformanceExperimentConfig(
            concurrency=2,
            request_count=4,
            timeout_ms=1000,
            downstream_mode=DownstreamMode.FAST,
            downstream_latency_ms=5,
            downstream_capacity=5,
        ),
        remediation_strategy=RemediationStrategy.CACHE_AND_COALESCE_EXTERNAL_CALL,
        remediation_description="Test sync remediation",
    )
    executor = PerformanceExperimentExecutor()
    results = executor.execute_fixture(fixture, variant="baseline")
    assert len(results) == 4
    assert results[3].observation_code == PerformanceObservationCode.PERFORMANCE_HEALTHY
