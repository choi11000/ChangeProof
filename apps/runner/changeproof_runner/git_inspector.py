import ast
import os
import subprocess
from pathlib import Path
from typing import Any


def get_git_changed_files(repo_path: Path, base_ref: str = "HEAD~1") -> list[str]:
    """Get list of changed files relative to base_ref using git command."""
    try:
        cmd = ["git", "diff", "--name-only", base_ref]
        result = subprocess.run(
            cmd, cwd=repo_path, capture_output=True, text=True, check=True
        )
        files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
        return files
    except Exception as exc:
        # Fallback: scan repository python files directly if not a git diff
        return []


def inspect_python_file(file_path: Path) -> list[dict[str, Any]]:
    """Scan a Python file for FastAPI routes with external client calls."""
    if not file_path.exists() or not file_path.name.endswith(".py"):
        return []

    try:
        source_code = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source_code, filename=str(file_path))
    except Exception:
        return []

    findings = []
    external_patterns = {"requests", "httpx", "weather_client", "client", "external", "api"}
    router_symbols = {"router", "app", "api_router"}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            route_method = None
            route_path = None
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                    m = dec.func.attr.upper()
                    if m in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                        route_method = m
                        if dec.args and isinstance(dec.args[0], ast.Constant):
                            route_path = str(dec.args[0].value)

            if not route_method or not route_path:
                continue

            for stmt in node.body:
                for b_node in ast.walk(stmt):
                    if isinstance(b_node, ast.Call):
                        # Extract call name
                        chain = []
                        curr = b_node.func
                        while isinstance(curr, ast.Attribute):
                            chain.append(curr.attr)
                            curr = curr.value
                        if isinstance(curr, ast.Name):
                            chain.append(curr.id)
                        call_sym = ".".join(reversed(chain))

                        if call_sym:
                            parts = call_sym.split(".")
                            if parts[0].lower() not in router_symbols:
                                if any(p in call_sym.lower() for p in external_patterns):
                                    findings.append(
                                        {
                                            "file": str(file_path),
                                            "line": b_node.lineno,
                                            "method": route_method,
                                            "path": route_path,
                                            "symbol": call_sym,
                                        }
                                    )
    return findings
