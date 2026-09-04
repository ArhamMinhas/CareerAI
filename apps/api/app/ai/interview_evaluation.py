from pydantic import BaseModel, Field

from app.ai.llm.base import AIExtractionError, LLMResult, PromptSpec
from app.ai.llm.router import get_provider_and_model
from app.ai.prompts.registry import load_prompt
from app.models.interview import InterviewMode

_MAX_ANSWER_CHARS = 10_000  # matches InterviewAnswerRequest's own max_length (schemas/interview.py)

# Mode-specific rubric guidance (docs/AI_ARCHITECTURE.md §8: "rubric-bounded scoring
# dimensions") — a single generic rubric applied uniformly across all 6 modes would be
# incoherent for at least `behavioral`/`hr` (there's rarely one "correct" answer to "tell me
# about a conflict with a coworker" the way there is for a technical question). Real, specific
# criteria per mode, not a placeholder string.
_MODE_RUBRICS: dict[InterviewMode, str] = {
    InterviewMode.TECHNICAL: (
        "Correctness means the approach is sound and would actually work — algorithmic "
        "correctness, correct handling of edge cases, awareness of complexity/performance where "
        "relevant. Depth means going beyond the first idea that comes to mind — discussing "
        "trade-offs, alternatives, or how to verify the solution."
    ),
    InterviewMode.BEHAVIORAL: (
        "There is rarely one 'correct' answer here — correctness means the story is real, "
        "specific, and actually answers what was asked (not a deflection to generalities). "
        "Depth means concrete detail: what the candidate specifically did and said, not just "
        "what the team or company did. Reward a STAR-like structure (Situation, Task, Action, "
        "Result) without requiring the labels themselves."
    ),
    InterviewMode.HR: (
        "Correctness means the answer is genuine and internally consistent (e.g. stated "
        "motivations align with the rest of their answers), not that there's a single right "
        "response. Depth means specific, personal reasoning rather than a rehearsed-sounding "
        "generic answer."
    ),
    InterviewMode.SYSTEM_DESIGN: (
        "Correctness means the proposed design would actually satisfy the stated requirements at "
        "the stated scale, without an obvious fatal flaw. Depth means real engagement with "
        "trade-offs (consistency vs. availability, cost vs. latency, etc.) and justifying "
        "choices, not just naming components or technologies."
    ),
    InterviewMode.ML: (
        "Correctness means the proposed approach (model choice, evaluation method, handling of "
        "data issues) is technically sound for the stated problem. Depth means discussing "
        "concrete failure modes, evaluation trade-offs, or how the candidate would validate the "
        "approach works, not just naming an algorithm."
    ),
    InterviewMode.DATA_SCIENCE: (
        "Correctness means the statistical/analytical reasoning is sound (e.g. a valid "
        "experiment design, a correctly-reasoned metric choice). Depth means engaging with "
        "confounders, sample size, or how results would be communicated to a non-technical "
        "stakeholder, not just naming a technique."
    ),
}


class InterviewEvaluationResult(BaseModel):
    """The LLM's structured judgment of one answer — passed as `response_format` to the provider
    call and re-validated against this schema, per docs/AI_ARCHITECTURE.md §3. Bounded scores,
    same convention as `ResumeExtraction.SubScore` (apps/api/app/schemas/resume.py)."""

    correctness_score: float = Field(ge=0, le=100)
    depth_score: float = Field(ge=0, le=100)
    communication_score: float = Field(ge=0, le=100)
    feedback: str


class InterviewEvaluationError(Exception):
    """Domain-specific error for the interview-answer route (app/api/v1/interviews.py). Wraps
    `AIExtractionError` from the provider layer, same convention as `ResumeExtractionError`.
    Unlike `app/ai/roadmap_overview.py`, this is allowed to propagate into a real error response
    — there's no deterministic fallback evaluation; the LLM call IS the product for this action,
    same reasoning as `app/ai/rag_answer.py`'s `RagAnswerError`."""


async def evaluate_answer(
    *,
    mode: InterviewMode,
    question_text: str,
    answer_text: str,
    resume_context: str | None,
) -> tuple[InterviewEvaluationResult, LLMResult]:
    """Structured evaluation via the `LLMProvider` abstraction. `resume_context` is a short,
    pre-formatted string (app/services/interviews.py) — never the raw `structured_data` blob —
    omitted from the prompt entirely when the caller has none (graceful degrade, not a required
    input): most users won't have an analyzed resume, and evaluation must still work well
    without one."""
    provider, model = get_provider_and_model("interview_evaluation")
    prompt_def = load_prompt("interview_evaluation", "v1")
    system = prompt_def.system.replace("{mode_rubric}", _MODE_RUBRICS[mode])

    resume_block = f"\n\nResume context: {resume_context}" if resume_context else ""
    user_message = (
        f"Question: {question_text}\n\n"
        f"Candidate's answer: {answer_text[:_MAX_ANSWER_CHARS]}"
        f"{resume_block}"
    )

    spec = PromptSpec(
        system=system,
        user=user_message,
        model=model,
        name=prompt_def.name,
        version=prompt_def.version,
    )

    try:
        result = await provider.complete(spec, response_model=InterviewEvaluationResult)
    except AIExtractionError as exc:
        raise InterviewEvaluationError(str(exc)) from exc

    if result.parsed is None or not isinstance(result.parsed, InterviewEvaluationResult):
        raise InterviewEvaluationError("Model did not return a structured evaluation.")

    return result.parsed, result
