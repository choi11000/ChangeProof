import asyncio
import subprocess
from pathlib import Path
import pytest
import httpx

from changeproof_runner.git_inspector import get_git_changed_files, inspect_python_file
from changeproof_runner.load_generator import run_local_load
from changeproof_runner.validator import TargetSecurityError, validate_target_url


@pytest.fixture
def temp_git_repo(tmp_path: Path):
    """Creates a synthetic local Git repository with BASE and HEAD commits."""
    repo = tmp_path / "synthetic_repo"
    repo.mkdir()

    # Initialize Git
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@changeproof.internal"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "ChangeProof Tester"], cwd=repo, check=True)

    # BASE commit: dashboard without weather client
    dashboard_file = repo / "dashboard.py"
    dashboard_file.write_text(
        'from fastapi import FastAPI\n'
        'app = FastAPI()\n\n'
        '@app.get("/dashboard")\n'
        'async def dashboard():\n'
        '    return {"status": "ok"}\n',
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "dashboard.py"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Base: dashboard without weather"], cwd=repo, check=True)

    # HEAD commit: dashboard with weather client
    dashboard_file.write_text(
        'from fastapi import FastAPI\n'
        'app = FastAPI()\n\n'
        '@app.get("/dashboard")\n'
        'async def dashboard():\n'
        '    weather = await weather_client.get_current()\n'
        '    return {"status": "ok", "weather": weather}\n',
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "dashboard.py"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Head: dashboard with weather client"], cwd=repo, check=True)

    return repo


def test_local_git_diff_change_detection(temp_git_repo: Path):
    """Section 15: Prove GitHub is genuinely optional for change detection."""
    changed_files = get_git_changed_files(temp_git_repo, "HEAD~1")
    assert "dashboard.py" in changed_files

    findings = inspect_python_file(
        temp_git_repo / "dashboard.py",
        repo_path=temp_git_repo,
        base_ref="HEAD~1",
    )
    assert len(findings) == 1
    assert findings[0]["method"] == "GET"
    assert findings[0]["path"] == "/dashboard"
    assert findings[0]["symbol"] == "weather_client.get_current"


def test_local_http_load_and_functional_pass_contrast():
    """Section 15 & 19: Local HTTP target execution, functional PASS vs peak load."""
    async def run_scenario():
        async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
            try:
                await reader.readuntil(b"\r\n\r\n")
            except asyncio.IncompleteReadError:
                return

            await asyncio.sleep(0.01)

            response = (
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: application/json\r\n"
                b"Content-Length: 16\r\n"
                b"Connection: close\r\n"
                b"\r\n"
                b'{"status": "ok"}'
            )
            try:
                writer.write(response)
                await writer.drain()
            except (ConnectionResetError, BrokenPipeError):
                pass
            finally:
                writer.close()
                await writer.wait_closed()

        server = await asyncio.start_server(handle_client, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]

        async with server:
            metrics = await run_local_load(
                target_url=f"http://127.0.0.1:{port}",
                method="GET",
                endpoint="/dashboard",
                concurrency=5,
                request_count=10,
            )

            assert metrics.functional_pass is True
            assert metrics.functional_latency_ms >= 1
            assert metrics.request_count == 10
            assert metrics.success_count == 10
            assert metrics.p50_ms >= 1
            assert metrics.throughput_rps > 0

    asyncio.run(run_scenario())


def test_private_target_security_policies():
    """Section 16 & 17: Runner security rules: allow private/local, deny public targets."""
    # Allowed
    assert validate_target_url("http://127.0.0.1:8000") == "http://127.0.0.1:8000"
    assert validate_target_url("http://localhost:3000") == "http://localhost:3000"
    assert validate_target_url("http://10.0.1.5:8080") == "http://10.0.1.5:8080"
    assert validate_target_url("http://192.168.1.50:5000") == "http://192.168.1.50:5000"

    # Denied
    with pytest.raises(TargetSecurityError):
        validate_target_url("http://google.com")

    with pytest.raises(TargetSecurityError):
        validate_target_url("http://8.8.8.8:80")

    with pytest.raises(TargetSecurityError):
        validate_target_url("https://changeproof-web-production.up.railway.app")


def test_redirect_bypass_denied():
    """Section 16: Ensure HTTP client refuses to silently follow redirects."""
    async def run_scenario():
        async def handle_redirect(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
            await reader.readuntil(b"\r\n\r\n")
            response = (
                b"HTTP/1.1 302 Found\r\n"
                b"Location: https://evil-public-site.com\r\n"
                b"Content-Length: 0\r\n"
                b"Connection: close\r\n"
                b"\r\n"
            )
            writer.write(response)
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(handle_redirect, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]

        async with server:
            metrics = await run_local_load(
                target_url=f"http://127.0.0.1:{port}",
                method="GET",
                endpoint="/dashboard",
                concurrency=1,
                request_count=2,
            )
            assert metrics.error_count == 2
            assert metrics.success_count == 0

    asyncio.run(run_scenario())
