from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, Boolean, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.embedding import EMBEDDING_DIMENSIONS
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Resource(UUIDPKMixin, TimestampMixin, Base):
    """A curated knowledge-base article — docs/DATABASE.md §2.6. Backs both the public,
    SEO-indexable `/resources/[slug]` page and the RAG pipeline's retrieval corpus
    (docs/AI_ARCHITECTURE.md §6, Phase 9): the same `body_md` is chunked and embedded into
    `KbChunk` (see that model's docstring for why chunk storage is a separate table) so the
    content is authored once and serves both consumers, matching `CareerPath`'s established
    dual-purpose pattern.

    `embedding` here is a whole-document vector, used only for the "related resources" lookup
    on the detail page (`find_related_resources`) — it is not what RAG retrieval queries against;
    that's `KbChunk.embedding`, one row per chunk.

    `published` gates visibility exactly like `CareerPath.published`: unpublished rows are
    queryable internally but never served by the public API, the sitemap, or RAG retrieval (RAG
    retrieval filters `Resource.published` in the same query as the similarity search — see
    `app/ai/rag_answer.py` — so a draft is never cited to a user). No soft-delete — curated
    reference content, not user data."""

    __tablename__ = "resources"
    __table_args__ = (
        Index(
            "ix_resources_embedding_hnsw_cosine",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text(), nullable=False)
    body_md: Mapped[str] = mapped_column(Text(), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String(100)), nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIMENSIONS), nullable=True
    )
    published: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
