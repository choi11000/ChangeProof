from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.clients.github import (
    GitHubApiUnavailable,
    GitHubAuthenticationError,
    GitHubPullRequestNotFound,
    GitHubRateLimitError,
    GitHubRepositoryNotFound,
)
from app.services.pull_request_service import InvalidGitHubRepository


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(InvalidGitHubRepository, _invalid_repository)
    app.add_exception_handler(GitHubRepositoryNotFound, _not_found)
    app.add_exception_handler(GitHubPullRequestNotFound, _not_found)
    app.add_exception_handler(GitHubAuthenticationError, _authentication_failed)
    app.add_exception_handler(GitHubRateLimitError, _rate_limited)
    app.add_exception_handler(GitHubApiUnavailable, _upstream_unavailable)


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


def _error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": message})
