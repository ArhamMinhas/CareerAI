from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx2
import pytest
from openai import APIError

from app.ai.llm.base import AIExtractionError, PromptSpec
from app.ai.llm.openai_provider import OpenAIProvider
from app.schemas.resume import ResumeExtraction

_DUMMY_REQUEST = httpx2.Request("POST", "https://api.openai.com/v1/chat/completions")


def _spec() -> PromptSpec:
    return PromptSpec(
        system="system", user="user", model="gpt-4o", name="resume_extraction", version="v1"
    )


def _fake_completion(*, parsed: object, refusal: str | None = None, content: str = "{}"):
    message = SimpleNamespace(parsed=parsed, refusal=refusal, content=content)
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message)],
        model="gpt-4o-2024-08-06",
        usage=SimpleNamespace(prompt_tokens=100, completion_tokens=20),
    )


@pytest.fixture
def provider() -> OpenAIProvider:
    instance = OpenAIProvider()
    instance._client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace()),
        embeddings=SimpleNamespace(),
    )
    return instance


async def test_complete_returns_parsed_result_on_success(provider: OpenAIProvider) -> None:
    parsed = ResumeExtraction(full_name="Ada Lovelace")
    provider._client.chat.completions.parse = AsyncMock(
        return_value=_fake_completion(parsed=parsed)
    )

    result = await provider.complete(_spec(), response_model=ResumeExtraction)

    assert result.parsed is parsed
    assert result.model == "gpt-4o-2024-08-06"
    assert result.prompt_tokens == 100
    assert result.completion_tokens == 20
    provider._client.chat.completions.parse.assert_awaited_once()


async def test_complete_retries_once_then_succeeds(provider: OpenAIProvider) -> None:
    parsed = ResumeExtraction(full_name="Ada Lovelace")
    provider._client.chat.completions.parse = AsyncMock(
        side_effect=[
            _fake_completion(parsed=None),  # first attempt: no structured output
            _fake_completion(parsed=parsed),  # retry succeeds
        ]
    )

    result = await provider.complete(_spec(), response_model=ResumeExtraction)

    assert result.parsed is parsed
    assert provider._client.chat.completions.parse.await_count == 2


async def test_complete_raises_after_exhausting_retries(provider: OpenAIProvider) -> None:
    provider._client.chat.completions.parse = AsyncMock(return_value=_fake_completion(parsed=None))

    with pytest.raises(AIExtractionError):
        await provider.complete(_spec(), response_model=ResumeExtraction)

    assert provider._client.chat.completions.parse.await_count == 2


async def test_complete_raises_on_refusal(provider: OpenAIProvider) -> None:
    provider._client.chat.completions.parse = AsyncMock(
        return_value=_fake_completion(parsed=None, refusal="I can't help with that.")
    )

    with pytest.raises(AIExtractionError, match="refused"):
        await provider.complete(_spec(), response_model=ResumeExtraction)


async def test_complete_wraps_openai_error(provider: OpenAIProvider) -> None:
    body = {"error": {"message": "You have no credits remaining."}}
    provider._client.chat.completions.parse = AsyncMock(
        side_effect=APIError(f"Error code: 429 - {body}", _DUMMY_REQUEST, body=body)
    )

    with pytest.raises(AIExtractionError, match="no credits remaining"):
        await provider.complete(_spec(), response_model=ResumeExtraction)


async def test_embed_returns_vectors(provider: OpenAIProvider) -> None:
    response = SimpleNamespace(
        data=[SimpleNamespace(embedding=[0.1, 0.2]), SimpleNamespace(embedding=[0.3, 0.4])]
    )
    provider._client.embeddings.create = AsyncMock(return_value=response)

    vectors = await provider.embed(["a", "b"])

    assert vectors == [[0.1, 0.2], [0.3, 0.4]]


async def test_embed_wraps_openai_error(provider: OpenAIProvider) -> None:
    body = {"error": {"message": "rate limited"}}
    provider._client.embeddings.create = AsyncMock(
        side_effect=APIError(f"Error code: 429 - {body}", _DUMMY_REQUEST, body=body)
    )

    with pytest.raises(AIExtractionError, match="rate limited"):
        await provider.embed(["a"])
