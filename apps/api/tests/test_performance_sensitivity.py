from app.executors.performance_experiment import PerformanceExperimentExecutor
from app.fixtures.shiftsafe_fixtures import ControlledPerformanceFixture
from app.schemas.experiment import ExperimentTemplate
from app.schemas.performance import PerformanceExperimentConfig
from app.schemas.remediation import RemediationStrategy


def make_fixture(fixture_id: str, cfg: PerformanceExperimentConfig) -> ControlledPerformanceFixture:
    return ControlledPerformanceFixture(
        id=fixture_id,
        name=fixture_id,
        template=ExperimentTemplate.EXTERNAL_DEPENDENCY_LATENCY,
        method="GET",
        path="/dashboard",
        config=cfg,
        remediation_strategy=RemediationStrategy.CACHE_AND_COALESCE_EXTERNAL_CALL,
        remediation_description="Apply cache and coalescing",
    )


def test_downstream_latency_sensitivity():
    """Verify that increasing downstream latency proportionally increases p95 response time."""
    executor = PerformanceExperimentExecutor()

    # Fast: 100ms
    cfg_fast = PerformanceExperimentConfig(
        concurrency=15, request_count=30, downstream_latency_ms=100, timeout_ms=3000
    )
    fix_fast = make_fixture("test/fast", cfg_fast)

    # Medium: 500ms
    cfg_med = PerformanceExperimentConfig(
        concurrency=15, request_count=30, downstream_latency_ms=500, timeout_ms=3000
    )
    fix_med = make_fixture("test/med", cfg_med)

    # Slow: 1000ms
    cfg_slow = PerformanceExperimentConfig(
        concurrency=15, request_count=30, downstream_latency_ms=1000, timeout_ms=3000
    )
    fix_slow = make_fixture("test/slow", cfg_slow)

    res_fast = executor.execute_fixture(fix_fast, variant="candidate")
    res_med = executor.execute_fixture(fix_med, variant="candidate")
    res_slow = executor.execute_fixture(fix_slow, variant="candidate")

    metrics_fast = [s.performance_metrics for s in res_fast if s.performance_metrics][0]
    metrics_med = [s.performance_metrics for s in res_med if s.performance_metrics][0]
    metrics_slow = [s.performance_metrics for s in res_slow if s.performance_metrics][0]

    # Monotonic ordering of latency
    assert metrics_slow.p95_ms > metrics_med.p95_ms > metrics_fast.p95_ms


def test_capacity_queue_sensitivity():
    """Verify that lower downstream capacity produces more downstream queue wait time."""
    executor = PerformanceExperimentExecutor()

    # Low capacity (3 workers) -> high wait time
    cfg_low_cap = PerformanceExperimentConfig(
        concurrency=20, request_count=40, downstream_latency_ms=150, downstream_capacity=3
    )
    fix_low_cap = make_fixture("test/low_cap", cfg_low_cap)

    # High capacity (20 workers) -> minimal wait time
    cfg_high_cap = PerformanceExperimentConfig(
        concurrency=20, request_count=40, downstream_latency_ms=150, downstream_capacity=20
    )
    fix_high_cap = make_fixture("test/high_cap", cfg_high_cap)

    res_low = executor.execute_fixture(fix_low_cap, variant="candidate")
    res_high = executor.execute_fixture(fix_high_cap, variant="candidate")

    metrics_low = [s.performance_metrics for s in res_low if s.performance_metrics][0]
    metrics_high = [s.performance_metrics for s in res_high if s.performance_metrics][0]

    assert metrics_low.downstream_wait_p95_ms > metrics_high.downstream_wait_p95_ms


def test_concurrency_queue_pressure():
    """Verify that higher concurrency increases p95 latency and queue pressure."""
    executor = PerformanceExperimentExecutor()

    # Low concurrency: 3 users against capacity 5 -> minimal queue
    cfg_low = PerformanceExperimentConfig(
        concurrency=3, request_count=15, downstream_latency_ms=150, downstream_capacity=5
    )
    fix_low = make_fixture("test/low_c", cfg_low)

    # High concurrency: 25 users against capacity 5 -> heavy queue
    cfg_high = PerformanceExperimentConfig(
        concurrency=25, request_count=50, downstream_latency_ms=150, downstream_capacity=5
    )
    fix_high = make_fixture("test/high_c", cfg_high)

    res_low = executor.execute_fixture(fix_low, variant="candidate")
    res_high = executor.execute_fixture(fix_high, variant="candidate")

    metrics_low = [s.performance_metrics for s in res_low if s.performance_metrics][0]
    metrics_high = [s.performance_metrics for s in res_high if s.performance_metrics][0]

    assert metrics_high.p95_ms > metrics_low.p95_ms
    assert metrics_high.downstream_wait_p95_ms >= metrics_low.downstream_wait_p95_ms


def test_baseline_candidate_remediated_real_execution():
    """Verify that Baseline, Candidate, and Remediated are ALL executed under the same contract."""
    executor = PerformanceExperimentExecutor()

    cfg = PerformanceExperimentConfig(
        concurrency=20, request_count=40, downstream_latency_ms=200, downstream_capacity=4
    )
    fixture = make_fixture("test/shiftsafe_all", cfg)

    # 1. Baseline Run
    res_base = executor.execute_fixture(fixture, variant="baseline")
    m_base = [s.performance_metrics for s in res_base if s.performance_metrics][0]
    assert m_base.timeout_rate == 0.0
    assert m_base.downstream_wait_p95_ms == 0
    assert m_base.p95_ms < 150

    # 2. Candidate Run
    res_cand = executor.execute_fixture(fixture, variant="candidate")
    m_cand = [s.performance_metrics for s in res_cand if s.performance_metrics][0]
    assert m_cand.p95_ms > m_base.p95_ms * 2
    assert m_cand.downstream_wait_p95_ms > 0

    # 3. Remediated Run
    res_rem = executor.execute_fixture(fixture, variant="remediated")
    m_rem = [s.performance_metrics for s in res_rem if s.performance_metrics][0]
    assert m_rem.timeout_rate == 0.0
    assert m_rem.p95_ms < m_cand.p95_ms
    assert m_rem.throughput_rps > m_cand.throughput_rps
