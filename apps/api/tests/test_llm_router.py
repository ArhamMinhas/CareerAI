import pytest

from app.ai.llm import router as router_module
from app.ai.llm.gemini_provider import GeminiProvider
from app.ai.llm.openai_provider import OpenAIProvider


@pytest.fixture(autouse=True)
def _clear_provider_cache() -> None:
    """`router._provider_cache` is a module-level singleton dict — clear it around each test so
    switching `settings.llm_provider` mid-suite doesn't reuse a provider built for a different
    setting."""
    router_module._provider_cache.clear()
    yield
    router_module._provider_cache.clear()


def test_get_provider_defaults_to_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(router_module.settings, "llm_provider", "openai")
    assert isinstance(router_module.get_provider(), OpenAIProvider)


def test_get_provider_returns_gemini_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(router_module.settings, "llm_provider", "gemini")
    assert isinstance(router_module.get_provider(), GeminiProvider)


def test_get_provider_is_cached_per_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(router_module.settings, "llm_provider", "openai")
    assert router_module.get_provider() is router_module.get_provider()


def test_get_model_uses_task_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(router_module.settings, "llm_model_reasoning", "reasoning-model")
    monkeypatch.setitem(router_module._TASK_MODELS, "resume_extraction", "reasoning-model")
    assert router_module.get_model("resume_extraction") == "reasoning-model"


def test_get_model_falls_back_to_default_for_unknown_task(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(router_module.settings, "llm_model_default", "default-model")
    assert router_module.get_model("some_unmapped_task") == "default-model"


def test_get_provider_and_model_returns_matching_pair(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(router_module.settings, "llm_provider", "openai")
    provider, model = router_module.get_provider_and_model("resume_extraction")
    assert isinstance(provider, OpenAIProvider)
    assert model == router_module.get_model("resume_extraction")
