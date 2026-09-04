import asyncio

import pytest

from app.clients.openai_client import FailurePlanningContext, OpenAITimeoutError
from app.schemas.ai import PlanningContextStats
from app.schemas.experiment import ExperimentTemplate
from app.schemas.hypothesis import FailureCategory, FailureHypothesis, HypothesisProposalResult
from app.services.ai_planning_cache import CachedHypothesisGenerator


def context(head_sha: str = "head") -> FailurePlanningContext:
    return FailurePlanningContext(
        head_sha=head_sha,
        stats=PlanningContextStats(
            available_changes=0,
            used_changes=0,
            available_evidence=0,
            used_evidence=0,
            available_warnings=0,
            used_warnings=0,
        ),
    )


class Generator:
    is_configured = True

    def __init__(self, error: Exception | None = None) -> None:
        self.calls = 0
        self.error = error

    async def generate(self, _context):
        self.calls += 1
        await asyncio.sleep(0.01)
        if self.error:
            raise self.error
        return HypothesisProposalResult(hypotheses=[])


def test_repeated_request_hits_cache_and_head_changes_miss() -> None:
    async def scenario():
        upstream = Generator()
        cached = CachedHypothesisGenerator(upstream, model="model")
        first = await cached.generate(context())
        second = await cached.generate(context())
        third = await cached.generate(context("other"))
        assert first.usage.cache_hit is False
        assert second.usage.cache_hit is True
        assert third.usage.cache_hit is False
        assert upstream.calls == 2

    asyncio.run(scenario())


def test_fingerprint_changes_with_model_and_prompt_version() -> None:
    upstream = Generator()
    one = CachedHypothesisGenerator(upstream, model="one", prompt_version="v1")
    two = CachedHypothesisGenerator(upstream, model="two", prompt_version="v1")
    three = CachedHypothesisGenerator(upstream, model="one", prompt_version="v2")
    fingerprints = {
        one.fingerprint(context()),
        two.fingerprint(context()),
        three.fingerprint(context()),
    }
    assert len(fingerprints) == 3


def test_expired_entry_misses_and_failures_are_not_cached() -> None:
    async def scenario():
        now = [0.0]
        upstream = Generator()
        cached = CachedHypothesisGenerator(
            upstream, model="model", ttl_seconds=10, clock=lambda: now[0]
        )
        await cached.generate(context())
        now[0] = 11
        await cached.generate(context())
        assert upstream.calls == 2

        failing = Generator(OpenAITimeoutError("timeout"))
        failure_cache = CachedHypothesisGenerator(failing, model="model")
        for _ in range(2):
            with pytest.raises(OpenAITimeoutError):
                await failure_cache.generate(context())
        assert failing.calls == 2

    asyncio.run(scenario())


def test_concurrent_duplicates_share_one_request() -> None:
    async def scenario():
        upstream = Generator()
        cached = CachedHypothesisGenerator(upstream, model="model")
        results = await asyncio.gather(*(cached.generate(context()) for _ in range(5)))
        assert upstream.calls == 1
        assert sum(result.usage.cache_hit for result in results) == 4

    asyncio.run(scenario())


def test_domain_invalid_structured_output_is_not_cached() -> None:
    class InvalidGenerator(Generator):
        async def generate(self, _context):
            self.calls += 1
            return HypothesisProposalResult(
                hypotheses=[
                    FailureHypothesis(
                        id="invalid",
                        category=FailureCategory.OTHER,
                        title="Invalid",
                        statement="Unknown evidence",
                        change_ids=["unknown-change"],
                        evidence_ids=["unknown-evidence"],
                        rationale="invalid",
                        expected_failure_mode="none",
                        experiment_template=ExperimentTemplate.MIGRATION_APPLY,
                    )
                ]
            )

    async def scenario():
        upstream = InvalidGenerator()
        cached = CachedHypothesisGenerator(upstream, model="model")
        await cached.generate(context())
        await cached.generate(context())
        assert upstream.calls == 2

    asyncio.run(scenario())
