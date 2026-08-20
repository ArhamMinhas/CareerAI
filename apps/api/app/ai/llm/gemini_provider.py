import time
from collections.abc import AsyncIterator
from typing import Any

from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel

from app.ai.llm.base import AIExtractionError, LLMResult, PromptSpec
from app.core.config import settings

# Matches OpenAIProvider: one initial attempt plus one bounded retry with the validation
# error fed back into the prompt, per docs/AI_ARCHITECTURE.md §3.
_MAX_ATTEMPTS = 2

# `EMBEDDINGS.embedding` (docs/DATABASE.md §2.2) is a fixed `vector(1536)` column shared by
# every provider, so Gemini's embedding output is truncated to the same width via the API's
# own Matryoshka `output_dimensionality` support rather than a separate schema per provider.
_EMBEDDING_DIMENSIONS = 1536


class GeminiProvider:
    """`LLMProvider` backed by the Google Gemini API (docs/AI_ARCHITECTURE.md §2). Structured
    output uses `response_schema` set to the Pydantic model directly; the SDK parses the result
    into `response.parsed`, mirroring OpenAI's `message.parsed` — re-validated by treating a
    missing/non-matching `.parsed` as a retryable failure rather than trusting raw JSON."""

    def __init__(self) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key)

    def _config(
        self, prompt: PromptSpec, *, response_model: type[BaseModel] | None
    ) -> types.GenerateContentConfig:
        kwargs: dict[str, Any] = {"system_instruction": prompt.system}
        if prompt.max_tokens is not None:
            kwargs["max_output_tokens"] = prompt.max_tokens
        if prompt.temperature is not None:
            kwargs["temperature"] = prompt.temperature
        if response_model is not None:
            kwargs["response_mime_type"] = "application/json"
            kwargs["response_schema"] = response_model
        return types.GenerateContentConfig(**kwargs)

    async def complete(
        self, prompt: PromptSpec, *, response_model: type[BaseModel] | None = None
    ) -> LLMResult:
        started = time.monotonic()
        contents = prompt.user
        last_error = ""

        for attempt in range(_MAX_ATTEMPTS):
            try:
                response = await self._client.aio.models.generate_content(
                    model=prompt.model,
                    contents=contents,
                    config=self._config(prompt, response_model=response_model),
                )
            except APIError as exc:
                raise AIExtractionError(f"LLM call failed: {exc.message or exc}") from exc

            parsed: BaseModel | None = None
            if response_model is not None:
                candidate = response.parsed
                parsed = candidate if isinstance(candidate, BaseModel) else None
                if parsed is None:
                    last_error = "Model did not return structured output matching the schema."
                    if attempt < _MAX_ATTEMPTS - 1:
                        contents = (
                            f"{prompt.user}\n\n---\n"
                            f"Your previous response was invalid: {last_error} "
                            "Respond again, strictly following the required schema."
                        )
                        continue
                    raise AIExtractionError(last_error)

            usage = response.usage_metadata
            return LLMResult(
                text=response.text or "",
                parsed=parsed,
                model=prompt.model,
                prompt_tokens=(usage.prompt_token_count or 0) if usage else 0,
                completion_tokens=(usage.candidates_token_count or 0) if usage else 0,
                latency_ms=int((time.monotonic() - started) * 1000),
            )

        raise AIExtractionError(last_error or "Structured output validation failed after retry.")

    async def stream(self, prompt: PromptSpec) -> AsyncIterator[str]:
        response_stream = await self._client.aio.models.generate_content_stream(
            model=prompt.model,
            contents=prompt.user,
            config=self._config(prompt, response_model=None),
        )
        async for chunk in response_stream:
            if chunk.text:
                yield chunk.text

    async def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            response = await self._client.aio.models.embed_content(
                model=settings.embedding_model,
                contents=texts,
                config=types.EmbedContentConfig(output_dimensionality=_EMBEDDING_DIMENSIONS),
            )
        except APIError as exc:
            raise AIExtractionError(f"Embedding call failed: {exc.message or exc}") from exc
        return [list(item.values or []) for item in (response.embeddings or [])]
