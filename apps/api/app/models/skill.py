import enum
import re
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin

_SLUG_NON_WORD = re.compile(r"[^a-z0-9]+")

SKILL_EMBEDDING_DIMENSIONS = 1536


def slugify(name: str) -> str:
    return _SLUG_NON_WORD.sub("-", name.strip().lower()).strip("-")


class Skill(UUIDPKMixin, TimestampMixin, Base):
    """Global skill taxonomy entry — docs/DATABASE.md §2.2.

    Phase 3 shipped `name`/`slug`/`category` only, for manual skill entry with autocomplete.
    `synonyms`/`seo_summary`/`embedding` are added here in Phase 6, which is the first feature
    that needs them: `seo_summary` renders on the public `/skills/[slug]` page
    (docs/SEO.md §1), `synonyms` improves that page's on-page content and search matching, and
    `embedding` powers the "related skills" section there via cosine similarity — all three
    stay null for skills nobody has curated content for yet (most user-entered/resume-extracted
    skills), which is fine: the gap-comparison algorithm itself never depends on them, only the
    content pages do.
    """

    __tablename__ = "skills"
    __table_args__ = (
        Index(
            "ix_skills_embedding_hnsw_cosine",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    synonyms: Mapped[list[str] | None] = mapped_column(ARRAY(String(100)), nullable=True)
    seo_summary: Mapped[str | None] = mapped_column(Text(), nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(SKILL_EMBEDDING_DIMENSIONS), nullable=True
    )


class Proficiency(enum.StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class SkillSource(enum.StrEnum):
    RESUME = "resume"
    MANUAL = "manual"
    INTERVIEW = "interview"


class UserSkill(UUIDPKMixin, TimestampMixin, Base):
    """A skill claimed by a profile — docs/DATABASE.md §2.2. `resume_id` stays null until
    Phase 4 wires resume-parsed skills in; Phase 3 only ever writes `source=manual`."""

    __tablename__ = "user_skills"
    __table_args__ = (
        UniqueConstraint("profile_id", "skill_id", name="uq_user_skills_profile_skill"),
    )

    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resume_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    proficiency: Mapped[Proficiency] = mapped_column(
        Enum(Proficiency, name="proficiency"), default=Proficiency.INTERMEDIATE, nullable=False
    )
    source: Mapped[SkillSource] = mapped_column(
        Enum(SkillSource, name="skill_source"), default=SkillSource.MANUAL, nullable=False
    )

    # `lazy="selectin"` because this is read during response serialization, outside the
    # await chain that loaded the parent query — see app/models/profile.py for the same
    # reasoning (async SQLAlchemy has no implicit lazy-load I/O).
    skill: Mapped["Skill"] = relationship(lazy="selectin")
