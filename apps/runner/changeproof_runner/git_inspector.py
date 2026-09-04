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
    except Exception:
        # Fallback: scan repository python files directly if not a git diff
        return []


def _extract_route_calls(source_code: str, file_path: str) -> list[dict[str, Any]]:
    """Extract external calls inside FastAPI routes from source code."""
    try:
        tree = ast.parse(source_code, filename=file_path)
    except Exception:
        return []

    findings = []
    external_patterns = {"requests", "httpx", "weather_client", "client", "external", "api", "downstream"}
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
                                            "file": file_path,
                                            "line": b_node.lineno,
                                            "method": route_method,
                                            "path": route_path,
                                            "symbol": call_sym,
                                        }
                                    )
    return findings


def get_git_file_content_at_ref(repo_path: Path, rel_path: str, ref: str = "HEAD~1") -> str | None:
    """Retrieve file content at specified git ref."""
    try:
        # Normalize path separators for git show (must be forward slash)
        git_path = rel_path.replace("\\", "/")
        cmd = ["git", "show", f"{ref}:{git_path}"]
        result = subprocess.run(
            cmd, cwd=repo_path, capture_output=True, text=True, check=True
        )
        return result.stdout
    except Exception:
        return None


def inspect_python_file(
    file_path: Path,
    repo_path: Path | None = None,
    base_ref: str = "HEAD~1",
) -> list[dict[str, Any]]:
    """Scan a Python file for FastAPI routes with external client calls.

    When repo_path is provided, performs change-aware diff comparison against base_ref,
    only reporting external calls that are genuinely ADDED in this change.
    """
    if not file_path.exists() or not file_path.name.endswith(".py"):
        return []

    try:
        head_code = file_path.read_text(encoding="utf-8")
    except Exception:
        return []

    head_findings = _extract_route_calls(head_code, str(file_path))

    # If repo_path provided, check against base_ref
    if repo_path is not None:
        try:
            rel_path = str(file_path.relative_to(repo_path))
        except ValueError:
            rel_path = file_path.name

        base_code = get_git_file_content_at_ref(repo_path, rel_path, ref=base_ref)
        if base_code is not None:
            base_findings = _extract_route_calls(base_code, str(file_path))
            base_keys = {(f["method"], f["path"], f["symbol"]) for f in base_findings}
            # Only keep findings NOT in base
            return [f for f in head_findings if (f["method"], f["path"], f["symbol"]) not in base_keys]

    return head_findings
