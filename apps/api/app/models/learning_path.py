import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPKMixin
from app.models.skill import Skill


class LearningPathStatus(enum.StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class RoadmapPhase(enum.StrEnum):
    """Deterministic, position-based buckets over the topologically-sorted skill sequence
    (app/services/learning_roadmap.py) — never LLM-decided, per docs/AI_ARCHITECTURE.md §8's
    Learning Planner guardrail."""

    FOUNDATIONS = "foundations"
    CORE = "core"
    ADVANCED = "advanced"


class LearningPath(UUIDPKMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A user's personalized, sequenced skill roadmap toward one target career path —
    docs/DATABASE.md §2.4, Phase 10. `target_role` is a plain string storing `career_paths.slug`,
    not a real FK — same convention and reasoning as `SkillGap.target_role`
    (app/models/skill_gap.py): a `career_paths` row can be renamed/removed without a defined
    cascade cleanly explaining what should happen to a user's roadmap.

    Unlike `SkillGap`/`JobMatch` (cached, deterministic, hard-replace-in-place output), this
    table carries genuine user-authored progress — `LearningPathItem.completed` checkmarks a
    user built up over time — so it's soft-deleted like `Application`
    (app/models/job_match.py), with the same **partial** unique index over non-deleted rows: a
    plain `UniqueConstraint` would block re-creating a roadmap for the same `target_role` after
    the user deletes it (`DELETE /api/v1/learning-roadmap`).

    `overview` is an optional LLM-generated narrative paragraph (app/ai/roadmap_overview.py) —
    stays `NULL` if that bounded call fails; the deterministic sequencing/resources are the real
    value here and must never be blocked by the narrative failing.

    `status` auto-transitions between `ACTIVE`/`COMPLETED` as items are completed/uncompleted
    (app/services/learning_roadmap.py) — `ABANDONED` is reserved for a future explicit
    "abandon this path" action, not used by anything in this phase."""

    __tablename__ = "learning_paths"
    __table_args__ = (
        Index(
            "uq_learning_paths_user_target_role_active",
            "user_id",
            "target_role",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_role: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    overview: Mapped[str | None] = mapped_column(Text(), nullable=True)
    status: Mapped[LearningPathStatus] = mapped_column(
        Enum(LearningPathStatus, name="learning_path_status"),
        default=LearningPathStatus.ACTIVE,
        nullable=False,
    )
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Deliberately no `items` relationship here: `app/services/learning_roadmap.py` always
    # queries `LearningPathItem` fresh (ordered, with `skill` eager-loaded) rather than reading
    # through a cached ORM collection, since `_persist_sequence` deletes and reinserts every
    # item on each regenerate within the same session — a relationship collection loaded before
    # that mutation would silently go stale.


class LearningPathItem(UUIDPKMixin, TimestampMixin, Base):
    """One skill's position in a `LearningPath`'s deterministic sequence — docs/DATABASE.md §2.4,
    Phase 10. Deliberate deviation from this doc's original design: `completed`/`completed_at`
    live here (the skill level), not on a resource row, because `SkillLearningResource` is
    shared curated content some skills have none of — see that model's docstring for the full
    reasoning. `phase`/`order_index` are fully recomputed on every
    `POST /learning-roadmap/generate` (app/services/learning_roadmap.py) — only `completed`/
    `completed_at` survive a regenerate, carried over by matching `skill_id`."""

    __tablename__ = "learning_path_items"
    __table_args__ = (
        UniqueConstraint("learning_path_id", "skill_id", name="uq_learning_path_items_path_skill"),
    )

    learning_path_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("learning_paths.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    phase: Mapped[RoadmapPhase] = mapped_column(
        Enum(RoadmapPhase, name="roadmap_phase"), nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer(), nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean(), default=False, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # `lazy="selectin"` — read during response serialization outside the loading query's own
    # await chain, same reasoning as `UserSkill.skill`/`CareerPathSkill.skill`.
    skill: Mapped["Skill"] = relationship(lazy="selectin")
