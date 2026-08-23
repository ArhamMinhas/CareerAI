from pydantic import BaseModel, ConfigDict, Field

from app.models.skill_gap import GapLevel
from app.schemas.career_path import CareerPathRead
from app.schemas.skill import SkillRead


class SkillGapItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill: SkillRead
    gap_level: GapLevel
    priority: int


class SkillGapSummary(BaseModel):
    missing: int = 0
    weak: int = 0
    adequate: int = 0
    strong: int = 0


class SkillGapsResponse(BaseModel):
    """`GET /api/v1/skills/gaps` and `POST /api/v1/skills/gaps/refresh` (docs/API.md §5,
    docs/ML_PIPELINE.md §2.3). `gaps` covers every skill the target role requires; `recommended_
    next` is the same list filtered to missing/weak and sorted by priority, capped — the
    dashboard's "what to learn next" panel reads this directly rather than re-deriving it."""

    target_role: str
    career_path: CareerPathRead
    summary: SkillGapSummary
    gaps: list[SkillGapItemRead] = Field(default_factory=list)
    recommended_next: list[SkillGapItemRead] = Field(default_factory=list)
