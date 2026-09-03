from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.analyzers.sql_migration import SqlMigrationParser
from app.clients.github import GitHubClient, build_github_http_client
from app.clients.openai_client import HypothesisGenerator, OpenAIHypothesisClient
from app.core.config import get_settings
from app.core.rate_limit import enforce_analysis_rate_limit
from app.schemas.github import AnalyzeGitHubPullRequest, PullRequestAnalysis
from app.services.ai_planning_cache import CachedHypothesisGenerator
from app.services.failure_planning_service import FailurePlanningService
from app.services.planning_context_budget import PlanningContextBudgeter
from app.services.pull_request_service import PullRequestService

router = APIRouter(prefix="/analyses", tags=["analyses"])


async def get_github_client() -> AsyncIterator[GitHubClient]:
    settings = get_settings()
    http_client = build_github_http_client(settings.github_token)
    try:
        yield GitHubClient(
            http_client,
            public_repositories_only=settings.github_public_repositories_only,
        )
    finally:
        await http_client.aclose()


@lru_cache
def get_hypothesis_generator() -> HypothesisGenerator:
    settings = get_settings()
    upstream = OpenAIHypothesisClient(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        max_output_tokens=settings.openai_max_output_tokens,
    )
    return CachedHypothesisGenerator(
        upstream,
        model=settings.openai_model,
        max_entries=settings.ai_cache_max_entries,
        ttl_seconds=settings.ai_cache_ttl_seconds,
    )


def get_pull_request_service(
    github_client: Annotated[GitHubClient, Depends(get_github_client)],
    hypothesis_generator: Annotated[HypothesisGenerator, Depends(get_hypothesis_generator)],
) -> PullRequestService:
    settings = get_settings()
    planning_service = FailurePlanningService(
        generator=hypothesis_generator,
        budgeter=PlanningContextBudgeter(
            max_changes=settings.max_ai_changes,
            max_evidence=settings.max_ai_evidence,
            max_excerpt_chars=settings.max_evidence_excerpt_chars,
            max_warnings=settings.max_ai_warnings,
            max_warning_chars=settings.max_warning_chars,
        ),
    )
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
    _rate_limit: Annotated[None, Depends(enforce_analysis_rate_limit)],
    service: Annotated[PullRequestService, Depends(get_pull_request_service)],
) -> PullRequestAnalysis:
    return await service.analyze(request.repository, request.pull_request)
