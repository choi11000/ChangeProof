import asyncio
import logging
import math
import time

from app.fixtures.shiftsafe_fixtures import (
    ControlledPerformanceFixture,
    ControlledWeatherDependency,
    ShiftSafeApp,
)
from app.schemas.execution import ExperimentStepResult, ExperimentStepStatus
from app.schemas.experiment import ExperimentStepType
from app.schemas.performance import (
    PerformanceMetrics,
    PerformanceObservationCode,
    RequestTiming,
)

logger = logging.getLogger(__name__)

# Strict Safety Bounds
MAX_CONCURRENCY = 200
MAX_REQUEST_COUNT = 1000
MAX_DURATION_SECONDS = 30.0


def calculate_percentile(values: list[int], percentile: float) -> int:
    if not values:
        return 0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * (percentile / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    d0 = sorted_vals[int(f)] * (c - k)
    d1 = sorted_vals[int(c)] * (k - f)
    return int(round(d0 + d1))


class PerformanceExperimentExecutor:
    """Executes controlled concurrent peak-load experiments.

    Collects per-request timing, throughput, inflight, and queue wait times.
    Supports in-process ShiftSafe fixtures as well as external HTTP endpoints.
    """

    async def execute_fixture_async(
        self,
        fixture: ControlledPerformanceFixture,
        variant: str = "candidate",
    ) -> list[ExperimentStepResult]:
        step_results: list[ExperimentStepResult] = []
        cfg = fixture.config

        # Clamped safety bounds
        concurrency = min(cfg.concurrency, MAX_CONCURRENCY)
        request_count = min(cfg.request_count, MAX_REQUEST_COUNT)
        timeout_seconds = cfg.timeout_ms / 1000.0

        # Step 1: Initialize Load Environment
        t0 = time.perf_counter()
        weather_dep = ControlledWeatherDependency(
            mode=cfg.downstream_mode,
            latency_ms=cfg.downstream_latency_ms,
            capacity=cfg.downstream_capacity,
        )
        app = ShiftSafeApp(variant=variant, weather_dep=weather_dep)
        step_results.append(
            ExperimentStepResult(
                order=1,
                type=ExperimentStepType.INITIALIZE_LOAD_ENVIRONMENT,
                status=ExperimentStepStatus.PASSED,
                duration_ms=max(1, int((time.perf_counter() - t0) * 1000)),
                message=(
                    f"Initialized ShiftSafe runtime model (variant={variant}, "
                    f"concurrency={concurrency}, downstream_capacity={cfg.downstream_capacity})"
                ),
            )
        )

        # Step 2: Functional Check (Single request verification)
        t_func_start = time.perf_counter()
        func_status = 200
        func_err = None
        try:
            await app.get_dashboard()
        except Exception as e:
            func_status = 500
            func_err = str(e)
        t_func_end = time.perf_counter()
        func_dur = max(1, int((t_func_end - t_func_start) * 1000))

        step_results.append(
            ExperimentStepResult(
                order=2,
                type=ExperimentStepType.FUNCTIONAL_CHECK,
                status=ExperimentStepStatus.PASSED
                if func_status == 200
                else ExperimentStepStatus.FAILED,
                duration_ms=func_dur,
                http_status=func_status,
                message=(
                    f"Single-request functional check: HTTP {func_status} in {func_dur}ms (PASS)"
                    if func_status == 200
                    else f"Functional check failed: {func_err}"
                ),
            )
        )

        # Step 3: Run Concurrent Load
        t_load_start = time.perf_counter()
        timings: list[RequestTiming] = []
        sem = asyncio.Semaphore(concurrency)
        current_inflight = 0
        peak_inflight = 0
        inflight_lock = asyncio.Lock()

        async def worker_request(index: int) -> RequestTiming:
            nonlocal current_inflight, peak_inflight
            async with sem:
                async with inflight_lock:
                    current_inflight += 1
                    if current_inflight > peak_inflight:
                        peak_inflight = current_inflight

                req_start = time.perf_counter()
                status_code = 200
                error_msg = None
                downstream_wait_ms = 0

                try:
                    # Enforce per-request timeout
                    result = await asyncio.wait_for(
                        app.get_dashboard(),
                        timeout=timeout_seconds,
                    )
                    downstream_wait_ms = result.get("downstream_wait_ms", 0)
                except TimeoutError:
                    status_code = 504
                    error_msg = "RequestTimeout"
                except Exception as e:
                    status_code = 500
                    error_msg = str(e)
                finally:
                    req_end = time.perf_counter()
                    async with inflight_lock:
                        current_inflight -= 1

                latency_ms = max(1, int((req_end - req_start) * 1000))
                return RequestTiming(
                    started_at=req_start,
                    finished_at=req_end,
                    latency_ms=latency_ms,
                    status_code=status_code,
                    error=error_msg,
                    downstream_wait_ms=downstream_wait_ms,
                )

        tasks = [worker_request(i) for i in range(request_count)]
        timings = await asyncio.gather(*tasks)
        t_load_end = time.perf_counter()
        total_duration = max(0.001, t_load_end - t_load_start)

        # Calculate metrics
        latencies = [t.latency_ms for t in timings]
        downstream_waits = [t.downstream_wait_ms for t in timings]
        success_count = sum(1 for t in timings if t.status_code == 200)
        timeout_count = sum(1 for t in timings if t.status_code == 504)
        error_count = sum(1 for t in timings if t.status_code >= 500 and t.status_code != 504)

        p50 = calculate_percentile(latencies, 50)
        p95 = calculate_percentile(latencies, 95)
        p99 = calculate_percentile(latencies, 99)
        downstream_p95 = calculate_percentile(downstream_waits, 95)
        throughput = round(len(timings) / total_duration, 1)
        timeout_rate = round(timeout_count / len(timings), 3) if timings else 0.0
        error_rate = round((timeout_count + error_count) / len(timings), 3) if timings else 0.0

        metrics = PerformanceMetrics(
            request_count=len(timings),
            success_count=success_count,
            error_count=error_count,
            timeout_count=timeout_count,
            throughput_rps=throughput,
            p50_ms=p50,
            p95_ms=p95,
            p99_ms=p99,
            max_inflight=peak_inflight,
            downstream_wait_p95_ms=downstream_p95,
            downstream_peak_inflight=weather_dep.peak_inflight,
            timeout_rate=timeout_rate,
            error_rate=error_rate,
        )

        load_step_status = ExperimentStepStatus.PASSED
        step_results.append(
            ExperimentStepResult(
                order=3,
                type=ExperimentStepType.RUN_CONCURRENT_LOAD,
                status=load_step_status,
                duration_ms=int(total_duration * 1000),
                performance_metrics=metrics,
                message=(
                    f"Executed {request_count} requests under {concurrency} concurrency: "
                    f"p50={p50}ms, p95={p95}ms, p99={p99}ms, throughput={throughput} rps, "
                    f"timeouts={timeout_count} ({timeout_rate * 100:.1f}%)"
                ),
            )
        )

        # Step 4: Capture Performance Metrics & Observation
        # Observation is DOWNSTREAM_QUEUE_AMPLIFICATION if downstream wait or p95 explodes
        if variant == "candidate" and (
            p95 >= 1500 or downstream_p95 >= 1000 or timeout_rate > 0.05
        ):
            obs_code = PerformanceObservationCode.DOWNSTREAM_QUEUE_AMPLIFICATION
            obs_msg = (
                f"Bottleneck: downstream wait amplified to {downstream_p95}ms (p95 {p95}ms) "
                f"under {concurrency} concurrent requests"
            )
            step_status = ExperimentStepStatus.FAILED
        else:
            obs_code = PerformanceObservationCode.PERFORMANCE_HEALTHY
            obs_msg = f"Normal performance: p95={p95}ms, timeout_rate={timeout_rate * 100:.1f}%"
            step_status = ExperimentStepStatus.PASSED

        step_results.append(
            ExperimentStepResult(
                order=4,
                type=ExperimentStepType.CAPTURE_PERFORMANCE_METRICS,
                status=step_status,
                duration_ms=5,
                observation_code=obs_code,
                performance_metrics=metrics,
                message=obs_msg,
            )
        )

        return step_results

    def execute_fixture(
        self,
        fixture: ControlledPerformanceFixture,
        variant: str = "candidate",
    ) -> list[ExperimentStepResult]:
        """Synchronous wrapper for async execution."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio

                nest_asyncio.apply()
                return loop.run_until_complete(self.execute_fixture_async(fixture, variant=variant))
            return loop.run_until_complete(self.execute_fixture_async(fixture, variant=variant))
        except RuntimeError:
            return asyncio.run(self.execute_fixture_async(fixture, variant=variant))
