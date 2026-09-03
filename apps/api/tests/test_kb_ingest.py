import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import delete

import app.ai.kb_ingest as kb_ingest_module
from app.ai.kb_ingest import (
    _MAX_WORDS,
    _OVERLAP_WORDS,
    _add_overlap,
    _merge_into_chunks,
    _split_paragraphs,
    _split_sections,
    chunk_markdown,
    get_kb_chunks,
    ingest_resource,
)
from app.core.db import AsyncSessionLocal
from app.models.kb_chunk import KbChunk
from app.models.resource import Resource

# Fully self-contained — these tests must not depend on app/scripts/seed_resources.py having
# been run, and never make real embedding calls (see `_fake_embed_text` / `monkeypatch`).


def test_split_sections_keeps_heading_attached_to_its_content() -> None:
    doc = (
        "Intro paragraph.\n\n## First heading\n\nFirst content.\n\n"
        "## Second heading\n\nSecond content."
    )
    sections = _split_sections(doc)
    assert sections == [
        "Intro paragraph.",
        "## First heading\n\nFirst content.",
        "## Second heading\n\nSecond content.",
    ]


def test_split_sections_falls_back_to_whole_doc_without_headings() -> None:
    doc = "Just some plain text.\n\nWith two paragraphs, no headings at all."
    assert _split_sections(doc) == [doc]


def test_split_paragraphs_splits_on_blank_lines_and_strips() -> None:
    section = "  Para one.  \n\n\nPara two.\n\nPara three.  "
    assert _split_paragraphs(section) == ["Para one.", "Para two.", "Para three."]


def test_merge_into_chunks_merges_small_paragraphs_up_to_target() -> None:
    # Three short paragraphs, well under target — should merge into one chunk, not three.
    paragraphs = ["Word " * 20, "Word " * 20, "Word " * 20]
    chunks = _merge_into_chunks(paragraphs, target_words=100, max_words=150)
    assert len(chunks) == 1
    assert chunks[0].count("Word") == 60


def test_merge_into_chunks_flushes_once_target_is_reached() -> None:
    paragraphs = ["Word " * 60, "Word " * 60, "Word " * 60]
    chunks = _merge_into_chunks(paragraphs, target_words=100, max_words=150)
    # First two paragraphs (120 words) exceed target after the 2nd, flushing before the 3rd.
    assert len(chunks) == 2


def test_merge_into_chunks_never_exceeds_max_words_for_normal_paragraphs() -> None:
    paragraphs = [f"Sentence number {i} with a few words in it." for i in range(40)]
    chunks = _merge_into_chunks(paragraphs, target_words=50, max_words=80)
    for chunk in chunks:
        assert len(chunk.split()) <= 80


def test_merge_into_chunks_splits_a_single_oversized_paragraph() -> None:
    # One paragraph alone exceeds max_words (e.g. a large table/code block) — must be split into
    # its own windows, never silently exceeding the cap or getting merged with anything else.
    paragraphs = ["small lead-in paragraph", "big " * 500]
    chunks = _merge_into_chunks(paragraphs, target_words=100, max_words=150)
    assert len(chunks) >= 4  # lead-in chunk + several 150-word windows from the 500-word blob
    for chunk in chunks:
        assert len(chunk.split()) <= 150


def test_add_overlap_carries_tail_of_previous_chunk_into_next() -> None:
    chunks = ["one two three four five", "six seven eight"]
    overlapped = _add_overlap(chunks, overlap_words=2)
    assert overlapped[0] == "one two three four five"
    assert overlapped[1] == "four five\n\nsix seven eight"


def test_add_overlap_noop_for_a_single_chunk() -> None:
    assert _add_overlap(["only chunk"], overlap_words=5) == ["only chunk"]


def test_add_overlap_noop_when_overlap_words_is_zero() -> None:
    chunks = ["a b c", "d e f"]
    assert _add_overlap(chunks, overlap_words=0) == chunks


def test_chunk_markdown_empty_input_returns_no_chunks() -> None:
    assert chunk_markdown("") == []
    assert chunk_markdown("   \n\n  ") == []


def test_chunk_markdown_produces_multiple_chunks_for_a_long_multi_section_document() -> None:
    sections = [f"## Heading {i}\n\n" + ("Real sentence content here. " * 80) for i in range(4)]
    doc = "\n\n".join(sections)
    chunks = chunk_markdown(doc)
    assert len(chunks) >= 4  # at least one chunk per heading section
    for chunk in chunks:
        # `_MAX_WORDS` plus the overlap words carried in from the previous chunk.
        assert len(chunk.split()) <= _MAX_WORDS + _OVERLAP_WORDS


@pytest.fixture
async def temp_resource() -> AsyncGenerator[Resource]:
    unique = uuid.uuid4().hex[:8]
    resource = Resource(
        slug=f"test-resource-{unique}",
        title=f"Test Resource {unique}",
        summary="A test resource.",
        body_md="## Section One\n\nSome content.\n\n## Section Two\n\nMore content.",
        published=True,
    )
    async with AsyncSessionLocal() as db:
        db.add(resource)
        await db.commit()
        await db.refresh(resource)

    yield resource

    async with AsyncSessionLocal() as db:
        await db.execute(delete(KbChunk).where(KbChunk.resource_id == resource.id))
        await db.execute(delete(Resource).where(Resource.id == resource.id))
        await db.commit()


async def _fake_embed_text(text: str) -> list[float]:
    return [0.1] * 1536


async def test_ingest_resource_persists_one_row_per_chunk(
    monkeypatch: pytest.MonkeyPatch, temp_resource: Resource
) -> None:
    monkeypatch.setattr(kb_ingest_module, "embed_text", _fake_embed_text)

    async with AsyncSessionLocal() as db:
        resource = await db.get(Resource, temp_resource.id)
        assert resource is not None
        chunks = await ingest_resource(db, resource)
        await db.commit()

    expected = chunk_markdown(temp_resource.body_md)
    assert len(chunks) == len(expected)
    assert [c.chunk_text for c in chunks] == expected
    assert [c.chunk_index for c in chunks] == list(range(len(expected)))


async def test_ingest_resource_reingestion_replaces_old_chunks(
    monkeypatch: pytest.MonkeyPatch, temp_resource: Resource
) -> None:
    monkeypatch.setattr(kb_ingest_module, "embed_text", _fake_embed_text)

    async with AsyncSessionLocal() as db:
        resource = await db.get(Resource, temp_resource.id)
        assert resource is not None
        await ingest_resource(db, resource)
        await db.commit()

    async with AsyncSessionLocal() as db:
        resource = await db.get(Resource, temp_resource.id)
        assert resource is not None
        resource.body_md = "## Only Section\n\nCompletely different content now."
        await db.flush()
        new_chunks = await ingest_resource(db, resource)
        await db.commit()

    async with AsyncSessionLocal() as db:
        stored = await get_kb_chunks(db, temp_resource.id)
        assert len(stored) == len(new_chunks)
        assert all("Completely different" in c.chunk_text for c in stored)


async def test_ingest_resource_survives_concurrent_calls(
    monkeypatch: pytest.MonkeyPatch, temp_resource: Resource
) -> None:
    """Regression test mirroring `test_compute_and_store_skill_gaps_survives_concurrent_calls`:
    two concurrent re-ingestions of the same resource used to be able to both see "no rows yet"
    and race to insert at the same `chunk_index`, crashing the loser with a duplicate-key
    `IntegrityError` against `uq_kb_chunks_resource_chunk_index` instead of cleanly resolving."""
    monkeypatch.setattr(kb_ingest_module, "embed_text", _fake_embed_text)

    async def _ingest() -> int:
        async with AsyncSessionLocal() as db:
            resource = await db.get(Resource, temp_resource.id)
            assert resource is not None
            chunks = await ingest_resource(db, resource)
            await db.commit()
            return len(chunks)

    first, second = await asyncio.gather(_ingest(), _ingest())
    assert first == second

    async with AsyncSessionLocal() as db:
        stored = await get_kb_chunks(db, temp_resource.id)
        indexes = [c.chunk_index for c in stored]
        assert indexes == sorted(set(indexes))  # no duplicate chunk_index rows survive
