from openai import AsyncOpenAI, OpenAIError

from app.core.config import settings
from app.schemas.resume import ResumeExtraction

# A plain inline prompt, not a versioned `ai/prompts/*.md` file — docs/AI_ARCHITECTURE.md §2/§4
# describe the full provider-abstraction + prompt-registry package for Phase 5, consumed by
# Phases 6-12 (Phase 4 isn't in that list). This module is a deliberately narrow, working
# stopgap: one direct OpenAI call behind a typed function, so Phase 4 has real extraction now
# without building infrastructure a later phase already owns formalizing. Nothing else in the
# codebase imports `openai` directly — this is the one flagged exception.
_SYSTEM_PROMPT = """You extract structured data from resume text. Only include information \
that is actually present in the text — never invent employers, dates, or skills. If a field \
isn't present, omit it or leave it empty. Normalize skill names to their common form (e.g. \
"JS" -> "JavaScript") but do not add skills that aren't mentioned."""


class ResumeExtractionError(Exception):
    pass


def _clean_error_detail(exc: OpenAIError) -> str:
    """`str(exc)` on an OpenAI SDK error is something like `Error code: 429 - {'error':
    {'message': '...', ...}}` — a Python dict repr, not fit to show a user. Pulls the actual
    message out of the parsed response body when there is one."""
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        message = body.get("error", {}).get("message")
        if message:
            return str(message)
    return str(exc)


async def extract_resume_fields(raw_text: str) -> ResumeExtraction:
    """Structured extraction via OpenAI's schema-constrained output — the response is
    guaranteed to match `ResumeExtraction`'s shape (docs/AI_ARCHITECTURE.md §3), so this either
    returns a valid object or raises; callers never see a partially-shaped result."""
    # `max_retries` above the SDK's default (2) — resume analysis is a background job, not a
    # user-blocking request, so it's worth trading a few extra seconds of backoff for
    # resilience against transient 429s rather than failing the whole analysis on one.
    client = AsyncOpenAI(api_key=settings.openai_api_key, max_retries=5)

    # Character cap, not token cap — cheap to compute and comfortably under any current
    # context window for a resume-length document, avoiding a tokenizer dependency just for this.
    truncated = raw_text[:20_000]

    try:
        completion = await client.chat.completions.parse(
            model=settings.llm_model_reasoning,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": truncated},
            ],
            response_format=ResumeExtraction,
        )
    except OpenAIError as exc:
        raise ResumeExtractionError(f"LLM extraction failed: {_clean_error_detail(exc)}") from exc

    message = completion.choices[0].message
    if message.refusal:
        raise ResumeExtractionError(f"Model refused extraction: {message.refusal}")
    if message.parsed is None:
        raise ResumeExtractionError("Model did not return structured output.")
    return message.parsed
