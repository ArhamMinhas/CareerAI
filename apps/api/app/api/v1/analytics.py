from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.analytics import CandidateDashboardRead, MarketAnalyticsRead, SkillAnalyticsRead
from app.schemas.envelope import Envelope, meta_from_request
from app.services.analytics import (
    DEFAULT_SKILL_ANALYTICS_LIMIT,
    get_candidate_dashboard,
    get_market_analytics,
    get_skill_analytics,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])

UserDep = Annotated[User, Depends(get_current_user)]
DbDep = Annotated[AsyncSession, Depends(get_db)]

# All three routes are read-only, no LLM call (docs/AI_ARCHITECTURE.md §8 has no Analytics
# agent), so none needs an Idempotency-Key or rate limit. Kept behind auth for consistency with
# every other /dashboard/*-backing route, not because the underlying data is confidential —
# `GET /skills/{slug}` already publicly exposes one skill's full SkillDemand history
# unauthenticated, so the catalog-wide views here are already reconstructable without login.


@router.get("/market", response_model=Envelope[MarketAnalyticsRead])
async def get_market(
    request: Request,
    _user: UserDep,
    db: DbDep,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> Envelope[MarketAnalyticsRead]:
    """Catalog-wide skill/job/salary/career-path trends — not personalized. `date_from`/
    `date_to` filter the two genuine time series (`job_posting_trend`, `salary_trend`) only;
    `top_growing_skills`/`trending_career_paths` always reflect the current snapshot (see the
    service docstring)."""
    data = await get_market_analytics(db, date_from=date_from, date_to=date_to)
    return Envelope(data=data, meta=meta_from_request(request))


@router.get("/skills", response_model=Envelope[SkillAnalyticsRead])
async def get_skills(
    request: Request,
    _user: UserDep,
    db: DbDep,
    sort: str = Query(default="demand_count"),
    limit: int = Query(default=DEFAULT_SKILL_ANALYTICS_LIMIT, ge=1, le=200),
) -> Envelope[SkillAnalyticsRead]:
    """Catalog-wide per-skill table (demand, growth, associated salary) — broader than
    `GET /skills/{slug}`'s single-skill detail page. No cursor pagination: the skill catalog is
    curated/seeded (~66 rows), matching docs/API.md §1's "small, stable" exemption."""
    data = await get_skill_analytics(db, sort=sort, limit=limit)
    return Envelope(data=data, meta=meta_from_request(request))


@router.get("/dashboard", response_model=Envelope[CandidateDashboardRead])
async def get_dashboard(
    request: Request, user: UserDep, db: DbDep
) -> Envelope[CandidateDashboardRead]:
    """Personalized executive-overview payload — a real rollup of the current user's own
    already-computed state (resume, skill gaps, interviews, roadmap, job-search funnel), never a
    trigger to compute new state."""
    data = await get_candidate_dashboard(db, user_id=user.id)
    return Envelope(data=data, meta=meta_from_request(request))
