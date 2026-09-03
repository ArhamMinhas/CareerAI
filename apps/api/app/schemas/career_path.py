import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.skill import SkillRead


class CareerPathRead(BaseModel):
    """List-view projection — `/api/v1/careers`, the public `/careers` index page, and
    `sitemap.ts` (which needs `updated_at` for a real `lastModified` — see docs/SEO.md;
    added in Phase 9 alongside the same fix for `ResourceRead`, replacing what had been a
    hardcoded `new Date()` in the sitemap for this content type)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    title: str
    summary: str
    related_job_titles: list[str] | None
    updated_at: datetime


class CareerPathSkillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill: SkillRead
    weight: int
    is_core: bool


class PredictedSalaryRange(BaseModel):
    """Model 4's output (docs/ML_PIPELINE.md §3, Phase 8) — p50 is the trained model's point
    prediction, p25/p75 a symmetric spread around it (app/ml/inference.py's docstring). Assumes
    US, mid-level, remote-agnostic — a `CareerPath` has no real region/seniority of its own the
    way a `Job` posting does, so this is one default-scope estimate, not a full breakdown."""

    p25: float
    p50: float
    p75: float
    assumed_scope: str = "US, mid-level, remote-agnostic"


class CareerRecommendationRead(BaseModel):
    """`GET /api/v1/career-recommendations` (docs/ML_PIPELINE.md §3 model 2, Phase 8) — ranked by
    resume-to-career-path embedding cosine similarity, not the trained model (see that service
    module's docstring for why)."""

    career_path: CareerPathRead
    fit_score: float = Field(
        description="Cosine similarity between resume and career-path embeddings (-1 to 1 in "
        "theory; real embeddings are practically almost always positive)."
    )


class CareerPathDetailRead(CareerPathRead):
    """`/api/v1/careers/{slug}` and the public `/careers/[slug]` page. `related_career_paths`
    isn't an ORM relationship — it's populated by the route after validation, via embedding
    cosine similarity (app/services/career_paths.py). `predicted_salary_range` is `None` when
    the model artifact isn't available or this path's category has too little real salary data
    for even the baseline lookup to be defined (app/ml/inference.py::predict_salary_range)."""

    description_md: str
    required_skills: list[CareerPathSkillRead]
    related_career_paths: list[CareerPathRead] = Field(default_factory=list)
    predicted_salary_range: PredictedSalaryRange | None = None
