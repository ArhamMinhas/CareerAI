import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin
from app.models.skill import Skill


class GapLevel(enum.StrEnum):
    MISSING = "missing"
    WEAK = "weak"
    ADEQUATE = "adequate"
    STRONG = "strong"


class SkillGap(UUIDPKMixin, TimestampMixin, Base):
    """One user's computed gap for one required skill of one target role —
    docs/DATABASE.md §2.3, docs/ML_PIPELINE.md §2.3. Deterministic set comparison, not an LLM
    call (docs/AI_ARCHITECTURE.md §1) — see `app/services/skill_gap.py`.

    `target_role` stores the resolved `career_paths.slug`, not the caller's raw query string
    (e.g. a `career_goals.target_role` of "AI Engineer" or a `?target_role=ai-engineer` query
    param both resolve to the same career path and must land in the same cached row set — a
    free-text key would let differently-phrased-but-equivalent queries silently duplicate the
    cache). It's still not a real FK: a `career_paths` row can be renamed/removed later without
    a cascade cleanly explaining what should happen to already-computed gaps, so this stays a
    plain string column, same as `career_goals.target_role` itself. Hard-deleted and fully
    replaced on every refresh (no soft-delete) — this is cached computed output, not durable
    user content, same category as `UserSkill`/`CareerGoal`."""

    __tablename__ = "skill_gaps"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "skill_id", "target_role", name="uq_skill_gaps_user_skill_role"
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_role: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    gap_level: Mapped[GapLevel] = mapped_column(Enum(GapLevel, name="gap_level"), nullable=False)
    priority: Mapped[int] = mapped_column(Integer(), nullable=False)

    # `lazy="selectin"` — same reasoning as `UserSkill.skill`/`CareerPathSkill.skill`.
    skill: Mapped["Skill"] = relationship(lazy="selectin")
