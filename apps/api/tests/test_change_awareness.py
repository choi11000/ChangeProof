from app.analyzers.performance_analyzer import PerformanceAnalyzer
from app.schemas.performance import PerformanceChangeType


def test_change_awareness_case_b_added_in_head():
    """CASE B: Weather call exists ONLY in head -> Fact emitted."""
    analyzer = PerformanceAnalyzer()

    base_code = """
from fastapi import FastAPI
app = FastAPI()

@app.get("/dashboard")
async def dashboard():
    return {"status": "ok"}
"""

    head_code = """
from fastapi import FastAPI
app = FastAPI()

@app.get("/dashboard")
async def dashboard():
    weather = await weather_client.get_current()
    return {"status": "ok", "weather": weather}
"""

    facts, evidences = analyzer.analyze_change(base_code, head_code)
    assert len(facts) == 1
    assert (
        facts[0].performance_change.change_type
        == PerformanceChangeType.EXTERNAL_CALL_ADDED_TO_REQUEST_PATH
    )
    assert facts[0].performance_change.downstream_symbol == "weather_client.get_current"
    assert facts[0].performance_change.endpoint == "GET /dashboard"
    assert len(evidences) == 1


def test_change_awareness_case_a_already_in_base():
    """CASE A: The weather call already exists in BOTH base and head -> NO new fact emitted."""
    analyzer = PerformanceAnalyzer()

    base_code = """
from fastapi import FastAPI
app = FastAPI()

@app.get("/dashboard")
async def dashboard():
    weather = await weather_client.get_current()
    return {"status": "ok", "weather": weather}
"""

    # Head modifies other logic on the route, but weather call was already present in base
    head_code = """
from fastapi import FastAPI
app = FastAPI()

@app.get("/dashboard")
async def dashboard():
    weather = await weather_client.get_current()
    logger.info("dashboard accessed")
    return {"status": "ok", "weather": weather, "logged": True}
"""

    facts, evidences = analyzer.analyze_change(base_code, head_code)
    # MUST NOT emit ADDED fact because it was already in base
    assert len(facts) == 0
    assert len(evidences) == 0


def test_change_awareness_case_c_removed_in_head():
    """CASE C: Weather call is removed in head -> must NOT be classified as ADDED."""
    analyzer = PerformanceAnalyzer()

    base_code = """
from fastapi import FastAPI
app = FastAPI()

@app.get("/dashboard")
async def dashboard():
    weather = await weather_client.get_current()
    return {"status": "ok", "weather": weather}
"""

    head_code = """
from fastapi import FastAPI
app = FastAPI()

@app.get("/dashboard")
async def dashboard():
    # Removed external call in favor of cached worker summary
    return {"status": "ok"}
"""

    facts, evidences = analyzer.analyze_change(base_code, head_code)
    assert len(facts) == 0
    assert len(evidences) == 0


def test_change_awareness_case_d_unrelated_code_change():
    """CASE D: Completely unrelated code change -> no performance ChangeFact."""
    analyzer = PerformanceAnalyzer()

    base_code = """
from fastapi import FastAPI
app = FastAPI()

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id}
"""

    head_code = """
from fastapi import FastAPI
app = FastAPI()

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id, "active": True}
"""

    facts, evidences = analyzer.analyze_change(base_code, head_code)
    assert len(facts) == 0
    assert len(evidences) == 0
