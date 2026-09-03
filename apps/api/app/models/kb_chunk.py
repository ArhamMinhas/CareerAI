import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.embedding import EMBEDDING_DIMENSIONS
from app.models.mixins import UUIDPKMixin


class KbChunk(UUIDPKMixin, Base):
    """A retrievable slice of a `Resource.body_md`, with its own embedding — the corpus RAG
    retrieval queries against (docs/AI_ARCHITECTURE.md §6, Phase 9). See `app/ai/kb_ingest.py`
    for how a resource is split into these.

    **Deliberate deviation from docs/DATABASE.md §2.6**, recorded here and in that section: the
    doc's original design routes per-chunk RAG embeddings through the polymorphic `Embedding`
    table (`owner_type='resource'`). That table has no text/content column — only a vector and
    an owner pointer — so it structurally cannot hold what RAG retrieval needs to show a user
    (the chunk text itself). Beyond the missing column, `Embedding`'s own docstring commits to an
    immutable, single-current-value-by-`created_at` lifecycle (proven right for its one real
    consumer, resume re-analysis); RAG chunks need the opposite — a *set* of N rows per resource,
    replaced atomically as a set on re-ingestion. Reusing `Embedding` would mean either violating
    that contract or leaving orphaned stale chunks from a prior ingestion mixed into future
    top-k retrieval — a real correctness bug (citing removed/outdated content to a user), not
    just a style mismatch. A dedicated table also avoids coupling one shared HNSW index across a
    low-QPS owner set (resumes/skills/career paths) and a high-QPS, chunk-heavy one (every RAG
    query hits this).

    `UniqueConstraint(resource_id, chunk_index)` backs the SAVEPOINT-based re-ingestion race fix
    in `app/ai/kb_ingest.py` (mirrors `app/services/skill_gap.py`'s pattern): without it,
    concurrent re-ingestion of the same resource could insert two different texts at the same
    index with no conflict to catch.
    """

    __tablename__ = "kb_chunks"
    __table_args__ = (
        UniqueConstraint("resource_id", "chunk_index", name="uq_kb_chunks_resource_chunk_index"),
        Index(
            "ix_kb_chunks_embedding_hnsw_cosine",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer(), nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text(), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS), nullable=False)
    token_count: Mapped[int] = mapped_column(Integer(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
