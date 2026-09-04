import math
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from functools import lru_cache

from fastapi import HTTPException, Request, status

from app.core.config import get_settings


@dataclass
class _Window:
    started_at: float
    count: int


class FixedWindowRateLimiter:
    def __init__(
        self, *, window_seconds: int = 60, max_entries: int = 4096, clock=time.monotonic
    ) -> None:
        self.window_seconds = window_seconds
        self.max_entries = max_entries
        self.clock = clock
        self._windows: OrderedDict[str, _Window] = OrderedDict()
        self._lock = threading.Lock()

    def check(self, key: str, limit: int) -> int | None:
        now = self.clock()
        with self._lock:
            self._expire(now)
            window = self._windows.get(key)
            if window is None:
                self._windows[key] = _Window(now, 1)
                self._windows.move_to_end(key)
                while len(self._windows) > self.max_entries:
                    self._windows.popitem(last=False)
                return None
            self._windows.move_to_end(key)
            if window.count >= limit:
                return max(1, math.ceil(self.window_seconds - (now - window.started_at)))
            window.count += 1
            return None

    @property
    def entry_count(self) -> int:
        return len(self._windows)

    def _expire(self, now: float) -> None:
        for key, window in list(self._windows.items()):
            if now - window.started_at >= self.window_seconds:
                self._windows.pop(key, None)


@lru_cache
def get_rate_limiter() -> FixedWindowRateLimiter:
    settings = get_settings()
    return FixedWindowRateLimiter(
        window_seconds=settings.rate_limit_window_seconds,
        max_entries=settings.rate_limit_max_clients,
    )


def client_identity(request: Request) -> str:
    settings = get_settings()
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
        if forwarded:
            return forwarded
    return request.client.host if request.client else "unknown"


def rate_limit_dependency(endpoint: str, setting_name: str):
    def enforce(request: Request) -> None:
        settings = get_settings()
        retry_after = get_rate_limiter().check(
            f"{endpoint}:{client_identity(request)}", getattr(settings, setting_name)
        )
        if retry_after is not None:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Request rate limit exceeded.",
                headers={"Retry-After": str(retry_after)},
            )

    return enforce


enforce_analysis_rate_limit = rate_limit_dependency("analysis", "analysis_rate_limit")
enforce_experiment_rate_limit = rate_limit_dependency("experiment", "experiment_rate_limit")
enforce_proof_rate_limit = rate_limit_dependency("proof", "proof_rate_limit")
