import httpx2
import pytest
from openai import APIError

import app.ai.resume_extraction as resume_extraction_module
from app.ai.llm.base import AIExtractionError, LLMResult, PromptSpec
from app.ai.llm.openai_provider import _clean_error_detail
from app.ai.resume_extraction import ResumeExtractionError, extract_resume_fields
from app.schemas.resume import ResumeExtraction

_DUMMY_REQUEST = httpx2.Request("POST", "https://api.openai.com/v1/chat/completions")


def _make_openai_error(body: object) -> APIError:
    return APIError(f"Error code: 429 - {body}", _DUMMY_REQUEST, body=body)


def test_clean_error_detail_extracts_message_from_body() -> None:
    body = {"error": {"message": "You have no credits remaining.", "code": "insufficient_quota"}}
    exc = _make_openai_error(body)
    assert _clean_error_detail(exc) == "You have no credits remaining."


def test_clean_error_detail_falls_back_to_str_when_no_body_message() -> None:
    exc = _make_openai_error(None)
    assert "429" in _clean_error_detail(exc)


class _FailingProvider:
    """Mimics an `LLMProvider` whose call fails — used to verify `extract_resume_fields`
    translates the provider layer's `AIExtractionError` into the resume-domain
    `ResumeExtractionError` rather than leaking the generic infra error."""

    async def complete(
        self, prompt: PromptSpec, *, response_model: type | None = None
    ) -> LLMResult:
        raise AIExtractionError("LLM call failed: no credits remaining")


class _SucceedingProvider:
    async def complete(
        self, prompt: PromptSpec, *, response_model: type | None = None
    ) -> LLMResult:
        parsed = ResumeExtraction(full_name="Ada Lovelace", skills=["Python"])
        return LLMResult(
            text="{}",
            parsed=parsed,
            model="test-model",
            prompt_tokens=1,
            completion_tokens=1,
            latency_ms=1,
        )


async def test_extract_resume_fields_wraps_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        resume_extraction_module,
        "get_provider_and_model",
        lambda task: (_FailingProvider(), "test-model"),
    )
    with pytest.raises(ResumeExtractionError, match="no credits remaining"):
        await extract_resume_fields("some resume text")


async def test_extract_resume_fields_returns_parsed_result_and_llm_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        resume_extraction_module,
        "get_provider_and_model",
        lambda task: (_SucceedingProvider(), "test-model"),
    )
    extraction, llm_result = await extract_resume_fields("some resume text")
    assert extraction.full_name == "Ada Lovelace"
    assert llm_result.model == "test-model"
