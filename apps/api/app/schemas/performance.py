from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, Field


class PerformanceChangeType(StrEnum):
    EXTERNAL_HTTP_CALL_ADDED = "EXTERNAL_HTTP_CALL_ADDED"
    EXTERNAL_CALL_ADDED_TO_REQUEST_PATH = "EXTERNAL_CALL_ADDED_TO_REQUEST_PATH"
    EXTERNAL_CALL_TIMEOUT_MISSING = "EXTERNAL_CALL_TIMEOUT_MISSING"
    EXTERNAL_CALL_CACHE_NOT_DETECTED = "EXTERNAL_CALL_CACHE_NOT_DETECTED"


class PerformanceObservationCode(StrEnum):
    DOWNSTREAM_QUEUE_AMPLIFICATION = "DOWNSTREAM_QUEUE_AMPLIFICATION"
    PERFORMANCE_LATENCY_REGRESSION = "PERFORMANCE_LATENCY_REGRESSION"
    PERFORMANCE_TIMEOUT_RATE = "PERFORMANCE_TIMEOUT_RATE"
    PERFORMANCE_HEALTHY = "PERFORMANCE_HEALTHY"


class DownstreamMode(StrEnum):
    FAST = "FAST"
    SLOW = "SLOW"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


class PerformanceChange(BaseModel):
    change_type: PerformanceChangeType
    endpoint: str
    method: str = "GET"
    source_file: str
    line: int
    downstream_symbol: str
    changed_in_pull_request: bool = True
    context_snippet: str = ""


class PerformanceMetrics(BaseModel):
    request_count: int = Field(default=0, ge=0)
    success_count: int = Field(default=0, ge=0)
    error_count: int = Field(default=0, ge=0)
    timeout_count: int = Field(default=0, ge=0)
    throughput_rps: float = Field(default=0.0, ge=0.0)
    p50_ms: int = Field(default=0, ge=0)
    p95_ms: int = Field(default=0, ge=0)
    p99_ms: int = Field(default=0, ge=0)
    max_inflight: int = Field(default=0, ge=0)
    downstream_wait_p95_ms: int = Field(default=0, ge=0)
    downstream_peak_inflight: int = Field(default=0, ge=0)
    timeout_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    error_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    regression_ratio: float | None = Field(default=None, ge=0.0)


class PerformanceExperimentConfig(BaseModel):
    concurrency: int = Field(default=150, ge=1, le=200)
    request_count: int = Field(default=300, ge=1, le=1000)
    warmup_requests: int = Field(default=10, ge=0, le=100)
    timeout_ms: int = Field(default=3000, ge=100, le=30000)
    downstream_mode: DownstreamMode = DownstreamMode.SLOW
    downstream_latency_ms: int = Field(default=700, ge=0, le=10000)
    downstream_capacity: int = Field(default=10, ge=1, le=100)


@dataclass(frozen=True)
class RequestTiming:
    started_at: float
    finished_at: float
    latency_ms: int
    status_code: int
    error: str | None = None
    downstream_wait_ms: int = 0
