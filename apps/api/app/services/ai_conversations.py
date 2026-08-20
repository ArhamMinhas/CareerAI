import enum
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm.base import LLMResult
from app.models.ai_conversation import AIConversation


class AIFeature(enum.StrEnum):
    """Valid `ai_conversations.feature` values (docs/DATABASE.md §2.4). Kept as an
    application-layer enum, not a DB one — see `AIConversation`'s docstring."""

    RESUME_ANALYSIS = "resume_analysis"
    CAREER_ADVISOR = "career_advisor"
    INTERVIEW = "interview"
    RAG_CHAT = "rag_chat"


async def log_conversation(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    feature: AIFeature,
    result: LLMResult,
    prompt_name: str,
    prompt_version: str,
) -> AIConversation:
    """Records one LLM call for cost/latency observability (docs/AI_ARCHITECTURE.md §7, §10).
    `request_meta` only ever holds the prompt identity and non-sensitive params — never the
    full prompt/response text, per §10's safe-logging policy. Does not commit: callers append
    this to whatever transaction they're already in (e.g. the resume-processing task), so a
    later failure in that same transaction rolls this log entry back along with it rather than
    leaving an orphaned success record for a resume that ultimately failed.
    """
    conversation = AIConversation(
        user_id=user_id,
        feature=feature.value,
        model=result.model,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        latency_ms=result.latency_ms,
        request_meta={"prompt_name": prompt_name, "prompt_version": prompt_version},
    )
    db.add(conversation)
    await db.flush()
    return conversation
