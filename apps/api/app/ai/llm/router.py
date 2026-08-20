from app.ai.llm.base import LLMProvider
from app.ai.llm.gemini_provider import GeminiProvider
from app.ai.llm.openai_provider import OpenAIProvider
from app.core.config import settings

# Per-task model overrides. Anything not listed here falls back to `settings.llm_model_default`
# — both are provider-agnostic identifiers (docs/AI_ARCHITECTURE.md §2): switching providers
# means pointing these env vars at that provider's model names, not touching this dict or any
# call site.
_TASK_MODELS: dict[str, str] = {
    "resume_extraction": settings.llm_model_reasoning,
}

_provider_cache: dict[str, LLMProvider] = {}


def _build_provider(name: str) -> LLMProvider:
    if name == "gemini":
        return GeminiProvider()
    return OpenAIProvider()


def get_provider(name: str | None = None) -> LLMProvider:
    """Returns the cached provider instance for `name` (defaults to `settings.llm_provider`).
    Cached so each provider's underlying SDK client — and its connection pool — is reused
    across calls within a process rather than rebuilt per request."""
    provider_name = name or settings.llm_provider
    if provider_name not in _provider_cache:
        _provider_cache[provider_name] = _build_provider(provider_name)
    return _provider_cache[provider_name]


def get_model(task: str) -> str:
    return _TASK_MODELS.get(task, settings.llm_model_default)


def get_provider_and_model(task: str) -> tuple[LLMProvider, str]:
    """The single call site every AI-consuming service should use to get a provider + model
    for a named task — never hardcode a provider class or model string elsewhere
    (docs/AI_ARCHITECTURE.md §2)."""
    return get_provider(), get_model(task)
