import asyncio
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)

from app.clients.openai_client import (
    FailurePlanningContext,
    OpenAIAuthError,
    OpenAIHypothesisClient,
    OpenAIRateLimitError,
    OpenAITimeoutError,
)
from app.schemas.experiment import ExperimentTemplate
from app.schemas.hypothesis import (
    FailureCategory,
    FailureHypothesis,
    HypothesisProposalResult,
    HypothesisStatus,
)


def _sample_context() -> FailurePlanningContext:
    return FailurePlanningContext(
        changes=[],
        evidence=[],
        scan_complete=True,
    )


def test_unconfigured_client_raises_auth_error() -> None:
    client = OpenAIHypothesisClient(api_key=None)
    assert client.is_configured is False

    with pytest.raises(OpenAIAuthError, match="not configured"):
        asyncio.run(client.generate(_sample_context()))


def test_openai_auth_error_mapping() -> None:
    mock_openai = MagicMock()
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    mock_openai.responses.parse = AsyncMock(
        side_effect=AuthenticationError(
            message="Incorrect API key",
            response=httpx.Response(401, request=request),
            body=None,
        )
    )

    client = OpenAIHypothesisClient(client=mock_openai)
    assert client.is_configured is True

    with pytest.raises(OpenAIAuthError, match="authentication failed"):
        asyncio.run(client.generate(_sample_context()))


def test_openai_rate_limit_mapping() -> None:
    mock_openai = MagicMock()
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    mock_openai.responses.parse = AsyncMock(
        side_effect=RateLimitError(
            message="Rate limit reached",
            response=httpx.Response(429, request=request),
            body=None,
        )
    )

    client = OpenAIHypothesisClient(client=mock_openai)

    with pytest.raises(OpenAIRateLimitError, match="rate limit"):
        asyncio.run(client.generate(_sample_context()))


def test_openai_timeout_mapping() -> None:
    mock_openai = MagicMock()
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    mock_openai.responses.parse = AsyncMock(
        side_effect=APITimeoutError(request=request)
    )

    client = OpenAIHypothesisClient(client=mock_openai)

    with pytest.raises(OpenAITimeoutError, match="network/timeout"):
        asyncio.run(client.generate(_sample_context()))


def test_openai_connection_error_mapping() -> None:
    mock_openai = MagicMock()
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    mock_openai.responses.parse = AsyncMock(
        side_effect=APIConnectionError(request=request)
    )

    client = OpenAIHypothesisClient(client=mock_openai)

    with pytest.raises(OpenAITimeoutError, match="network/timeout"):
        asyncio.run(client.generate(_sample_context()))


def test_openai_successful_structured_output() -> None:
    mock_openai = MagicMock()
    expected_result = HypothesisProposalResult(
        hypotheses=[
            FailureHypothesis(
                id="hyp_001",
                category=FailureCategory.SCHEMA_CONTRACT_BREAK,
                title="Dropped column referenced",
                statement="Application references orders.legacy_status",
                change_ids=["c1"],
                evidence_ids=["e1"],
                rationale="Test",
                expected_failure_mode="Error",
                assumptions=[],
                experiment_template=ExperimentTemplate.DROPPED_COLUMN_REFERENCE,
                status=HypothesisStatus.UNVERIFIED,
            )
        ]
    )
    mock_response = MagicMock()
    mock_response.output_parsed = expected_result
    mock_response.usage.input_tokens = 101
    mock_response.usage.output_tokens = 22
    mock_response.usage.total_tokens = 123
    mock_openai.responses.parse = AsyncMock(return_value=mock_response)

    client = OpenAIHypothesisClient(client=mock_openai)
    result = asyncio.run(client.generate(_sample_context()))

    assert len(result.hypotheses) == 1
    assert result.hypotheses[0].id == "hyp_001"
    assert result.usage.input_tokens == 101
    assert result.usage.output_tokens == 22
    assert result.usage.total_tokens == 123
    assert mock_openai.responses.parse.await_args.kwargs["max_output_tokens"] == 1200


def test_openai_model_refusal_or_empty_returns_empty_list() -> None:
    mock_openai = MagicMock()
    mock_response = MagicMock()
    mock_response.output_parsed = None
    mock_openai.responses.parse = AsyncMock(return_value=mock_response)

    client = OpenAIHypothesisClient(client=mock_openai)
    result = asyncio.run(client.generate(_sample_context()))

    assert result.hypotheses == []


def test_missing_usage_is_safe() -> None:
    mock_openai = MagicMock()
    mock_response = MagicMock(spec=["output_parsed"])
    mock_response.output_parsed = HypothesisProposalResult(hypotheses=[])
    mock_openai.responses.parse = AsyncMock(return_value=mock_response)
    result = asyncio.run(OpenAIHypothesisClient(client=mock_openai).generate(_sample_context()))
    assert result.usage.input_tokens is None
    assert result.usage.total_tokens is None
