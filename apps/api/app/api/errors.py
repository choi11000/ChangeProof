import logging
import traceback

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.clients.github import (
    GitHubApiUnavailable,
    GitHubAuthenticationError,
    GitHubPrivateRepositoryRestricted,
    GitHubPullRequestNotFound,
    GitHubRateLimitError,
    GitHubRepositoryNotFound,
)
from app.core.redaction import redact_secrets
from app.core.sandbox_gate import SandboxBusyError
from app.services.pull_request_service import InvalidGitHubRepository

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(InvalidGitHubRepository, _invalid_repository)
    app.add_exception_handler(GitHubRepositoryNotFound, _not_found)
    app.add_exception_handler(GitHubPullRequestNotFound, _not_found)
    app.add_exception_handler(GitHubAuthenticationError, _authentication_failed)
    app.add_exception_handler(GitHubRateLimitError, _rate_limited)
    app.add_exception_handler(GitHubApiUnavailable, _upstream_unavailable)
    app.add_exception_handler(GitHubPrivateRepositoryRestricted, _private_repository)
    app.add_exception_handler(SandboxBusyError, _sandbox_busy)
    app.add_exception_handler(Exception, _unexpected_error)


async def _invalid_repository(_request: Request, error: Exception) -> JSONResponse:
    return _error(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error))


async def _not_found(_request: Request, error: Exception) -> JSONResponse:
    return _error(status.HTTP_404_NOT_FOUND, str(error))


async def _authentication_failed(_request: Request, error: Exception) -> JSONResponse:
    return _error(status.HTTP_401_UNAUTHORIZED, str(error))


async def _rate_limited(_request: Request, error: Exception) -> JSONResponse:
    return _error(status.HTTP_429_TOO_MANY_REQUESTS, str(error))


async def _upstream_unavailable(_request: Request, error: Exception) -> JSONResponse:
    return _error(status.HTTP_502_BAD_GATEWAY, str(error))


async def _private_repository(_request: Request, error: Exception) -> JSONResponse:
    return _error(status.HTTP_403_FORBIDDEN, str(error))


async def _sandbox_busy(_request: Request, error: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        headers={"Retry-After": "1"},
        content={"detail": str(error)},
    )


async def _unexpected_error(request: Request, error: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    safe_traceback = redact_secrets("".join(traceback.format_exception(error)))
    logger.error(
        "unexpected_request_error\n%s", safe_traceback, extra={"request_id": request_id}
    )
    response = _error(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        f"Internal service error. Reference: {request_id}",
    )
    response.headers["X-Request-ID"] = request_id
    return response


def _error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": message})
