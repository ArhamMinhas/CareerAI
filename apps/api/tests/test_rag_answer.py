import uuid
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import delete

import app.ai.rag_answer as rag_answer_module
from app.ai.llm.base import AIExtractionError, LLMResult, PromptSpec
from app.ai.rag_answer import RagAnswerError, answer_question
from app.core.db import AsyncSessionLocal
from app.models.kb_chunk import KbChunk
from app.models.resource import Resource

# Fully self-contained — real embed/LLM calls are always monkeypatched out.

_CLOSE_VECTOR = [0.1] * 1536
_FAR_VECTOR = [-0.1] * 1536


class _EchoProvider:
    """Records the assembled prompt so tests can assert on what actually reached the model,
    and returns a fixed answer — same pattern as test_resume_extraction.py's fake providers."""

    def __init__(self) -> None:
        self.last_prompt: PromptSpec | None = None

    async def complete(
        self, prompt: PromptSpec, *, response_model: type | None = None
    ) -> LLMResult:
        self.last_prompt = prompt
        return LLMResult(
            text="Here is the grounded answer. [1]",
            parsed=None,
            model="test-model",
            prompt_tokens=10,
            completion_tokens=5,
            latency_ms=1,
        )


class _FailingProvider:
    async def complete(
        self, prompt: PromptSpec, *, response_model: type | None = None
    ) -> LLMResult:
        raise AIExtractionError("LLM call failed: no credits remaining")


async def _fake_embed_text_close(text: str) -> list[float]:
    return _CLOSE_VECTOR


@pytest.fixture
async def rag_fixture() -> AsyncGenerator[tuple[Resource, Resource, Resource]]:
    """Two published resources (one with a chunk vector close to the test query, one far) and
    one draft resource whose chunk vector is *closest* of all — proves the published filter runs
    inside the retrieval query itself, not as a post-filter, since if it were a post-filter the
    draft's chunk would be retrieved (it's the closest vector) before being dropped."""
    unique = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        close_published = Resource(
            slug=f"rag-close-{unique}",
            title=f"Close Published Resource {unique}",
            summary="s",
            body_md="b",
            published=True,
        )
        far_published = Resource(
            slug=f"rag-far-{unique}",
            title=f"Far Published Resource {unique}",
            summary="s",
            body_md="b",
            published=True,
        )
        draft = Resource(
            slug=f"rag-draft-{unique}",
            title=f"Draft Resource {unique}",
            summary="s",
            body_md="b",
            published=False,
        )
        db.add_all([close_published, far_published, draft])
        await db.flush()

        db.add_all(
            [
                KbChunk(
                    resource_id=close_published.id,
                    chunk_index=0,
                    chunk_text="The published, relevant passage.",
                    embedding=_CLOSE_VECTOR,
                    token_count=5,
                ),
                KbChunk(
                    resource_id=far_published.id,
                    chunk_index=0,
                    chunk_text="An unrelated published passage.",
                    embedding=_FAR_VECTOR,
                    token_count=5,
                ),
                KbChunk(
                    resource_id=draft.id,
                    chunk_index=0,
                    chunk_text="A draft passage that must never be cited.",
                    embedding=_CLOSE_VECTOR,  # closest of all three
                    token_count=5,
                ),
            ]
        )
        await db.commit()
        ids = (close_published.id, far_published.id, draft.id)

    yield close_published, far_published, draft

    async with AsyncSessionLocal() as db:
        await db.execute(delete(KbChunk).where(KbChunk.resource_id.in_(ids)))
        await db.execute(delete(Resource).where(Resource.id.in_(ids)))
        await db.commit()


async def test_answer_question_never_cites_a_draft_resource_even_when_closest(
    monkeypatch: pytest.MonkeyPatch, rag_fixture: tuple[Resource, Resource, Resource]
) -> None:
    close_published, far_published, draft = rag_fixture
    provider = _EchoProvider()
    monkeypatch.setattr(rag_answer_module, "embed_text", _fake_embed_text_close)
    monkeypatch.setattr(
        rag_answer_module, "get_provider_and_model", lambda task: (provider, "test-model")
    )

    async with AsyncSessionLocal() as db:
        answer, citations, result = await answer_question(db, "What should I do?")

    cited_slugs = {c.resource_slug for c in citations}
    assert draft.slug not in cited_slugs
    assert close_published.slug in cited_slugs
    assert answer == "Here is the grounded answer. [1]"
    assert result.model == "test-model"
    assert provider.last_prompt is not None
    assert "draft passage" not in provider.last_prompt.user
    assert "published, relevant passage" in provider.last_prompt.user
    assert provider.last_prompt.max_tokens is not None


async def test_answer_question_dedupes_citations_by_resource(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unique = uuid.uuid4().hex[:8]
    provider = _EchoProvider()
    monkeypatch.setattr(rag_answer_module, "embed_text", _fake_embed_text_close)
    monkeypatch.setattr(
        rag_answer_module, "get_provider_and_model", lambda task: (provider, "test-model")
    )

    async with AsyncSessionLocal() as db:
        resource = Resource(
            slug=f"rag-multi-chunk-{unique}",
            title=f"Multi Chunk Resource {unique}",
            summary="s",
            body_md="b",
            published=True,
        )
        db.add(resource)
        await db.flush()
        db.add_all(
            [
                KbChunk(
                    resource_id=resource.id,
                    chunk_index=0,
                    chunk_text="First relevant passage.",
                    embedding=_CLOSE_VECTOR,
                    token_count=5,
                ),
                KbChunk(
                    resource_id=resource.id,
                    chunk_index=1,
                    chunk_text="Second relevant passage.",
                    embedding=_CLOSE_VECTOR,
                    token_count=5,
                ),
            ]
        )
        await db.commit()
        resource_id = resource.id

    try:
        async with AsyncSessionLocal() as db:
            _, citations, _ = await answer_question(db, "What should I do?")
        matching = [c for c in citations if c.resource_slug == f"rag-multi-chunk-{unique}"]
        assert len(matching) == 1  # deduplicated, not one row per chunk
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(KbChunk).where(KbChunk.resource_id == resource_id))
            await db.execute(delete(Resource).where(Resource.id == resource_id))
            await db.commit()


async def test_answer_question_wraps_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rag_answer_module, "embed_text", _fake_embed_text_close)
    monkeypatch.setattr(
        rag_answer_module, "get_provider_and_model", lambda task: (_FailingProvider(), "test-model")
    )

    async with AsyncSessionLocal() as db:
        with pytest.raises(RagAnswerError, match="no credits remaining"):
            await answer_question(db, "What should I do?")


async def test_answer_question_handles_empty_retrieval_without_crashing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No published resource has any chunk near the query — `_retrieve_chunks` returns nothing,
    and the module must still produce a (no-citation) answer via the "no relevant passages"
    fallback text rather than raising or sending an empty prompt."""
    provider = _EchoProvider()
    monkeypatch.setattr(rag_answer_module, "embed_text", _fake_embed_text_close)
    monkeypatch.setattr(
        rag_answer_module, "get_provider_and_model", lambda task: (provider, "test-model")
    )

    async def _empty_retrieve(db: object, query_vector: object, *, limit: int) -> list:  # noqa: ANN001, ARG001
        return []

    monkeypatch.setattr(rag_answer_module, "_retrieve_chunks", _empty_retrieve)

    async with AsyncSessionLocal() as db:
        answer, citations, _ = await answer_question(db, "A question with no relevant content.")

    assert answer == "Here is the grounded answer. [1]"
    assert citations == []
    assert provider.last_prompt is not None
    assert "No relevant passages were found" in provider.last_prompt.user
