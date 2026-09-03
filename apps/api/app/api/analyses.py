from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.analyzers.sql_migration import SqlMigrationParser
from app.clients.github import GitHubClient, build_github_http_client
from app.clients.openai_client import HypothesisGenerator, OpenAIHypothesisClient
from app.core.config import get_settings
from app.schemas.github import AnalyzeGitHubPullRequest, PullRequestAnalysis
from app.services.failure_planning_service import FailurePlanningService
from app.services.pull_request_service import PullRequestService

router = APIRouter(prefix="/analyses", tags=["analyses"])


async def get_github_client() -> AsyncIterator[GitHubClient]:
    settings = get_settings()
    http_client = build_github_http_client(settings.github_token)
    try:
        yield GitHubClient(http_client)
    finally:
        await http_client.aclose()


def get_hypothesis_generator() -> HypothesisGenerator:
    settings = get_settings()
    return OpenAIHypothesisClient(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
    )


def get_pull_request_service(
    github_client: Annotated[GitHubClient, Depends(get_github_client)],
    hypothesis_generator: Annotated[HypothesisGenerator, Depends(get_hypothesis_generator)],
) -> PullRequestService:
    planning_service = FailurePlanningService(generator=hypothesis_generator)
    return PullRequestService(
        github_client,
        SqlMigrationParser(),
        planning_service=planning_service,
    )


@router.post(
    "/github-pr",
    response_model=PullRequestAnalysis,
    status_code=status.HTTP_200_OK,
)
async def analyze_github_pull_request(
    request: AnalyzeGitHubPullRequest,
    service: Annotated[PullRequestService, Depends(get_pull_request_service)],
) -> PullRequestAnalysis:
    return await service.analyze(request.repository, request.pull_request)
