import asyncio
import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any

from app.schemas.execution import ExperimentVerdict
from app.schemas.experiment import ExperimentTemplate
from app.schemas.performance import DownstreamMode, PerformanceExperimentConfig
from app.schemas.remediation import RemediationStrategy


class ControlledWeatherDependency:
    """Server-owned controlled downstream weather service model.

    Supports deterministic modes:
    - FAST: ~50ms
    - SLOW: 600-1000ms (default 700ms)
    - TIMEOUT: sleep beyond request timeout
    - ERROR: raise HTTP 500 error
    Bounded capacity: Semaphore(capacity) simulating limited outbound connections/workers.
    """

    def __init__(self, mode: DownstreamMode = DownstreamMode.SLOW, latency_ms: int = 700, capacity: int = 10):
        self.mode = mode
        self.latency_ms = latency_ms
        self.capacity = capacity
        self._semaphore = asyncio.Semaphore(capacity)
        self.current_inflight = 0
        self.peak_inflight = 0

    async def get_current_weather(self) -> dict[str, Any]:
        t0 = time.perf_counter()
        async with self._semaphore:
            self.current_inflight += 1
            if self.current_inflight > self.peak_inflight:
                self.peak_inflight = self.current_inflight

            wait_ms = int((time.perf_counter() - t0) * 1000)

            try:
                if self.mode == DownstreamMode.ERROR:
                    raise RuntimeError("Downstream weather service HTTP 503 unavailable")

                if self.mode == DownstreamMode.TIMEOUT:
                    await asyncio.sleep(5.0)
                    return {"temp_c": 22.5, "condition": "Sunny", "downstream_wait_ms": wait_ms}

                duration_s = (50 if self.mode == DownstreamMode.FAST else self.latency_ms) / 1000.0
                await asyncio.sleep(duration_s)

                return {
                    "temp_c": 21.0,
                    "condition": "Cloudy",
                    "humidity": 65,
                    "downstream_wait_ms": wait_ms,
                }
            finally:
                self.current_inflight -= 1


class ShiftSafeApp:
    """In-process ShiftSafe demo application supporting Baseline, Candidate, and Remediated subjects."""

    def __init__(self, variant: str = "candidate", weather_dep: ControlledWeatherDependency | None = None):
        self.variant = variant
        self.weather_dep = weather_dep or ControlledWeatherDependency()
        # Remediated cache state
        self._cache: dict[str, Any] | None = None
        self._cache_expires_at: float = 0.0
        self._coalescing_lock = asyncio.Lock()

    async def get_dashboard(self) -> dict[str, Any]:
        # Fast local worker summary (in-memory / local DB)
        workers_summary = {
            "active_workers": 142,
            "on_shift": 128,
            "safety_alerts": 0,
            "status": "HEALTHY",
        }

        if self.variant == "baseline":
            # No downstream call on request path
            return {"dashboard": workers_summary, "downstream_wait_ms": 0}

        if self.variant == "candidate":
            # Risky change: synchronous/awaited downstream call on EVERY request
            weather = await self.weather_dep.get_current_weather()
            return {
                "dashboard": workers_summary,
                "weather": weather,
                "downstream_wait_ms": weather.get("downstream_wait_ms", 0),
            }

        if self.variant == "remediated":
            # Remediation: Cache + Single-flight coalescing + fallback
            now = time.monotonic()
            if self._cache and now < self._cache_expires_at:
                return {
                    "dashboard": workers_summary,
                    "weather": self._cache,
                    "downstream_wait_ms": 0,
                    "cache_hit": True,
                }

            async with self._coalescing_lock:
                now = time.monotonic()
                if self._cache and now < self._cache_expires_at:
                    return {
                        "dashboard": workers_summary,
                        "weather": self._cache,
                        "downstream_wait_ms": 0,
                        "cache_hit": True,
                    }

                try:
                    # Bounded timeout for downstream call
                    weather = await asyncio.wait_for(
                        self.weather_dep.get_current_weather(),
                        timeout=1.5,
                    )
                    self._cache = weather
                    self._cache_expires_at = now + 10.0  # 10s TTL
                    return {
                        "dashboard": workers_summary,
                        "weather": weather,
                        "downstream_wait_ms": weather.get("downstream_wait_ms", 0),
                        "cache_hit": False,
                    }
                except Exception:
                    # Fallback to default / stale data
                    fallback_weather = {"temp_c": 20.0, "condition": "Unknown", "fallback": True}
                    return {
                        "dashboard": workers_summary,
                        "weather": fallback_weather,
                        "downstream_wait_ms": 0,
                        "fallback": True,
                    }

        raise ValueError(f"Unknown subject variant: {self.variant}")


@dataclass(frozen=True)
class ControlledPerformanceFixture:
    id: str
    name: str
    template: ExperimentTemplate
    method: str
    path: str
    config: PerformanceExperimentConfig
    remediation_strategy: RemediationStrategy
    remediation_description: str
    expected_verdict: ExperimentVerdict = ExperimentVerdict.PROVEN_BOTTLENECK

    def compute_contract_digest(self) -> str:
        canonical = json.dumps(
            {
                "domain": "PERFORMANCE",
                "template": self.template,
                "method": self.method,
                "path": self.path,
                "concurrency": self.config.concurrency,
                "request_count": self.config.request_count,
                "downstream_mode": self.config.downstream_mode,
                "downstream_latency_ms": self.config.downstream_latency_ms,
                "downstream_capacity": self.config.downstream_capacity,
                "timeout_ms": self.config.timeout_ms,
            },
            sort_keys=True,
        )
        return f"perf_contract_{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]}"

    def compute_subject_digest(self, variant: str = "candidate") -> str:
        canonical = json.dumps(
            {
                "fixture_id": self.id,
                "variant": variant,
                "endpoint": f"{self.method} {self.path}",
                "implementation": (
                    "local_summary_only"
                    if variant == "baseline"
                    else (
                        "synchronous_weather_call_per_request"
                        if variant == "candidate"
                        else "cached_coalesced_weather_call"
                    )
                ),
            },
            sort_keys=True,
        )
        return f"perf_subject_{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]}"


CONTROLLED_PERFORMANCE_FIXTURES: dict[str, ControlledPerformanceFixture] = {
    "shiftsafe/dashboard-weather-dependency": ControlledPerformanceFixture(
        id="shiftsafe/dashboard-weather-dependency",
        name="ShiftSafe Workforce Safety Dashboard - External Weather API on hot request path",
        template=ExperimentTemplate.EXTERNAL_DEPENDENCY_LATENCY,
        method="GET",
        path="/dashboard",
        config=PerformanceExperimentConfig(
            concurrency=150,
            request_count=300,
            warmup_requests=10,
            timeout_ms=3000,
            downstream_mode=DownstreamMode.SLOW,
            downstream_latency_ms=700,
            downstream_capacity=10,
        ),
        remediation_strategy=RemediationStrategy.CACHE_AND_COALESCE_EXTERNAL_CALL,
        remediation_description=(
            "Apply short-TTL response cache (10s), single-flight request coalescing, "
            "and a 1.5s client timeout with stale fallback on external weather dependency."
        ),
        expected_verdict=ExperimentVerdict.PROVEN_BOTTLENECK,
    )
}


def get_controlled_performance_fixture(fixture_id: str) -> ControlledPerformanceFixture | None:
    return CONTROLLED_PERFORMANCE_FIXTURES.get(fixture_id)
