import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.skill import SkillRead


class CareerPathRead(BaseModel):
    """List-view projection — `/api/v1/careers` and the public `/careers` index page."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    title: str
    summary: str
    related_job_titles: list[str] | None


class CareerPathSkillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill: SkillRead
    weight: int
    is_core: bool


class CareerPathDetailRead(CareerPathRead):
    """`/api/v1/careers/{slug}` and the public `/careers/[slug]` page. `related_career_paths`
    isn't an ORM relationship — it's populated by the route after validation, via embedding
    cosine similarity (app/services/career_paths.py)."""

    description_md: str
    required_skills: list[CareerPathSkillRead]
    related_career_paths: list[CareerPathRead] = Field(default_factory=list)
