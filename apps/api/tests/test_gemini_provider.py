from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from google.genai.errors import APIError

from app.ai.llm.base import AIExtractionError, PromptSpec
from app.ai.llm.gemini_provider import GeminiProvider
from app.schemas.resume import ResumeExtraction


def _spec() -> PromptSpec:
    return PromptSpec(
        system="system",
        user="user",
        model="gemini-2.5-pro",
        name="resume_extraction",
        version="v1",
    )


def _fake_response(*, parsed: object, text: str = "{}"):
    return SimpleNamespace(
        parsed=parsed,
        text=text,
        usage_metadata=SimpleNamespace(prompt_token_count=100, candidates_token_count=20),
    )


@pytest.fixture
def provider() -> GeminiProvider:
    instance = GeminiProvider()
    instance._client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace()))
    return instance


async def test_complete_returns_parsed_result_on_success(provider: GeminiProvider) -> None:
    parsed = ResumeExtraction(full_name="Ada Lovelace")
    provider._client.aio.models.generate_content = AsyncMock(
        return_value=_fake_response(parsed=parsed)
    )

    result = await provider.complete(_spec(), response_model=ResumeExtraction)

    assert result.parsed is parsed
    assert result.prompt_tokens == 100
    assert result.completion_tokens == 20
    provider._client.aio.models.generate_content.assert_awaited_once()


async def test_complete_retries_once_then_succeeds(provider: GeminiProvider) -> None:
    parsed = ResumeExtraction(full_name="Ada Lovelace")
    provider._client.aio.models.generate_content = AsyncMock(
        side_effect=[
            _fake_response(parsed=None),  # not a BaseModel instance -> retryable
            _fake_response(parsed=parsed),
        ]
    )

    result = await provider.complete(_spec(), response_model=ResumeExtraction)

    assert result.parsed is parsed
    assert provider._client.aio.models.generate_content.await_count == 2


async def test_complete_raises_after_exhausting_retries(provider: GeminiProvider) -> None:
    provider._client.aio.models.generate_content = AsyncMock(
        return_value=_fake_response(parsed=None)
    )

    with pytest.raises(AIExtractionError):
        await provider.complete(_spec(), response_model=ResumeExtraction)

    assert provider._client.aio.models.generate_content.await_count == 2


async def test_complete_wraps_api_error(provider: GeminiProvider) -> None:
    provider._client.aio.models.generate_content = AsyncMock(
        side_effect=APIError(429, {"message": "quota exceeded"})
    )

    with pytest.raises(AIExtractionError, match="quota exceeded"):
        await provider.complete(_spec(), response_model=ResumeExtraction)


async def test_embed_returns_truncated_vectors(provider: GeminiProvider) -> None:
    response = SimpleNamespace(
        embeddings=[SimpleNamespace(values=[0.1, 0.2]), SimpleNamespace(values=[0.3, 0.4])]
    )
    provider._client.aio.models.embed_content = AsyncMock(return_value=response)

    vectors = await provider.embed(["a", "b"])

    assert vectors == [[0.1, 0.2], [0.3, 0.4]]


async def test_embed_wraps_api_error(provider: GeminiProvider) -> None:
    provider._client.aio.models.embed_content = AsyncMock(
        side_effect=APIError(429, {"message": "quota exceeded"})
    )

    with pytest.raises(AIExtractionError, match="quota exceeded"):
        await provider.embed(["a"])
