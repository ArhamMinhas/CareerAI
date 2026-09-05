from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.resume import ResumeStatus


class SkillTrendPoint(BaseModel):
    """One skill's most-recent demand snapshot, catalog-wide (docs/API.md "### Analytics",
    Phase 12) — not the full per-period history `SkillDemandPoint` (app/schemas/skill.py)
    returns for a single skill's own detail page."""

    skill_id: UUID
    skill_name: str
    skill_slug: str
    demand_count: int
    growth_rate: float


class JobPostingTrendPoint(BaseModel):
    period: date
    total: int
    remote: int
    onsite: int


class SalaryTrendPoint(BaseModel):
    period: date
    average_p50: float


class TrendingCareerPath(BaseModel):
    """`growth_rate` is `None` when every one of this path's required skills has a `None`
    growth_rate (too little demand history) — never coerced to 0, which would misrepresent
    "unknown" as "flat"."""

    career_path_id: UUID
    career_path_slug: str
    career_path_title: str
    growth_rate: float | None


class MarketAnalyticsRead(BaseModel):
    """`GET /api/v1/analytics/market` (Phase 12) — catalog-wide, not personalized. Every list is
    empty (never fabricated) when the underlying aggregated data doesn't yet cover it."""

    top_growing_skills: list[SkillTrendPoint] = Field(default_factory=list)
    job_posting_trend: list[JobPostingTrendPoint] = Field(default_factory=list)
    salary_trend: list[SalaryTrendPoint] = Field(default_factory=list)
    trending_career_paths: list[TrendingCareerPath] = Field(default_factory=list)


class SkillAnalyticsRow(BaseModel):
    """One row of `GET /api/v1/analytics/skills` — the whole curated catalog, not one skill.
    `avg_associated_salary` is `None` when no job requiring this skill has a matching
    `SalaryData` row yet (an honest average of real data, not a fabricated correlation)."""

    skill_id: UUID
    skill_name: str
    skill_slug: str
    demand_count: int | None
    growth_rate: float | None
    avg_associated_salary: float | None


class SkillAnalyticsRead(BaseModel):
    rows: list[SkillAnalyticsRow] = Field(default_factory=list)


class DashboardResumeSummary(BaseModel):
    status: ResumeStatus | None
    overall_score: float | None


class DashboardSkillGapSummary(BaseModel):
    """`None` (the whole section, not per-field) when the user has no active `CareerGoal` or no
    gaps computed yet — this route never triggers computation itself (see
    `app/services/analytics.py`'s module docstring for why)."""

    target_role: str
    missing: int
    weak: int
    adequate: int
    strong: int


class DashboardInterviewSummary(BaseModel):
    total_completed: int
    average_overall_score: float | None


class DashboardRoadmapSummary(BaseModel):
    target_role: str
    completed_items: int
    total_items: int


class DashboardApplicationFunnel(BaseModel):
    total_matches: int
    saved: int = 0
    applied: int = 0
    interviewing: int = 0
    offer: int = 0
    rejected: int = 0


class CandidateDashboardRead(BaseModel):
    """`GET /api/v1/analytics/dashboard` (Phase 12) — a real rollup of the current user's own
    already-computed state across every other feature, never a trigger to compute new state.
    Each section is `None`/zeroed independently when that feature has no data yet for this user
    — a brand-new user sees an honestly empty dashboard, not an error."""

    resume: DashboardResumeSummary
    skill_gaps: DashboardSkillGapSummary | None
    interviews: DashboardInterviewSummary
    roadmap: DashboardRoadmapSummary | None
    applications: DashboardApplicationFunnel


__all__ = [
    "CandidateDashboardRead",
    "DashboardApplicationFunnel",
    "DashboardInterviewSummary",
    "DashboardResumeSummary",
    "DashboardRoadmapSummary",
    "DashboardSkillGapSummary",
    "JobPostingTrendPoint",
    "MarketAnalyticsRead",
    "SalaryTrendPoint",
    "SkillAnalyticsRead",
    "SkillAnalyticsRow",
    "SkillTrendPoint",
    "TrendingCareerPath",
]
