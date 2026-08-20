import time
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI, OpenAIError
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from openai.types.chat.parsed_chat_completion import ParsedChatCompletion
from pydantic import BaseModel

from app.ai.llm.base import AIExtractionError, LLMResult, PromptSpec
from app.core.config import settings

# One initial attempt plus one bounded retry with the validation error fed back into the
# prompt, per docs/AI_ARCHITECTURE.md §3 — never more, so a persistently malformed response
# fails fast as a typed error instead of silently retrying forever.
_MAX_ATTEMPTS = 2


def _clean_error_detail(exc: OpenAIError) -> str:
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        message = body.get("error", {}).get("message")
        if message:
            return str(message)
    return str(exc)


def _optional_kwargs(prompt: PromptSpec) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if prompt.max_tokens is not None:
        kwargs["max_tokens"] = prompt.max_tokens
    if prompt.temperature is not None:
        kwargs["temperature"] = prompt.temperature
    return kwargs


class OpenAIProvider:
    """`LLMProvider` backed by the OpenAI API (docs/AI_ARCHITECTURE.md §2). Structured output
    uses `chat.completions.parse()`, which constrains decoding to the given Pydantic schema and
    returns an already-validated instance — satisfying §3's "always re-validated" requirement
    without a separate manual validation pass."""

    def __init__(self) -> None:
        # Constructed lazily, on first real use (see `_get_client`) — not here. `OpenAIProvider`
        # is instantiated eagerly by `app.ai.llm.router` regardless of whether an OpenAI key is
        # actually configured (e.g. `settings.llm_provider == "gemini"`, or no key set yet in a
        # fresh dev environment); the SDK's own constructor raises immediately on a blank key,
        # which would turn "AI not configured yet" into a hard crash instead of the graceful
        # degradation this codebase uses elsewhere (docs/CONTRIBUTING.md §2). Deferring
        # construction into the same try/except that already handles `OpenAIError` turns a
        # missing key into a normal `AIExtractionError` instead.
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(api_key=settings.openai_api_key, max_retries=5)
        return self._client

    async def complete(
        self, prompt: PromptSpec, *, response_model: type[BaseModel] | None = None
    ) -> LLMResult:
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": prompt.system},
            {"role": "user", "content": prompt.user},
        ]
        started = time.monotonic()
        last_error = ""

        for attempt in range(_MAX_ATTEMPTS):
            try:
                client = self._get_client()
                completion: ChatCompletion | ParsedChatCompletion[BaseModel]
                if response_model is not None:
                    completion = await client.chat.completions.parse(
                        model=prompt.model,
                        messages=messages,
                        response_format=response_model,
                        **_optional_kwargs(prompt),
                    )
                    message = completion.choices[0].message
                    if message.refusal:
                        raise AIExtractionError(f"Model refused: {message.refusal}")
                    if message.parsed is None:
                        raise AIExtractionError("Model did not return structured output.")
                    parsed: BaseModel | None = message.parsed
                    text = message.content or ""
                else:
                    completion = await client.chat.completions.create(
                        model=prompt.model,
                        messages=messages,
                        **_optional_kwargs(prompt),
                    )
                    parsed = None
                    text = completion.choices[0].message.content or ""
            except OpenAIError as exc:
                raise AIExtractionError(f"LLM call failed: {_clean_error_detail(exc)}") from exc
            except AIExtractionError as exc:
                last_error = str(exc)
                if attempt < _MAX_ATTEMPTS - 1:
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                f"Your previous response was invalid: {last_error}. "
                                "Respond again, strictly following the required schema."
                            ),
                        }
                    )
                    continue
                raise
            else:
                usage = completion.usage
                return LLMResult(
                    text=text,
                    parsed=parsed,
                    model=completion.model,
                    prompt_tokens=usage.prompt_tokens if usage else 0,
                    completion_tokens=usage.completion_tokens if usage else 0,
                    latency_ms=int((time.monotonic() - started) * 1000),
                )

        raise AIExtractionError(last_error or "Structured output validation failed after retry.")

    async def stream(self, prompt: PromptSpec) -> AsyncIterator[str]:
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": prompt.system},
            {"role": "user", "content": prompt.user},
        ]
        response_stream = await self._get_client().chat.completions.create(
            model=prompt.model,
            messages=messages,
            stream=True,
            **_optional_kwargs(prompt),
        )
        async for chunk in response_stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            response = await self._get_client().embeddings.create(
                model=settings.embedding_model, input=texts
            )
        except OpenAIError as exc:
            raise AIExtractionError(f"Embedding call failed: {_clean_error_detail(exc)}") from exc
        return [item.embedding for item in response.data]
