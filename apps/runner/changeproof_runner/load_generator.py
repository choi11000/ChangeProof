import asyncio
import math
import time
from dataclasses import asdict, dataclass
from typing import Any

import httpx

from changeproof_runner.validator import validate_target_url


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


@dataclass
class LocalLoadMetrics:
    request_count: int
    success_count: int
    error_count: int
    timeout_count: int
    throughput_rps: float
    p50_ms: int
    p95_ms: int
    p99_ms: int
    timeout_rate: float
    error_rate: float
    observation: str
    verdict: str
    functional_pass: bool = True
    functional_latency_ms: int = 0


async def run_local_load(
    target_url: str,
    method: str = "GET",
    endpoint: str = "/dashboard",
    concurrency: int = 50,
    request_count: int = 100,
    timeout_seconds: float = 3.0,
) -> LocalLoadMetrics:
    """Execute concurrent HTTP load against a validated local/private target."""
    validated_base = validate_target_url(target_url)
    full_url = f"{validated_base}{endpoint}"

    # Step 1: Functional Check (single request)
    functional_pass = False
    functional_latency_ms = 0
    async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=False) as client:
        try:
            t0 = time.perf_counter()
            f_resp = await client.request(method, full_url)
            t1 = time.perf_counter()
            functional_latency_ms = max(1, int((t1 - t0) * 1000))
            if f_resp.status_code == 200:
                functional_pass = True
        except Exception:
            functional_pass = False

    latencies: list[int] = []
    success_count = 0
    timeout_count = 0
    error_count = 0

    sem = asyncio.Semaphore(concurrency)
    t_start = time.perf_counter()

    async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=False) as client:
        async def worker():
            nonlocal success_count, timeout_count, error_count
            async with sem:
                t0 = time.perf_counter()
                try:
                    resp = await client.request(method, full_url)
                    t1 = time.perf_counter()
                    lat_ms = max(1, int((t1 - t0) * 1000))
                    latencies.append(lat_ms)
                    if resp.status_code == 200:
                        success_count += 1
                    else:
                        error_count += 1
                except httpx.TimeoutException:
                    t1 = time.perf_counter()
                    latencies.append(max(1, int((t1 - t0) * 1000)))
                    timeout_count += 1
                except Exception:
                    t1 = time.perf_counter()
                    latencies.append(max(1, int((t1 - t0) * 1000)))
                    error_count += 1

        tasks = [worker() for _ in range(request_count)]
        await asyncio.gather(*tasks)

    t_end = time.perf_counter()
    duration = max(0.001, t_end - t_start)

    p50 = calculate_percentile(latencies, 50)
    p95 = calculate_percentile(latencies, 95)
    p99 = calculate_percentile(latencies, 99)
    throughput = round(len(latencies) / duration, 1)
    timeout_rate = round(timeout_count / len(latencies), 3) if latencies else 0.0
    error_rate = round((timeout_count + error_count) / len(latencies), 3) if latencies else 0.0

    if p95 >= 1500 or timeout_rate > 0.05:
        obs = "DOWNSTREAM_QUEUE_AMPLIFICATION"
        verdict = "PROVEN_BOTTLENECK"
    else:
        obs = "PERFORMANCE_HEALTHY"
        verdict = "PROVEN_PASS"

    return LocalLoadMetrics(
        request_count=len(latencies),
        success_count=success_count,
        error_count=error_count,
        timeout_count=timeout_count,
        throughput_rps=throughput,
        p50_ms=p50,
        p95_ms=p95,
        p99_ms=p99,
        timeout_rate=timeout_rate,
        error_rate=error_rate,
        observation=obs,
        verdict=verdict,
        functional_pass=functional_pass,
        functional_latency_ms=functional_latency_ms,
    )
