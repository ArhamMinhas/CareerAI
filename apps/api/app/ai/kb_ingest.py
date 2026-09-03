import re
import uuid

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kb_chunk import KbChunk
from app.models.resource import Resource
from app.services.embeddings import embed_text

# Word-count heuristic, not a real tokenizer — same "no tokenizer dependency just for this"
# tradeoff already made in app/workers/resume_tasks.py's `_EMBEDDING_MAX_CHARS`. English prose
# averages roughly 1.3 tokens per word (a few words split into multiple subword tokens); good
# enough to hit a soft ~300-500 token chunk-size target without a hard token-count guarantee.
_TOKENS_PER_WORD = 1.3
_TARGET_CHUNK_TOKENS = 400
_MAX_CHUNK_TOKENS = 500
_OVERLAP_RATIO = 0.15

_TARGET_WORDS = round(_TARGET_CHUNK_TOKENS / _TOKENS_PER_WORD)
_MAX_WORDS = round(_MAX_CHUNK_TOKENS / _TOKENS_PER_WORD)
_OVERLAP_WORDS = round(_TARGET_WORDS * _OVERLAP_RATIO)

# `##`/`###` headings only — an `#` (h1) is the document title, already captured by
# `Resource.title`, and doesn't recur as a mid-document boundary in the seeded content style.
_HEADING_RE = re.compile(r"(?m)^(#{2,3}\s+.+)$")


def _split_sections(body_md: str) -> list[str]:
    """Splits on heading boundaries first (docs/AI_ARCHITECTURE.md §6's "semantic boundaries"),
    keeping each heading attached to the section that follows it so a chunk built from that
    section still carries its heading's context. Falls back to treating the whole document as
    one section when there are no `##`/`###` headings at all."""
    parts = _HEADING_RE.split(body_md)
    sections: list[str] = []
    if parts[0].strip():
        sections.append(parts[0].strip())
    for i in range(1, len(parts), 2):
        heading = parts[i].strip()
        # `content` retains its own leading blank line(s) from the source text (the split only
        # consumes the heading line itself) — strip it before rejoining so a single canonical
        # `\n\n` separates heading from content, not a run of several blank lines.
        content = (parts[i + 1] if i + 1 < len(parts) else "").strip()
        sections.append(f"{heading}\n\n{content}" if content else heading)
    return sections


def _split_paragraphs(section: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n{2,}", section) if p.strip()]


def _split_oversized_paragraph(paragraph: str, max_words: int) -> list[str]:
    """A single paragraph (e.g. a table or code block) that alone exceeds `max_words` can't be
    merged with anything — split it into fixed-size word windows so no chunk downstream ever
    exceeds the assembled-context cap in `app/ai/rag_answer.py`."""
    words = paragraph.split()
    windows = [" ".join(words[i : i + max_words]) for i in range(0, len(words), max_words)]
    return windows or [paragraph]


def _merge_into_chunks(paragraphs: list[str], *, target_words: int, max_words: int) -> list[str]:
    """Greedily merges small adjacent paragraphs until hitting `target_words`, and never lets a
    chunk exceed `max_words` (splitting an oversized single paragraph on its own first)."""
    chunks: list[str] = []
    current: list[str] = []
    current_words = 0

    for paragraph in paragraphs:
        word_count = len(paragraph.split())

        if word_count > max_words:
            if current:
                chunks.append("\n\n".join(current))
                current, current_words = [], 0
            chunks.extend(_split_oversized_paragraph(paragraph, max_words))
            continue

        if current and current_words + word_count > max_words:
            chunks.append("\n\n".join(current))
            current, current_words = [], 0

        current.append(paragraph)
        current_words += word_count

        if current_words >= target_words:
            chunks.append("\n\n".join(current))
            current, current_words = [], 0

    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _add_overlap(chunks: list[str], *, overlap_words: int) -> list[str]:
    """Carries the tail of chunk N into the head of chunk N+1 so a fact split across a chunk
    boundary is still fully present in at least one chunk a retrieval can surface."""
    if overlap_words <= 0 or len(chunks) < 2:
        return chunks
    overlapped = [chunks[0]]
    for i in range(1, len(chunks)):
        previous_words = chunks[i - 1].split()
        tail = (
            " ".join(previous_words[-overlap_words:])
            if len(previous_words) > overlap_words
            else chunks[i - 1]
        )
        overlapped.append(f"{tail}\n\n{chunks[i]}")
    return overlapped


def chunk_markdown(body_md: str) -> list[str]:
    """Splits markdown into ~300-500 token chunks on semantic boundaries — headings first, then
    paragraphs — per docs/AI_ARCHITECTURE.md §6. Pure function, no I/O, so it's directly unit-
    testable without a DB or embedding calls."""
    sections = _split_sections(body_md) or ([body_md.strip()] if body_md.strip() else [])
    all_chunks: list[str] = []
    for section in sections:
        paragraphs = _split_paragraphs(section)
        if not paragraphs:
            continue
        all_chunks.extend(
            _merge_into_chunks(paragraphs, target_words=_TARGET_WORDS, max_words=_MAX_WORDS)
        )
    return _add_overlap(all_chunks, overlap_words=_OVERLAP_WORDS)


async def get_kb_chunks(db: AsyncSession, resource_id: uuid.UUID) -> list[KbChunk]:
    result = await db.execute(
        select(KbChunk).where(KbChunk.resource_id == resource_id).order_by(KbChunk.chunk_index)
    )
    return list(result.scalars().all())


async def ingest_resource(db: AsyncSession, resource: Resource) -> list[KbChunk]:
    """Chunks `resource.body_md`, embeds each chunk, and replaces this resource's `kb_chunks` as
    an atomic set. Re-ingestion is delete-then-reinsert inside a SAVEPOINT, mirroring
    `app/services/skill_gap.py`'s pattern exactly: two concurrent ingestions of the same resource
    would otherwise both see "no rows yet" and race to insert at the same `chunk_index`, and the
    loser would crash with a duplicate-key `IntegrityError` against
    `uq_kb_chunks_resource_chunk_index` instead of cleanly resolving. Since ingestion is
    deterministic for a given `body_md`, the loser doesn't need to retry its own write — it just
    reads back whatever the winner already committed. Does not commit — callers own the
    transaction, same convention as `store_embedding`/`compute_and_store_skill_gaps`."""
    chunk_texts = chunk_markdown(resource.body_md)
    chunks = [
        KbChunk(
            resource_id=resource.id,
            chunk_index=index,
            chunk_text=text,
            embedding=await embed_text(text),
            token_count=round(len(text.split()) * _TOKENS_PER_WORD),
        )
        for index, text in enumerate(chunk_texts)
    ]

    try:
        async with db.begin_nested():
            await db.execute(delete(KbChunk).where(KbChunk.resource_id == resource.id))
            db.add_all(chunks)
            await db.flush()
    except IntegrityError:
        return await get_kb_chunks(db, resource.id)
    return chunks
