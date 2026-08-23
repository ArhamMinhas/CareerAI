import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.job import JobRead


class JobMatchSubScore(BaseModel):
    """One weighted component of the hybrid match formula (docs/ML_PIPELINE.md §2.2). `score`
    is normalized 0-100 like resume scoring's `SubScore` (app/schemas/resume.py); `weight` is
    the fraction of `JobMatchRead.match_score` this component contributes (0.35, 0.25, ...)."""

    score: float = Field(ge=0, le=100)
    weight: float = Field(ge=0, le=1)
    explanation: str


class JobMatchBreakdown(BaseModel):
    """The six components of `job_match_score` (docs/ML_PIPELINE.md §2.2), stored verbatim as
    `JobMatch.score_breakdown` JSONB and reshaped into this typed model on read."""

    semantic_similarity: JobMatchSubScore
    skill_overlap: JobMatchSubScore
    experience_match: JobMatchSubScore
    education_match: JobMatchSubScore
    preference_match: JobMatchSubScore
    location_match: JobMatchSubScore


class JobMatchRead(BaseModel):
    """`POST /api/v1/jobs/match` and `GET /api/v1/jobs/matches` — the dashboard's ranked
    `/dashboard/matches` view. `id` here is the `JobMatch` row id, not the job's id (that's
    nested under `job.id`)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job: JobRead
    match_score: float
    score_breakdown: JobMatchBreakdown
    explanation: str


class JobFitRead(BaseModel):
    """`GET /api/v1/jobs/{id}/match` — a live per-job fit score for a job a user is looking at
    directly (search results, job detail page), not persisted as a `JobMatch` row the way the
    batch `/matches` dashboard is."""

    match_score: float
    score_breakdown: JobMatchBreakdown
    explanation: str
