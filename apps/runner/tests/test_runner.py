import pytest
from pathlib import Path

from changeproof_runner.git_inspector import inspect_python_file
from changeproof_runner.load_generator import calculate_percentile
from changeproof_runner.validator import (
    TargetSecurityError,
    is_private_or_local_host,
    validate_target_url,
)


def test_validator_allows_local_and_private_targets():
    assert is_private_or_local_host("localhost") is True
    assert is_private_or_local_host("127.0.0.1") is True
    assert is_private_or_local_host("10.0.0.5") is True
    assert is_private_or_local_host("192.168.1.100") is True
    assert is_private_or_local_host("172.16.0.1") is True
    assert is_private_or_local_host("service.internal") is True
    assert is_private_or_local_host("myhost.local") is True

    assert validate_target_url("http://localhost:8000") == "http://localhost:8000"
    assert validate_target_url("http://127.0.0.1:8001/api") == "http://127.0.0.1:8001/api"


def test_validator_rejects_public_targets():
    assert is_private_or_local_host("google.com") is False
    assert is_private_or_local_host("8.8.8.8") is False
    assert is_private_or_local_host("changeproof-web-production.up.railway.app") is False

    with pytest.raises(TargetSecurityError, match="not a local or private environment"):
        validate_target_url("https://google.com")

    with pytest.raises(TargetSecurityError, match="not a local or private environment"):
        validate_target_url("http://8.8.8.8:8080")


def test_calculate_percentile_runner():
    vals = [10, 20, 30, 40, 50]
    assert calculate_percentile(vals, 50) == 30
    assert calculate_percentile([], 50) == 0


def test_inspect_python_file(tmp_path: Path):
    sample_file = tmp_path / "routes.py"
    sample_file.write_text(
        """
from fastapi import APIRouter
router = APIRouter()

@router.get("/dashboard")
def dashboard():
    data = weather_client.get_current()
    return data
""",
        encoding="utf-8",
    )

    findings = inspect_python_file(sample_file)
    assert len(findings) == 1
    assert findings[0]["method"] == "GET"
    assert findings[0]["path"] == "/dashboard"
    assert "weather_client.get_current" in findings[0]["symbol"]
