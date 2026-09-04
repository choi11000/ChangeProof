import time
from typing import Any

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from app.fixtures.api_fixtures import ControlledApiFixture
from app.schemas.api_contract import ApiObservationCode
from app.schemas.execution import ExperimentStepResult, ExperimentStepStatus
from app.schemas.experiment import ExperimentStepType


class ApiExperimentExecutor:
    """Executes controlled API contract experiments using an in-process ASGI transport.

    Zero external network egress: All requests stay within the Python process memory.
    Zero arbitrary repository execution: Only server-owned controlled fixtures are executed.
    """

    def execute_fixture(
        self,
        fixture: ControlledApiFixture,
        variant: str = "changed",
    ) -> list[ExperimentStepResult]:
        step_results: list[ExperimentStepResult] = []
        payload = (
            fixture.remediated_payload if variant == "remediated" else fixture.changed_payload
        )

        # Step 1: Prepare in-process API environment
        t0 = time.perf_counter()
        step_results.append(
            ExperimentStepResult(
                order=1,
                type=ExperimentStepType.PREPARE_API_ENVIRONMENT,
                status=ExperimentStepStatus.PASSED,
                duration_ms=max(1, int((time.perf_counter() - t0) * 1000)),
                message="In-process ASGI provider environment initialized",
            )
        )

        # Build in-process Starlette ASGI application
        async def endpoint_handler(request):
            return JSONResponse(payload, status_code=fixture.expected_status)

        # Strip path parameters for exact fixture route
        route_path = fixture.path
        routes = [Route(route_path, endpoint_handler, methods=[fixture.method])]
        app = Starlette(routes=routes)

        # Step 2: Send real HTTP request through in-process ASGI transport
        t1 = time.perf_counter()
        resp_json: Any = None
        http_status: int = 0
        try:
            from starlette.testclient import TestClient
            with TestClient(app) as client:
                response = client.request(fixture.method, fixture.path)
                http_status = response.status_code
                resp_json = response.json()

            step_results.append(
                ExperimentStepResult(
                    order=2,
                    type=ExperimentStepType.SEND_HTTP_REQUEST,
                    status=ExperimentStepStatus.PASSED,
                    duration_ms=max(1, int((time.perf_counter() - t1) * 1000)),
                    http_status=http_status,
                    message=f"{fixture.method} {fixture.path} returned HTTP {http_status}",
                )
            )
        except Exception as exc:
            step_results.append(
                ExperimentStepResult(
                    order=2,
                    type=ExperimentStepType.SEND_HTTP_REQUEST,
                    status=ExperimentStepStatus.FAILED,
                    duration_ms=max(1, int((time.perf_counter() - t1) * 1000)),
                    http_status=http_status,
                    observation_code=ApiObservationCode.API_UNEXPECTED_STATUS,
                    message=f"HTTP request failed: {exc}",
                )
            )
            return step_results

        # Step 3: Run deterministic consumer probe
        t2 = time.perf_counter()
        target_field = fixture.target_field
        if isinstance(resp_json, dict) and target_field in resp_json:
            step_results.append(
                ExperimentStepResult(
                    order=3,
                    type=ExperimentStepType.PROBE_RESPONSE_FIELD,
                    status=ExperimentStepStatus.PASSED,
                    duration_ms=max(1, int((time.perf_counter() - t2) * 1000)),
                    http_status=http_status,
                    observation_code=ApiObservationCode.API_PROBE_PASSED,
                    json_pointer=f"/{target_field}",
                    message=(
                        f"Consumer probe passed: response contains required field {target_field!r}"
                    ),
                )
            )
        else:
            step_results.append(
                ExperimentStepResult(
                    order=3,
                    type=ExperimentStepType.PROBE_RESPONSE_FIELD,
                    status=ExperimentStepStatus.FAILED,
                    duration_ms=max(1, int((time.perf_counter() - t2) * 1000)),
                    http_status=http_status,
                    observation_code=ApiObservationCode.API_MISSING_RESPONSE_FIELD,
                    json_pointer=f"/{target_field}",
                    error_type="KeyError",
                    message=(
                        f"Consumer probe failed: response missing required field {target_field!r} "
                        f"(returned payload: {resp_json})"
                    ),
                )
            )

        # Step 4: Capture API result
        t3 = time.perf_counter()
        step_results.append(
            ExperimentStepResult(
                order=4,
                type=ExperimentStepType.CAPTURE_API_RESULT,
                status=ExperimentStepStatus.PASSED,
                duration_ms=max(1, int((time.perf_counter() - t3) * 1000)),
                message="API experiment result captured",
            )
        )

        return step_results
