import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin
from app.models.skill import SKILL_EMBEDDING_DIMENSIONS, Skill


class CareerPath(UUIDPKMixin, TimestampMixin, Base):
    """A curated role profile — docs/DATABASE.md §2.6. Backs both the public `/careers/[slug]`
    page and the Skill Gap Engine's target-role catalog (docs/ML_PIPELINE.md §2.3): a user's
    free-text `career_goals.target_role`/`skills/gaps?target_role=` is resolved to one of these
    rows by slug, and its `CareerPathSkill` rows are the required-skill profile the gap engine
    diffs a user's skills against. One row serves both consumers so the content is authored
    once, per docs/ROADMAP.md's Phase 6 entry.

    `published` gates visibility exactly like `Resources.published` will (Phase 9): unpublished
    rows are queryable internally but never served by the public API or included in the
    sitemap. No soft-delete — this is curated reference content, not user data (docs/DATABASE.md
    §1's soft-delete rule is for user-facing content tables)."""

    __tablename__ = "career_paths"
    __table_args__ = (
        Index(
            "ix_career_paths_embedding_hnsw_cosine",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text(), nullable=False)
    description_md: Mapped[str] = mapped_column(Text(), nullable=False)
    related_job_titles: Mapped[list[str] | None] = mapped_column(ARRAY(String(255)), nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(SKILL_EMBEDDING_DIMENSIONS), nullable=True
    )
    published: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)

    required_skills: Mapped[list["CareerPathSkill"]] = relationship(
        back_populates="career_path",
        lazy="selectin",
        order_by="CareerPathSkill.weight.desc()",
        cascade="all, delete-orphan",
    )


class CareerPathSkill(UUIDPKMixin, Base):
    """The required-skill profile for one career path — docs/DATABASE.md §2.6. `weight` (1-10)
    is how heavily this skill counts toward gap priority; `is_core` marks a skill as
    non-negotiable for the role (missing a core skill always outranks missing a merely
    high-weight one) — see `app/services/skill_gap.py`."""

    __tablename__ = "career_path_skills"
    __table_args__ = (
        UniqueConstraint("career_path_id", "skill_id", name="uq_career_path_skills_path_skill"),
    )

    career_path_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("career_paths.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    weight: Mapped[int] = mapped_column(Integer(), default=5, nullable=False)
    is_core: Mapped[bool] = mapped_column(Boolean(), default=False, nullable=False)

    career_path: Mapped["CareerPath"] = relationship(back_populates="required_skills")
    # `lazy="selectin"` — read during response serialization outside the loading query's own
    # await chain, same reasoning as `UserSkill.skill` (app/models/skill.py).
    skill: Mapped["Skill"] = relationship(lazy="selectin")
