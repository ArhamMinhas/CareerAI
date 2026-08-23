import uuid

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


class SkillDetailRead(SkillRead):
    """`/api/v1/skills/{id_or_slug}` and the public `/skills/[slug]` page (docs/SEO.md §1).
    `related_skills`/`career_paths` aren't ORM relationships — populated by the route after
    validation (app/services/skills.py). `seo_summary`, `related_skills`, and `career_paths`
    are commonly empty: most skills (user-entered/resume-extracted) have no curated content or
    career-path association, only the ones seeded for `/skills/[slug]` do."""

    seo_summary: str | None
    synonyms: list[str] | None
    related_skills: list[SkillRead] = Field(default_factory=list)
    career_paths: list[SkillCareerPathRef] = Field(default_factory=list)
