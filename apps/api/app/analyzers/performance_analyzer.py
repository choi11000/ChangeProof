import ast
import logging
from typing import Any

from app.schemas.dependency import ChangeFact, DependencyEvidence, DependencyMatchKind, DependencyTarget, DependencyTargetType, SourceScope
from app.schemas.performance import PerformanceChange, PerformanceChangeType

logger = logging.getLogger(__name__)

EXTERNAL_CLIENT_PATTERNS = {
    "httpx",
    "requests",
    "weather_client",
    "external_client",
    "http_client",
    "api_client",
    "downstream",
}


def _get_call_attribute_chain(node: ast.AST) -> str:
    """Recursively extract attribute chain like 'weather_client.get_current' or 'httpx.get'."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _get_call_attribute_chain(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


ROUTER_SYMBOLS = {"router", "app", "api_router"}


def _is_external_call(call_expr: str) -> bool:
    """Check if the call expression looks like an external downstream HTTP / service call."""
    parts = call_expr.split(".")
    first_part = parts[0].lower()
    if first_part in ROUTER_SYMBOLS:
        return False
    lower = call_expr.lower()
    for pattern in EXTERNAL_CLIENT_PATTERNS:
        if pattern in lower:
            return True
    if any(lower.endswith(f".{m}") for m in ("get", "post", "put", "delete", "patch", "request")):
        return True
    return False


class RouteExternalCallVisitor(ast.NodeVisitor):
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.findings: list[dict[str, Any]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        self._check_route_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._check_route_function(node)
        self.generic_visit(node)

    def _check_route_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        route_method = None
        route_path = None

        for decorator in node.decorator_list:
            # Handle @app.get("/path") or @router.get("/path")
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                attr_name = decorator.func.attr.upper()
                if attr_name in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                    route_method = attr_name
                    if decorator.args and isinstance(decorator.args[0], ast.Constant):
                        route_path = str(decorator.args[0].value)
                    elif decorator.args and isinstance(decorator.args[0], ast.Str):  # py < 3.8
                        route_path = decorator.args[0].s

        if not route_method or not route_path:
            return

        # Scan ONLY function body for external client calls, NOT decorators
        for stmt in node.body:
            for body_node in ast.walk(stmt):
                if isinstance(body_node, ast.Call):
                    call_chain = _get_call_attribute_chain(body_node.func)
                    if call_chain and _is_external_call(call_chain):
                        self.findings.append(
                            {
                                "method": route_method,
                                "path": route_path,
                                "function_name": node.name,
                                "line": body_node.lineno,
                                "downstream_symbol": call_chain,
                            }
                        )


class PerformanceAnalyzer:
    """Deterministic AST analyzer detecting downstream external dependencies on hot request paths."""

    def analyze_source(
        self,
        source_code: str,
        file_path: str = "app/dashboard.py",
        *,
        changed_in_pull_request: bool = True,
    ) -> tuple[list[ChangeFact], list[DependencyEvidence]]:
        facts: list[ChangeFact] = []
        evidences: list[DependencyEvidence] = []

        try:
            tree = ast.parse(source_code, filename=file_path)
        except SyntaxError as e:
            logger.warning("Failed to parse %s for performance analysis: %s", file_path, e)
            return facts, evidences

        visitor = RouteExternalCallVisitor(file_path)
        visitor.visit(tree)

        for finding in visitor.findings:
            endpoint_str = f"{finding['method']} {finding['path']}"
            stable_id = f"performance:{finding['method']}:{finding['path']}:external:{finding['downstream_symbol']}"
            evidence_id = f"evidence_perf_{finding['line']}_{finding['downstream_symbol'].replace('.', '_')}"

            perf_change = PerformanceChange(
                change_type=PerformanceChangeType.EXTERNAL_CALL_ADDED_TO_REQUEST_PATH,
                endpoint=endpoint_str,
                method=finding["method"],
                source_file=file_path,
                line=finding["line"],
                downstream_symbol=finding["downstream_symbol"],
                changed_in_pull_request=changed_in_pull_request,
                context_snippet=f"{finding['function_name']}() calls {finding['downstream_symbol']}",
            )

            fact = ChangeFact(
                id=stable_id,
                domain="PERFORMANCE",
                sql_file_path=file_path,
                performance_change=perf_change,
            )
            facts.append(fact)

            target = DependencyTarget(
                type=DependencyTargetType.PERFORMANCE_ENDPOINT,
                path=finding["path"],
                table="",
                change_ids=[stable_id],
            )

            evidence = DependencyEvidence(
                id=evidence_id,
                target=target,
                path=file_path,
                line=finding["line"],
                match_kind=DependencyMatchKind.QUALIFIED_REFERENCE,
                excerpt=f"{endpoint_str} -> {finding['downstream_symbol']}",
                source_scope=SourceScope.APPLICATION,
                changed_in_pull_request=changed_in_pull_request,
            )
            evidences.append(evidence)

        return facts, evidences
