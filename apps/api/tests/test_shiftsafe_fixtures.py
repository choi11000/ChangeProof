import asyncio

from app.fixtures.shiftsafe_fixtures import (
    ControlledWeatherDependency,
    DownstreamMode,
    ShiftSafeApp,
    get_controlled_performance_fixture,
)


def test_shiftsafe_baseline_variant():
    async def _test():
        app = ShiftSafeApp(variant="baseline")
        res = await app.get_dashboard()
        assert "dashboard" in res
        assert res["dashboard"]["status"] == "HEALTHY"
        assert "weather" not in res
        assert res["downstream_wait_ms"] == 0

    asyncio.run(_test())


def test_shiftsafe_candidate_fast_mode():
    async def _test():
        weather = ControlledWeatherDependency(mode=DownstreamMode.FAST, latency_ms=10)
        app = ShiftSafeApp(variant="candidate", weather_dep=weather)
        res = await app.get_dashboard()
        assert "weather" in res
        assert res["weather"]["condition"] == "Cloudy"

    asyncio.run(_test())


def test_shiftsafe_remediated_caching_and_fallback():
    async def _test():
        weather = ControlledWeatherDependency(mode=DownstreamMode.FAST, latency_ms=10)
        app = ShiftSafeApp(variant="remediated", weather_dep=weather)
        res1 = await app.get_dashboard()
        assert res1["cache_hit"] is False

        # Second call should hit cache
        res2 = await app.get_dashboard()
        assert res2["cache_hit"] is True

        # Error mode triggers fallback
        err_weather = ControlledWeatherDependency(mode=DownstreamMode.ERROR)
        err_app = ShiftSafeApp(variant="remediated", weather_dep=err_weather)
        res_err = await err_app.get_dashboard()
        assert res_err.get("fallback") is True

    asyncio.run(_test())


def test_controlled_performance_fixture_digests():
    fixture = get_controlled_performance_fixture("shiftsafe/dashboard-weather-dependency")
    assert fixture is not None
    contract_digest = fixture.compute_contract_digest()
    assert contract_digest.startswith("perf_contract_")

    candidate_subject = fixture.compute_subject_digest("candidate")
    remediated_subject = fixture.compute_subject_digest("remediated")
    baseline_subject = fixture.compute_subject_digest("baseline")

    assert candidate_subject.startswith("perf_subject_")
    assert candidate_subject != remediated_subject
    assert candidate_subject != baseline_subject
