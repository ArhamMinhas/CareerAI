import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.learning_path import LearningPathStatus, RoadmapPhase
from app.models.skill_learning_resource import LearningResourceType
from app.schemas.career_path import CareerPathRead
from app.schemas.skill import SkillRead


class SkillLearningResourceRead(BaseModel):
    """A curated resource/project suggestion for one skill (app/models/skill_learning_resource.py)
    — not an ORM `from_attributes` mapping on its own, since `resource_slug` is derived from a
    join the route performs (app/services/learning_roadmap.py), not a column on the model."""

    id: uuid.UUID
    title: str
    url: str | None
    resource_type: LearningResourceType
    estimated_hours: int | None
    resource_slug: str | None = Field(
        default=None,
        description="Set when this resource links to a curated /resources/[slug] article "
        "(Phase 9) rather than an external url.",
    )


class LearningPathItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    skill: SkillRead
    phase: RoadmapPhase
    order_index: int
    completed: bool
    completed_at: datetime | None
    resources: list[SkillLearningResourceRead] = Field(default_factory=list)


class LearningRoadmapProgress(BaseModel):
    completed: int
    total: int


class LearningRoadmapRead(BaseModel):
    """`GET/POST /api/v1/learning-roadmap*` (docs/API.md §5, Phase 10). `items`/`resources`/
    `progress` aren't ORM relationships resolved via a single `from_attributes` call — the route
    builds this explicitly from `LearningPath` + a fresh, ordered `LearningPathItem` query +
    curated `SkillLearningResource` lookups, since `phase`/`order_index`/resources need the
    joins `app/services/learning_roadmap.py` performs, not lazy-loaded relationship access."""

    id: uuid.UUID
    target_role: str
    career_path: CareerPathRead
    overview: str | None
    status: LearningPathStatus
    generated_at: datetime | None
    items: list[LearningPathItemRead] = Field(default_factory=list)
    progress: LearningRoadmapProgress


class LearningPathItemUpdate(BaseModel):
    completed: bool
