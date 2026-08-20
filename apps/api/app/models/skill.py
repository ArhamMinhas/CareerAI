import enum
import re
import uuid

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin

_SLUG_NON_WORD = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    return _SLUG_NON_WORD.sub("-", name.strip().lower()).strip("-")


class Skill(UUIDPKMixin, TimestampMixin, Base):
    """Global skill taxonomy entry — docs/DATABASE.md §2.2.

    Phase 3 only needs `name`/`slug`/`category` to support manual skill entry with
    autocomplete; `synonyms`, `seo_summary`, and `embedding` are Phase 6 concerns
    (skill-gap engine, public `/skills/[slug]` pages) added when that phase needs them.
    """

    __tablename__ = "skills"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)


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
