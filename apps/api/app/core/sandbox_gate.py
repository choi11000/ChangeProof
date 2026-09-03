import threading
from contextlib import contextmanager
from functools import lru_cache

from app.core.config import get_settings


class SandboxBusyError(RuntimeError):
    pass


class SandboxExecutionGate:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self._semaphore = threading.BoundedSemaphore(limit)

    @contextmanager
    def slot(self):
        if not self._semaphore.acquire(blocking=False):
            raise SandboxBusyError("Sandbox capacity is busy. Retry later.")
        try:
            yield
        finally:
            self._semaphore.release()


@lru_cache
def get_sandbox_gate() -> SandboxExecutionGate:
    return SandboxExecutionGate(get_settings().max_concurrent_sandbox_runs)
