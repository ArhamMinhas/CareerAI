import uuid

from sqlalchemy import delete, select

from app.ai.llm.base import LLMResult
from app.core.db import AsyncSessionLocal
from app.models.ai_conversation import AIConversation
from app.models.user import Role, User
from app.services.ai_conversations import AIFeature, log_conversation


async def test_log_conversation_persists_expected_fields() -> None:
    user = User(id=uuid.uuid4(), email=f"test-{uuid.uuid4()}@example.com", role=Role.USER)
    result = LLMResult(
        text="ignored",
        parsed=None,
        model="gpt-4o",
        prompt_tokens=123,
        completion_tokens=45,
        latency_ms=678,
    )

    async with AsyncSessionLocal() as db:
        db.add(user)
        await db.flush()

        conversation = await log_conversation(
            db,
            user_id=user.id,
            feature=AIFeature.RESUME_ANALYSIS,
            result=result,
            prompt_name="resume_extraction",
            prompt_version="v1",
        )
        await db.commit()
        conversation_id = conversation.id

    async with AsyncSessionLocal() as db:
        row = await db.get(AIConversation, conversation_id)
        assert row is not None
        assert row.user_id == user.id
        assert row.feature == "resume_analysis"
        assert row.model == "gpt-4o"
        assert row.prompt_tokens == 123
        assert row.completion_tokens == 45
        assert row.latency_ms == 678
        # Safe-logging policy (docs/AI_ARCHITECTURE.md §10): only prompt identity, never raw
        # prompt/response text.
        assert row.request_meta == {"prompt_name": "resume_extraction", "prompt_version": "v1"}

        await db.execute(delete(AIConversation).where(AIConversation.id == conversation_id))
        await db.execute(delete(User).where(User.id == user.id))
        await db.commit()


async def test_log_conversation_does_not_commit() -> None:
    """`log_conversation` only flushes — the caller controls the transaction (see
    app/workers/resume_tasks.py, which logs a conversation and may still roll the whole
    unit of work back on a later failure)."""
    user = User(id=uuid.uuid4(), email=f"test-{uuid.uuid4()}@example.com", role=Role.USER)
    result = LLMResult(
        text="", parsed=None, model="m", prompt_tokens=1, completion_tokens=1, latency_ms=1
    )

    async with AsyncSessionLocal() as db:
        db.add(user)
        await db.flush()
        await log_conversation(
            db,
            user_id=user.id,
            feature=AIFeature.RESUME_ANALYSIS,
            result=result,
            prompt_name="resume_extraction",
            prompt_version="v1",
        )
        await db.rollback()

    async with AsyncSessionLocal() as db:
        found = await db.execute(select(User).where(User.id == user.id))
        assert found.scalar_one_or_none() is None
