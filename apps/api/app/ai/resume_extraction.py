from app.ai.llm.base import AIExtractionError, LLMResult, PromptSpec
from app.ai.llm.router import get_provider_and_model
from app.ai.prompts.registry import load_prompt
from app.schemas.resume import ResumeExtraction

_MAX_INPUT_CHARS = 20_000


class ResumeExtractionError(Exception):
    """Domain-specific error for the resume pipeline (app/workers/resume_tasks.py catches this
    specifically). Wraps `AIExtractionError` from the provider layer so callers here don't need
    to know about the underlying LLM abstraction."""


async def extract_resume_fields(raw_text: str) -> tuple[ResumeExtraction, LLMResult]:
    """Structured extraction via the `LLMProvider` abstraction (docs/AI_ARCHITECTURE.md §2) —
    this module used to call `openai` directly as a Phase 4 stopgap ahead of that abstraction
    existing; this is the migration the module's old docstring flagged. Returns the parsed
    extraction alongside the raw `LLMResult` so the caller (the resume-processing task) can log
    it to `ai_conversations` without this module taking on a DB dependency itself.
    """
    provider, model = get_provider_and_model("resume_extraction")
    prompt_def = load_prompt("resume_extraction", "v1")
    spec = PromptSpec(
        system=prompt_def.system,
        user=raw_text[:_MAX_INPUT_CHARS],
        model=model,
        name=prompt_def.name,
        version=prompt_def.version,
    )

    try:
        result = await provider.complete(spec, response_model=ResumeExtraction)
    except AIExtractionError as exc:
        raise ResumeExtractionError(str(exc)) from exc

    if result.parsed is None or not isinstance(result.parsed, ResumeExtraction):
        raise ResumeExtractionError("Model did not return structured output.")

    return result.parsed, result
