import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import UUIDPKMixin

EMBEDDING_DIMENSIONS = 1536


class Embedding(UUIDPKMixin, Base):
    """docs/DATABASE.md §2.2 — polymorphic table for RAG knowledge-base chunks and any owner
    type that doesn't warrant its own dedicated `vector` column (resumes for now; jobs/skills
    get one here too until a later phase's query patterns justify denormalizing). No
    `updated_at`/soft-delete: an embedding is immutable for its content — a changed input gets
    a new row, not an update, so `(owner_type, owner_id)` can have several rows over time (e.g.
    resume re-analysis) and callers pick the most recent by `created_at`."""

    __tablename__ = "embeddings"
    __table_args__ = (
        # HNSW over cosine distance — matches the `<=>` operator docs/AI_ARCHITECTURE.md §5
        # names for similarity search. Doesn't need existing rows to build (unlike IVFFlat), so
        # it's safe to have from table creation even before anything queries it.
        Index(
            "ix_embeddings_embedding_hnsw_cosine",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    owner_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
