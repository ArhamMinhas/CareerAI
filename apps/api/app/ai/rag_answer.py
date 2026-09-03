from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm.base import AIExtractionError, LLMResult, PromptSpec
from app.ai.llm.router import get_provider_and_model
from app.ai.prompts.registry import load_prompt
from app.models.kb_chunk import KbChunk
from app.models.resource import Resource
from app.schemas.rag import RagCitation
from app.services.embeddings import embed_text

_RETRIEVAL_LIMIT = 5
# Hard cap on the *assembled* multi-chunk context, independent of each chunk's own ~500-token
# soft ingestion-time target (app/ai/kb_ingest.py) — bounds the prompt even in the edge case
# where several retrieved chunks are all near their individual max size. Same defensive-cap
# pattern as app/workers/resume_tasks.py's `_EMBEDDING_MAX_CHARS`.
_MAX_CONTEXT_CHARS = 12_000
_MAX_ANSWER_TOKENS = 600


class RagAnswerError(Exception):
    """Domain-specific error for the RAG query route. Wraps `AIExtractionError` from the
    provider layer, same convention as `ResumeExtractionError`."""


@dataclass(frozen=True)
class _RetrievedChunk:
    chunk_text: str
    resource_slug: str
    resource_title: str


async def _retrieve_chunks(
    db: AsyncSession, query_vector: list[float], *, limit: int
) -> list[_RetrievedChunk]:
    """Single query: the `Resource.published` filter runs in the same `WHERE` clause as the
    `ORDER BY ... LIMIT` similarity search, matching `find_related_career_paths`'s established
    single-query-snapshot pattern. This must never be a filter applied to results in Python
    *after* fetching — that would let a draft resource's chunks be retrieved (and cited to a
    user) before being filtered out, the moment a real draft resource exists."""
    result = await db.execute(
        select(KbChunk.chunk_text, Resource.slug, Resource.title)
        .join(Resource, KbChunk.resource_id == Resource.id)
        .where(Resource.published.is_(True))
        .order_by(KbChunk.embedding.cosine_distance(query_vector))
        .limit(limit)
    )
    return [
        _RetrievedChunk(chunk_text=row.chunk_text, resource_slug=row.slug, resource_title=row.title)
        for row in result.all()
    ]


def _build_context_and_citations(
    chunks: list[_RetrievedChunk],
) -> tuple[str, list[RagCitation]]:
    """Assembles numbered passages up to `_MAX_CONTEXT_CHARS` and returns citations only for the
    resources actually included in that assembled context (deduplicated — several chunks can
    come from the same resource, and a citation list should name each source once, not once per
    chunk)."""
    blocks: list[str] = []
    citations: list[RagCitation] = []
    seen_slugs: set[str] = set()
    total_chars = 0

    for index, chunk in enumerate(chunks, start=1):
        block = f'[{index}] (from "{chunk.resource_title}")\n{chunk.chunk_text}'
        if blocks and total_chars + len(block) > _MAX_CONTEXT_CHARS:
            break
        blocks.append(block)
        total_chars += len(block)
        if chunk.resource_slug not in seen_slugs:
            seen_slugs.add(chunk.resource_slug)
            citations.append(
                RagCitation(resource_slug=chunk.resource_slug, resource_title=chunk.resource_title)
            )

    return "\n\n".join(blocks), citations


async def answer_question(
    db: AsyncSession, question: str
) -> tuple[str, list[RagCitation], LLMResult]:
    """Retrieval + grounded generation (docs/AI_ARCHITECTURE.md §6). Returns the answer text,
    citations, and the raw `LLMResult` so the caller (the RAG query route) can log it to
    `ai_conversations` without this module taking on that responsibility itself — same division
    of labor as `extract_resume_fields`/the resume-processing task."""
    query_vector = await embed_text(question)
    chunks = await _retrieve_chunks(db, query_vector, limit=_RETRIEVAL_LIMIT)
    context, citations = _build_context_and_citations(chunks)

    provider, model = get_provider_and_model("rag_answer")
    prompt_def = load_prompt("rag_answer", "v1")
    passages = context or "No relevant passages were found in the knowledge base."
    user_message = f"{passages}\n\n---\n\nQuestion: {question}"
    spec = PromptSpec(
        system=prompt_def.system,
        user=user_message,
        model=model,
        name=prompt_def.name,
        version=prompt_def.version,
        max_tokens=_MAX_ANSWER_TOKENS,
    )

    try:
        result = await provider.complete(spec)
    except AIExtractionError as exc:
        raise RagAnswerError(str(exc)) from exc

    return result.text, citations, result
