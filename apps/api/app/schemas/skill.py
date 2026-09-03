import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class SkillRead(BaseModel):
    """Taxonomy entry — used for the `/skills?q=` autocomplete backing manual skill entry, and
    nested inside career-path/skill-gap responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    category: str | None


class SkillCareerPathRef(BaseModel):
    """A lean cross-link back to a career path that requires this skill — a minimal projection
    (not the full `CareerPathRead`) to avoid a circular import between this module and
    app/schemas/career_path.py, which already imports `SkillRead` from here."""

    model_config = ConfigDict(from_attributes=True)

    slug: str
    title: str


class SkillDemandPoint(BaseModel):
    """One real weekly `skill_demand` observation (docs/ML_PIPELINE.md §3 model 6, Phase 8)."""

    model_config = ConfigDict(from_attributes=True)

    period: date
    demand_count: int
    growth_rate: float | None


class SkillDetailRead(SkillRead):
    """`/api/v1/skills/{id_or_slug}` and the public `/skills/[slug]` page (docs/SEO.md §1).
    `related_skills`/`career_paths` aren't ORM relationships — populated by the route after
    validation (app/services/skills.py). `seo_summary`, `related_skills`, and `career_paths`
    are commonly empty: most skills (user-entered/resume-extracted) have no curated content or
    career-path association, only the ones seeded for `/skills/[slug]` do.

    `skill_family`/`demand_history`/`demand_forecast` are Phase 8 additions, populated by the
    route from `app.ml.inference` rather than ORM relationships — `null`/empty when the
    underlying model/data isn't available for this skill (e.g. no embedding, too little demand
    history), never a placeholder value."""

    seo_summary: str | None
    synonyms: list[str] | None
    related_skills: list[SkillRead] = Field(default_factory=list)
    career_paths: list[SkillCareerPathRef] = Field(default_factory=list)
    skill_family: str | None = Field(
        default=None,
        description="Cluster-derived family name (docs/ML_PIPELINE.md §3 model 3, Phase 8).",
    )
    demand_history: list[SkillDemandPoint] = Field(default_factory=list)
    demand_forecast: float | None = Field(
        default=None, description="Next-period forecast (model 6, Phase 8)."
    )
