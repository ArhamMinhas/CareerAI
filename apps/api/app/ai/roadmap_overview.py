import logging

from app.ai.llm.base import LLMResult, PromptSpec
from app.ai.llm.router import get_provider_and_model
from app.ai.prompts.registry import load_prompt
from app.services.learning_roadmap import SequencedSkill

logger = logging.getLogger(__name__)

_MAX_OVERVIEW_TOKENS = 300


async def generate_overview(
    target_role: str, sequenced: list[SequencedSkill]
) -> tuple[str, LLMResult] | None:
    """The one bounded LLM call in the Learning Roadmap feature (docs/AI_ARCHITECTURE.md §8's
    Learning Planner) — given the target role and an *already-sequenced* skill list, generates a
    short narrative paragraph explaining the sequence. Never decides the sequence itself; that's
    entirely deterministic (app/services/learning_roadmap.py), matching the same "explains a
    decision it didn't make" guardrail as the Career Advisor agent.

    Returns `None` on any failure — a provider outage, a malformed response, an empty sequence,
    or any other unexpected error — rather than raising. This is deliberate and load-bearing:
    roadmap generation (the deterministic sequencing + resources) is the actual product here,
    and it must succeed whether or not this narrative does. Unlike `app/ai/rag_answer.py`, where
    the LLM answer *is* the product and a failure legitimately surfaces as a 502, this call's
    failure is swallowed here, inside this module, so the route calling it never sees an
    exception to mishandle.

    Deliberately catches `Exception` broadly, not just `AIExtractionError` — the provider layer
    only wraps its own SDK's exception hierarchy (`OpenAIError` etc.) into `AIExtractionError`;
    a lower-level failure (a raw network timeout, an SDK bug, anything the wrapper doesn't
    recognize) would otherwise propagate straight through this function and up into the route,
    contradicting the "never blocks generation" promise this docstring makes. `Exception` still
    lets `BaseException`-only signals (`asyncio.CancelledError`, `KeyboardInterrupt`) propagate
    normally — this only widens what counts as "the narrative failed," never swallows a real
    cancellation."""
    if not sequenced:
        return None

    try:
        provider, model = get_provider_and_model("roadmap_overview")
        prompt_def = load_prompt("roadmap_overview", "v1")
        skill_lines = "\n".join(
            f"{index}. {seq.skill.name} ({seq.phase.value}, currently {seq.gap_level.value})"
            for index, seq in enumerate(sequenced, start=1)
        )
        user_message = f"Target role: {target_role}\n\nSequenced skills:\n{skill_lines}"
        spec = PromptSpec(
            system=prompt_def.system,
            user=user_message,
            model=model,
            name=prompt_def.name,
            version=prompt_def.version,
            max_tokens=_MAX_OVERVIEW_TOKENS,
        )
        result = await provider.complete(spec)
    except Exception:
        logger.warning(
            "Roadmap overview generation failed; continuing without a narrative.", exc_info=True
        )
        return None

    return result.text, result
