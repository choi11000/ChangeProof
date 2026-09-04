import asyncio
import hashlib
import logging
import time
from collections import OrderedDict
from collections.abc import Callable

from app.clients.openai_client import (
    FAILURE_HYPOTHESIS_PROMPT_VERSION,
    FailurePlanningContext,
    HypothesisGenerationResult,
    HypothesisGenerator,
)
from app.schemas.ai import AIUsageMetadata
from app.schemas.experiment import ExperimentTemplate

logger = logging.getLogger(__name__)


class CachedHypothesisGenerator:
    """Bounded TTL cache with per-fingerprint async single-flight suppression."""

    def __init__(
        self,
        upstream: HypothesisGenerator,
        *,
        model: str,
        prompt_version: str = FAILURE_HYPOTHESIS_PROMPT_VERSION,
        max_entries: int = 256,
        ttl_seconds: float = 3600,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.upstream = upstream
        self.model = model
        self.prompt_version = prompt_version
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self.clock = clock
        self._cache: OrderedDict[str, tuple[float, HypothesisGenerationResult]] = OrderedDict()
        self._inflight: dict[str, asyncio.Task[HypothesisGenerationResult]] = {}
        self._lock = asyncio.Lock()

    @property
    def is_configured(self) -> bool:
        return not hasattr(self.upstream, "is_configured") or bool(self.upstream.is_configured)

    def fingerprint(self, context: FailurePlanningContext) -> str:
        payload = "\n".join(
            (
                context.head_sha,
                self.model,
                self.prompt_version,
                context.model_dump_json(exclude={"head_sha"}),
            )
        )
        return f"planning_{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"

    async def generate(self, context: FailurePlanningContext) -> HypothesisGenerationResult:
        fingerprint = self.fingerprint(context)
        now = self.clock()
        async with self._lock:
            self._expire(now)
            cached = self._cache.get(fingerprint)
            if cached is not None:
                self._cache.move_to_end(fingerprint)
                logger.info(
                    "ai_planning_cache_hit",
                    extra={
                        "model": self.model,
                        "prompt_version": self.prompt_version,
                        "fingerprint": fingerprint,
                    },
                )
                return cached[1].model_copy(
                    update={"usage": cached[1].usage.model_copy(update={"cache_hit": True})}
                )
            task = self._inflight.get(fingerprint)
            owner = task is None
            if task is None:
                task = asyncio.create_task(self._call_upstream(context, fingerprint))
                self._inflight[fingerprint] = task
                task.add_done_callback(
                    lambda completed, key=fingerprint, source=context: self._finalize_task(
                        key, source, completed
                    )
                )
        try:
            result = await asyncio.shield(task)
            if owner and self._is_cacheable(result, context):
                async with self._lock:
                    self._cache[fingerprint] = (self.clock() + self.ttl_seconds, result)
                    self._cache.move_to_end(fingerprint)
                    while len(self._cache) > self.max_entries:
                        self._cache.popitem(last=False)
            return result.model_copy(
                update={"usage": result.usage.model_copy(update={"cache_hit": not owner})}
            )
        finally:
            if owner:
                async with self._lock:
                    if self._inflight.get(fingerprint) is task:
                        self._inflight.pop(fingerprint, None)

    def _finalize_task(
        self,
        fingerprint: str,
        context: FailurePlanningContext,
        task: asyncio.Task[HypothesisGenerationResult],
    ) -> None:
        if not task.cancelled() and task.exception() is None:
            result = task.result()
            if self._is_cacheable(result, context):
                self._cache[fingerprint] = (self.clock() + self.ttl_seconds, result)
                self._cache.move_to_end(fingerprint)
                while len(self._cache) > self.max_entries:
                    self._cache.popitem(last=False)
        if self._inflight.get(fingerprint) is task:
            self._inflight.pop(fingerprint, None)

    async def _call_upstream(
        self, context: FailurePlanningContext, fingerprint: str
    ) -> HypothesisGenerationResult:
        raw = await self.upstream.generate(context)
        if isinstance(raw, HypothesisGenerationResult):
            usage = raw.usage.model_copy(
                update={
                    "model": self.model,
                    "prompt_version": self.prompt_version,
                    "fingerprint": fingerprint,
                    "context": context.stats,
                }
            )
            return raw.model_copy(update={"usage": usage})
        return HypothesisGenerationResult(
            proposal=raw,
            usage=AIUsageMetadata(
                model=self.model,
                prompt_version=self.prompt_version,
                fingerprint=fingerprint,
                context=context.stats,
            ),
        )

    @staticmethod
    def _is_cacheable(result: HypothesisGenerationResult, context: FailurePlanningContext) -> bool:
        change_ids = {item.id for item in context.changes}
        evidence_ids = {item.id for item in context.evidence}
        templates = set(ExperimentTemplate)
        return all(
            hypothesis.change_ids
            and set(hypothesis.change_ids) <= change_ids
            and set(hypothesis.evidence_ids) <= evidence_ids
            and hypothesis.experiment_template in templates
            for hypothesis in result.proposal.hypotheses
        )

    def _expire(self, now: float) -> None:
        for key, (expires_at, _) in list(self._cache.items()):
            if expires_at <= now:
                self._cache.pop(key, None)
