import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.company import CompanyRead
from app.schemas.skill import SkillRead


class JobRead(BaseModel):
    """List-view projection — `GET /api/v1/jobs`, and nested inside company/match responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    company: CompanyRead
    seniority_level: str | None
    employment_type: str | None
    location: str | None
    remote: bool
    salary_min: float | None
    salary_max: float | None
    currency: str | None
    posted_at: datetime


class JobSkillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill: SkillRead
    is_required: bool
    weight: int


class JobDetailRead(JobRead):
    """`GET /api/v1/jobs/{id}` and the public `/jobs/[id]` page."""

    description: str
    required_skills: list[JobSkillRead] = Field(default_factory=list)


class CompanyDetailRead(CompanyRead):
    """`GET /api/v1/companies/{slug}` and the public `/companies/[slug]` page (docs/DATABASE.md
    §2.3's `/companies/[id]` intent, routed by slug instead — see `Company`'s docstring for
    why). Lives here rather than in `app/schemas/company.py` because it nests `JobRead`, and
    `company.py` must stay dependency-free so `JobRead` (above) can import `CompanyRead` from
    it — same one-directional-dependency shape as `CareerPathDetailRead`/`SkillDetailRead`.
    `jobs` isn't an ORM relationship — populated by the route after validation, filtered to
    this company's currently-active postings only."""

    jobs: list[JobRead] = Field(default_factory=list)
