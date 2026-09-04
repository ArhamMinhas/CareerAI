import pytest

import app.ai.interview_evaluation as interview_evaluation_module
from app.ai.interview_evaluation import (
    InterviewEvaluationError,
    InterviewEvaluationResult,
    evaluate_answer,
)
from app.ai.llm.base import AIExtractionError, LLMResult, PromptSpec
from app.models.interview import InterviewMode

# Fully self-contained — real LLM calls are always monkeypatched out.


class _SucceedingProvider:
    def __init__(self) -> None:
        self.last_prompt: PromptSpec | None = None

    async def complete(
        self, prompt: PromptSpec, *, response_model: type | None = None
    ) -> LLMResult:
        self.last_prompt = prompt
        parsed = InterviewEvaluationResult(
            correctness_score=80, depth_score=70, communication_score=90, feedback="Solid answer."
        )
        return LLMResult(
            text="{}",
            parsed=parsed,
            model="test-model",
            prompt_tokens=1,
            completion_tokens=1,
            latency_ms=1,
        )


class _FailingProvider:
    async def complete(
        self, prompt: PromptSpec, *, response_model: type | None = None
    ) -> LLMResult:
        raise AIExtractionError("LLM call failed: no credits remaining")


class _NoParsedProvider:
    async def complete(
        self, prompt: PromptSpec, *, response_model: type | None = None
    ) -> LLMResult:
        return LLMResult(
            text="{}",
            parsed=None,
            model="test-model",
            prompt_tokens=1,
            completion_tokens=1,
            latency_ms=1,
        )


async def test_evaluate_answer_returns_parsed_result_and_llm_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _SucceedingProvider()
    monkeypatch.setattr(
        interview_evaluation_module, "get_provider_and_model", lambda task: (provider, "test-model")
    )

    result, llm_result = await evaluate_answer(
        mode=InterviewMode.TECHNICAL,
        question_text="How would you reverse a linked list?",
        answer_text="Iterate with three pointers, reversing links as you go.",
        resume_context=None,
    )

    assert result.correctness_score == 80
    assert result.feedback == "Solid answer."
    assert llm_result.model == "test-model"
    assert provider.last_prompt is not None
    assert "reverse a linked list" in provider.last_prompt.user
    assert "Iterate with three pointers" in provider.last_prompt.user
    # The mode-specific rubric was substituted into the system prompt, not left as a placeholder.
    assert "{mode_rubric}" not in provider.last_prompt.system
    assert "algorithmic correctness" in provider.last_prompt.system


async def test_evaluate_answer_includes_resume_context_when_given(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _SucceedingProvider()
    monkeypatch.setattr(
        interview_evaluation_module, "get_provider_and_model", lambda task: (provider, "test-model")
    )

    await evaluate_answer(
        mode=InterviewMode.BEHAVIORAL,
        question_text="Tell me about a conflict.",
        answer_text="I once disagreed with a teammate about...",
        resume_context="Skills: Python, React. Most recent role: Engineer at Acme",
    )

    assert provider.last_prompt is not None
    assert "Skills: Python, React" in provider.last_prompt.user


async def test_evaluate_answer_omits_resume_context_when_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _SucceedingProvider()
    monkeypatch.setattr(
        interview_evaluation_module, "get_provider_and_model", lambda task: (provider, "test-model")
    )

    await evaluate_answer(
        mode=InterviewMode.HR,
        question_text="Why this role?",
        answer_text="Because...",
        resume_context=None,
    )

    assert provider.last_prompt is not None
    assert "Resume context" not in provider.last_prompt.user


async def test_evaluate_answer_wraps_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        interview_evaluation_module,
        "get_provider_and_model",
        lambda task: (_FailingProvider(), "test-model"),
    )

    with pytest.raises(InterviewEvaluationError, match="no credits remaining"):
        await evaluate_answer(
            mode=InterviewMode.ML,
            question_text="Q",
            answer_text="A",
            resume_context=None,
        )


async def test_evaluate_answer_raises_when_model_returns_no_structured_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        interview_evaluation_module,
        "get_provider_and_model",
        lambda task: (_NoParsedProvider(), "test-model"),
    )

    with pytest.raises(InterviewEvaluationError, match="structured evaluation"):
        await evaluate_answer(
            mode=InterviewMode.DATA_SCIENCE,
            question_text="Q",
            answer_text="A",
            resume_context=None,
        )


def test_every_interview_mode_has_rubric_guidance() -> None:
    """A generic rubric applied uniformly across all 6 modes would be incoherent for at least
    behavioral/hr (no single 'correct' answer) — confirms every mode has real, distinct guidance
    text, not a missing/placeholder entry that would silently degrade to an empty substitution."""
    for mode in InterviewMode:
        assert mode in interview_evaluation_module._MODE_RUBRICS
        assert len(interview_evaluation_module._MODE_RUBRICS[mode]) > 20
