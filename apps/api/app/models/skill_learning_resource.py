import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class LearningResourceType(enum.StrEnum):
    COURSE = "course"
    ARTICLE = "article"
    PROJECT = "project"
    DOCS = "docs"


class SkillLearningResource(UUIDPKMixin, TimestampMixin, Base):
    """A curated learning resource (or project suggestion) for one skill — docs/DATABASE.md
    §2.4, Phase 10. Curated reference content, like `CareerPathSkill`/`SkillPrerequisite` —
    shared across all users' roadmaps, not persisted per-user; the Learning Roadmap response is
    built by joining this table on `skill_id` at read time, never duplicated per
    `LearningPathItem`.

    `resource_id` is a nullable FK to Phase 9's `resources` table, for the rare case a step's
    content genuinely is one of the curated `/resources/[slug]` articles (e.g. a "prep your
    resume" step linking `resources.ats-resume-tips`) — this resolves a real inconsistency in
    this doc's original design, where §2.6 implied `LEARNING_RESOURCES` had an FK to `RESOURCES`
    that §2.4's entity definition never actually included. `url` covers the far more common case
    of an external official-docs link; only stable, official-domain URLs are used (never a
    course-platform URL whose stability can't be verified). A "project suggestion"
    (`resource_type=PROJECT`) has no `url` — `title` holds the project description directly.

    No `completed` column here (unlike this doc's original sketch) — completion is tracked on
    `LearningPathItem` (the skill level), not per-resource: some skills have zero curated
    resources, which would make them permanently unmarkable-complete under a resource-level
    completion model, and this table is shared/reference data anyway, not a per-user row a
    completion flag could even meaningfully live on without a second per-user join table."""

    __tablename__ = "skill_learning_resources"

    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resources.id", ondelete="CASCADE"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    resource_type: Mapped[LearningResourceType] = mapped_column(
        Enum(LearningResourceType, name="learning_resource_type"), nullable=False
    )
    estimated_hours: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    order_index: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
