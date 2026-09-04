import uuid

import pytest

import app.ai.roadmap_overview as roadmap_overview_module
from app.ai.llm.base import AIExtractionError, LLMResult, PromptSpec
from app.ai.roadmap_overview import generate_overview
from app.models.learning_path import RoadmapPhase
from app.models.skill import Skill
from app.models.skill_gap import GapLevel
from app.services.learning_roadmap import SequencedSkill

# Fully self-contained — real LLM calls are always monkeypatched out.


class _EchoProvider:
    def __init__(self) -> None:
        self.last_prompt: PromptSpec | None = None

    async def complete(
        self, prompt: PromptSpec, *, response_model: type | None = None
    ) -> LLMResult:
        self.last_prompt = prompt
        return LLMResult(
            text="A short, encouraging overview.",
            parsed=None,
            model="test-model",
            prompt_tokens=5,
            completion_tokens=5,
            latency_ms=1,
        )


class _FailingProvider:
    async def complete(
        self, prompt: PromptSpec, *, response_model: type | None = None
    ) -> LLMResult:
        raise AIExtractionError("LLM call failed: no credits remaining")


class _UnexpectedlyFailingProvider:
    """Raises something the provider layer's own wrapping never produces — e.g. a raw network
    error the SDK didn't translate into `AIExtractionError`. Proves `generate_overview` catches
    `Exception` broadly, not just the one error type the happy-path provider layer wraps."""

    async def complete(
        self, prompt: PromptSpec, *, response_model: type | None = None
    ) -> LLMResult:
        raise ConnectionError("connection reset by peer")


def _sequenced_skill(name: str, phase: RoadmapPhase, order_index: int) -> SequencedSkill:
    skill = Skill(id=uuid.uuid4(), name=name, slug=name.lower().replace(" ", "-"))
    return SequencedSkill(
        skill=skill, gap_level=GapLevel.MISSING, phase=phase, order_index=order_index
    )


async def test_generate_overview_returns_text_and_result_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _EchoProvider()
    monkeypatch.setattr(
        roadmap_overview_module, "get_provider_and_model", lambda task: (provider, "test-model")
    )
    sequenced = [_sequenced_skill("Python", RoadmapPhase.FOUNDATIONS, 0)]

    result = await generate_overview("AI Engineer", sequenced)

    assert result is not None
    text, llm_result = result
    assert text == "A short, encouraging overview."
    assert llm_result.model == "test-model"
    assert provider.last_prompt is not None
    assert "AI Engineer" in provider.last_prompt.user
    assert "Python" in provider.last_prompt.user
    assert provider.last_prompt.max_tokens is not None


async def test_generate_overview_returns_none_on_llm_failure_without_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        roadmap_overview_module,
        "get_provider_and_model",
        lambda task: (_FailingProvider(), "test-model"),
    )
    sequenced = [_sequenced_skill("Python", RoadmapPhase.FOUNDATIONS, 0)]

    result = await generate_overview("AI Engineer", sequenced)

    assert result is None  # never raises — the caller relies on this to keep generation working


async def test_generate_overview_returns_none_for_empty_sequence() -> None:
    result = await generate_overview("AI Engineer", [])
    assert result is None


async def test_generate_overview_returns_none_on_an_unexpected_exception_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression test found during human code review: the initial implementation only caught
    `AIExtractionError`, so a lower-level failure the provider layer doesn't wrap (a raw network
    error, an SDK bug) would have propagated straight through this function and broken the
    "generation always succeeds" promise. Widened to `except Exception`."""
    monkeypatch.setattr(
        roadmap_overview_module,
        "get_provider_and_model",
        lambda task: (_UnexpectedlyFailingProvider(), "test-model"),
    )
    sequenced = [_sequenced_skill("Python", RoadmapPhase.FOUNDATIONS, 0)]

    result = await generate_overview("AI Engineer", sequenced)

    assert result is None
