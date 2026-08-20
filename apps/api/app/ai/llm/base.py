from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel


class AIExtractionError(Exception):
    """Raised when a provider call fails outright, or when structured output still fails
    schema validation after the one bounded retry docs/AI_ARCHITECTURE.md §3 allows. Callers
    that want a domain-specific error (e.g. `ResumeExtractionError`) catch and re-raise this."""


@dataclass
class PromptSpec:
    """A single LLM call, resolved by `app.ai.prompts.registry` (system/name/version) and
    `app.ai.llm.router` (model) before it reaches a provider — providers never choose their
    own prompt text or model (docs/AI_ARCHITECTURE.md §2, §4)."""

    system: str
    user: str
    model: str
    name: str
    version: str
    max_tokens: int | None = None
    temperature: float | None = None


@dataclass
class LLMResult:
    """Provider-agnostic call result. `parsed` is only set when the call was made with a
    `response_model` and the provider's native structured-output mode returned a value that
    validated against it. Token/latency fields feed `ai_conversations` logging
    (docs/AI_ARCHITECTURE.md §10) — callers own the actual DB write, not this layer."""

    text: str
    parsed: BaseModel | None
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int


class LLMProvider(Protocol):
    """docs/AI_ARCHITECTURE.md §2. Services depend on this protocol, never on a vendor SDK
    directly — `app.ai.llm.router` is the only place that picks a concrete implementation."""

    async def complete(
        self, prompt: PromptSpec, *, response_model: type[BaseModel] | None = None
    ) -> LLMResult: ...

    # Deliberately not `async def` — an async-generator function's *call* is synchronous and
    # returns the iterator directly; only iterating over it is async. Declaring this `async def`
    # would type the protocol member as returning `Coroutine[Any, Any, AsyncIterator[str]]`
    # instead, which no provider implementation (an async generator via `yield`) actually
    # matches.
    def stream(self, prompt: PromptSpec) -> AsyncIterator[str]: ...

    async def embed(self, texts: list[str]) -> list[list[float]]: ...
