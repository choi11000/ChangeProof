from app.analyzers.performance_analyzer import PerformanceAnalyzer
from app.schemas.dependency import DependencyTargetType
from app.schemas.performance import PerformanceChangeType


def test_performance_analyzer_detects_sync_and_async_routes():
    source_code = """
from fastapi import APIRouter
import httpx

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard():
    weather = weather_client.get_current()
    return {"status": "ok", "weather": weather}

@router.post("/items")
def create_item():
    res = requests.post("https://example.com/api", json={})
    return {"created": True}

@router.get("/health")
def health():
    return {"status": "healthy"}
"""
    analyzer = PerformanceAnalyzer()
    facts, evidences = analyzer.analyze_source(source_code, file_path="app/routes.py")

    assert len(facts) == 2
    assert len(evidences) == 2

    # Check dashboard fact
    dash_fact = next(f for f in facts if "/dashboard" in f.id)
    assert dash_fact.domain == "PERFORMANCE"
    assert dash_fact.performance_change is not None
    assert (
        dash_fact.performance_change.change_type
        == PerformanceChangeType.EXTERNAL_CALL_ADDED_TO_REQUEST_PATH
    )
    assert dash_fact.performance_change.endpoint == "GET /dashboard"
    assert dash_fact.performance_change.downstream_symbol == "weather_client.get_current"

    # Check items fact
    items_fact = next(f for f in facts if "/items" in f.id)
    assert items_fact.performance_change is not None
    assert items_fact.performance_change.endpoint == "POST /items"
    assert items_fact.performance_change.downstream_symbol == "requests.post"

    # Verify evidence
    dash_ev = next(e for e in evidences if "/dashboard" in e.target.path)
    assert dash_ev.target.type == DependencyTargetType.PERFORMANCE_ENDPOINT
    assert dash_ev.path == "app/routes.py"
    assert dash_ev.line > 0


def test_performance_analyzer_handles_syntax_error():
    analyzer = PerformanceAnalyzer()
    facts, evidences = analyzer.analyze_source("def broken_syntax(:", file_path="broken.py")
    assert facts == []
    assert evidences == []


def test_performance_analyzer_no_routes():
    source_code = """
def helper_function():
    return 42
"""
    analyzer = PerformanceAnalyzer()
    facts, evidences = analyzer.analyze_source(source_code, file_path="helper.py")
    assert facts == []
    assert evidences == []
