"""Phase 12 — Career Analytics (docs/ROADMAP.md, docs/API.md "### Analytics"). Pure deterministic
SQL aggregation, zero LLM calls (docs/AI_ARCHITECTURE.md §8 has no Analytics agent) — every
number here is computed, never generated.

Market/skill analytics (A, B) are catalog-wide, not personalized, reading `SkillDemand`/
`SalaryData` (Phase 8) plus live aggregates over `jobs`/`career_path_skills`. The candidate
dashboard (C) is a strictly read-only rollup of the current user's *already-computed* state —
unlike `GET /skills/gaps`, it never triggers a fresh computation; a user who hasn't visited the
skill-gap/roadmap pages yet simply sees that section as `None`, not a surprise background write.
"""

import uuid
from collections import defaultdict
from datetime import date

from sqlalchemy import Date, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.selectable import Subquery

from app.models.career_goal import CareerGoal
from app.models.career_path import CareerPath, CareerPathSkill
from app.models.job import Job, JobSkill
from app.models.job_match import Application, ApplicationStatus, JobMatch
from app.models.learning_path import LearningPath
from app.models.market_data import SalaryData, SkillDemand
from app.models.resume import Resume
from app.models.skill import Skill
from app.models.skill_gap import GapLevel
from app.schemas.analytics import (
    CandidateDashboardRead,
    DashboardApplicationFunnel,
    DashboardInterviewSummary,
    DashboardResumeSummary,
    DashboardRoadmapSummary,
    DashboardSkillGapSummary,
    JobPostingTrendPoint,
    MarketAnalyticsRead,
    SalaryTrendPoint,
    SkillAnalyticsRead,
    SkillAnalyticsRow,
    SkillTrendPoint,
    TrendingCareerPath,
)
from app.scripts.aggregate_market_data import MIN_PERIOD_COUNT
from app.services.career_paths import CareerPathNotFoundError, resolve_career_path
from app.services.interviews import get_analytics as get_interview_analytics
from app.services.learning_roadmap import get_ordered_items
from app.services.skill_gap import get_stored_skill_gaps

_TOP_N_SKILLS = 10
_TOP_N_CAREER_PATHS = 10
DEFAULT_SKILL_ANALYTICS_LIMIT = 50

_VALID_SKILL_SORTS = ("growth_rate", "demand_count", "avg_associated_salary")


# --- A. Market analytics ------------------------------------------------------------------------


async def get_market_analytics(
    db: AsyncSession, *, date_from: date | None, date_to: date | None
) -> MarketAnalyticsRead:
    """`top_growing_skills`/`trending_career_paths` always reflect the truest *current* snapshot
    (each skill's latest period) regardless of `date_from`/`date_to` — a "what's trending right
    now" question doesn't have a sensible historical-range answer the way a time series does.
    `date_from`/`date_to` apply to the two genuine time series (`job_posting_trend`,
    `salary_trend`) only."""
    return MarketAnalyticsRead(
        top_growing_skills=await _top_growing_skills(db),
        job_posting_trend=await _job_posting_trend(db, date_from=date_from, date_to=date_to),
        salary_trend=await _salary_trend(db, date_from=date_from, date_to=date_to),
        trending_career_paths=await _trending_career_paths(db),
    )


def _latest_skill_demand_period_subq() -> Subquery:
    return (
        select(SkillDemand.skill_id, func.max(SkillDemand.period).label("latest_period"))
        .group_by(SkillDemand.skill_id)
        .subquery()
    )


async def _top_growing_skills(db: AsyncSession) -> list[SkillTrendPoint]:
    """Eligible only when the *current* period's `demand_count` also clears `MIN_PERIOD_COUNT` —
    `aggregate_market_data.py`'s own guard only checks the *prior* period before computing
    `growth_rate` at all, so a skill that fell to a thin current period (e.g. `demand_count=1`)
    can still carry a real-looking but noisy rate. A "top growing skills" headline list is far
    more visible than `skill_gap.py`'s blended priority score, so this extra floor matters here
    specifically."""
    latest_period_subq = _latest_skill_demand_period_subq()
    result = await db.execute(
        select(SkillDemand, Skill.name, Skill.slug)
        .join(Skill, Skill.id == SkillDemand.skill_id)
        .join(
            latest_period_subq,
            (SkillDemand.skill_id == latest_period_subq.c.skill_id)
            & (SkillDemand.period == latest_period_subq.c.latest_period),
        )
        .where(
            SkillDemand.growth_rate.is_not(None),
            SkillDemand.demand_count >= MIN_PERIOD_COUNT,
        )
        .order_by(SkillDemand.growth_rate.desc())
        .limit(_TOP_N_SKILLS)
    )
    return [
        SkillTrendPoint(
            skill_id=row.SkillDemand.skill_id,
            skill_name=row.name,
            skill_slug=row.slug,
            demand_count=row.SkillDemand.demand_count,
            growth_rate=float(row.SkillDemand.growth_rate),
        )
        for row in result.all()
    ]


async def _job_posting_trend(
    db: AsyncSession, *, date_from: date | None, date_to: date | None
) -> list[JobPostingTrendPoint]:
    """Computed live over `jobs` (no new table — ~550-600 rows, cheap). `date_trunc('week', ...)`
    truncates to the Monday of the ISO week, matching `aggregate_market_data.py`'s own
    `_week_start` bucketing exactly, so this trend's periods line up with `salary_trend`'s."""
    period_expr = func.date_trunc("week", Job.posted_at).cast(Date)
    stmt = (
        select(
            period_expr.label("period"),
            func.count().label("total"),
            func.count().filter(Job.remote.is_(True)).label("remote"),
        )
        .where(Job.is_active.is_(True))
        .group_by(period_expr)
        .order_by(period_expr)
    )
    if date_from is not None:
        stmt = stmt.where(Job.posted_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Job.posted_at <= date_to)
    result = await db.execute(stmt)
    return [
        JobPostingTrendPoint(
            period=row.period, total=row.total, remote=row.remote, onsite=row.total - row.remote
        )
        for row in result.all()
    ]


async def _salary_trend(
    db: AsyncSession, *, date_from: date | None, date_to: date | None
) -> list[SalaryTrendPoint]:
    stmt = (
        select(SalaryData.period, func.avg(SalaryData.p50).label("average_p50"))
        .group_by(SalaryData.period)
        .order_by(SalaryData.period)
    )
    if date_from is not None:
        stmt = stmt.where(SalaryData.period >= date_from)
    if date_to is not None:
        stmt = stmt.where(SalaryData.period <= date_to)
    result = await db.execute(stmt)
    return [
        SalaryTrendPoint(period=row.period, average_p50=float(row.average_p50))
        for row in result.all()
    ]


async def _trending_career_paths(db: AsyncSession) -> list[TrendingCareerPath]:
    """Ranks only paths with at least one required skill carrying a non-null `growth_rate` —
    averaging over non-null values only, never coercing a missing rate to 0 (that would falsely
    rank a thin-data path as "flat" instead of "unknown"). A path with zero eligible skills is
    excluded from the ranking entirely, not shown with a fabricated `growth_rate: 0`."""
    latest_period_subq = _latest_skill_demand_period_subq()
    growth_result = await db.execute(
        select(SkillDemand.skill_id, SkillDemand.growth_rate).join(
            latest_period_subq,
            (SkillDemand.skill_id == latest_period_subq.c.skill_id)
            & (SkillDemand.period == latest_period_subq.c.latest_period),
        )
    )
    growth_by_skill: dict[uuid.UUID, float] = {
        row.skill_id: float(row.growth_rate)
        for row in growth_result.all()
        if row.growth_rate is not None
    }

    paths_result = await db.execute(select(CareerPath).where(CareerPath.published.is_(True)))
    paths = list(paths_result.scalars().all())

    required_skills_result = await db.execute(
        select(CareerPathSkill.career_path_id, CareerPathSkill.skill_id)
    )
    skills_by_path: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    for row in required_skills_result.all():
        skills_by_path[row.career_path_id].append(row.skill_id)

    scored: list[TrendingCareerPath] = []
    for path in paths:
        rates = [
            growth_by_skill[skill_id]
            for skill_id in skills_by_path.get(path.id, [])
            if skill_id in growth_by_skill
        ]
        avg_rate = sum(rates) / len(rates) if rates else None
        scored.append(
            TrendingCareerPath(
                career_path_id=path.id,
                career_path_slug=path.slug,
                career_path_title=path.title,
                growth_rate=avg_rate,
            )
        )

    ranked = sorted(
        (path for path in scored if path.growth_rate is not None),
        key=lambda path: path.growth_rate,  # type: ignore[arg-type,return-value]
        reverse=True,
    )
    return ranked[:_TOP_N_CAREER_PATHS]


# --- B. Skill analytics --------------------------------------------------------------------------


async def get_skill_analytics(db: AsyncSession, *, sort: str, limit: int) -> SkillAnalyticsRead:
    skills_result = await db.execute(select(Skill.id, Skill.name, Skill.slug))
    skills = list(skills_result.all())

    latest_period_subq = _latest_skill_demand_period_subq()
    demand_result = await db.execute(
        select(SkillDemand.skill_id, SkillDemand.demand_count, SkillDemand.growth_rate).join(
            latest_period_subq,
            (SkillDemand.skill_id == latest_period_subq.c.skill_id)
            & (SkillDemand.period == latest_period_subq.c.latest_period),
        )
    )
    demand_by_skill = {
        row.skill_id: (row.demand_count, row.growth_rate) for row in demand_result.all()
    }

    salary_by_skill = await _avg_associated_salary_by_skill(db)

    rows = []
    for skill_id, name, slug in skills:
        demand_count, growth_rate = demand_by_skill.get(skill_id, (None, None))
        rows.append(
            SkillAnalyticsRow(
                skill_id=skill_id,
                skill_name=name,
                skill_slug=slug,
                demand_count=demand_count,
                growth_rate=float(growth_rate) if growth_rate is not None else None,
                avg_associated_salary=salary_by_skill.get(skill_id),
            )
        )

    sort_key_fn = {
        "growth_rate": lambda r: (r.growth_rate is not None, r.growth_rate or 0.0),
        "demand_count": lambda r: (r.demand_count is not None, r.demand_count or 0),
        "avg_associated_salary": lambda r: (
            r.avg_associated_salary is not None,
            r.avg_associated_salary or 0.0,
        ),
    }[sort if sort in _VALID_SKILL_SORTS else "demand_count"]
    rows.sort(key=sort_key_fn, reverse=True)

    return SkillAnalyticsRead(rows=rows[:limit])


async def _avg_associated_salary_by_skill(db: AsyncSession) -> dict[uuid.UUID, float]:
    """Two real bugs fixed here versus a naive join (caught by Plan-agent critique): (1) joining
    straight through `Job` fans out per matching job row, not per distinct (category, seniority)
    combo — a skill required by 10 jobs in the same category would count that category's `p50`
    ten times. Fixed by deduplicating `(skill_id, category, seniority)` triples before ever
    touching `SalaryData`. (2) `seniority_level` is nullable on both sides — a plain `=` silently
    drops every NULL-seniority match (`NULL = NULL` is false in SQL); fixed with
    `is_not_distinct_from`. Also restricts to each `(category, seniority)`'s most-recent period
    only, same "latest period wins" reasoning as `skill_gap.py`."""
    distinct_pairs_subq = (
        select(
            JobSkill.skill_id.label("skill_id"),
            Job.search_category.label("category"),
            Job.seniority_level.label("seniority"),
        )
        .join(Job, Job.id == JobSkill.job_id)
        .where(Job.search_category.is_not(None))
        .distinct()
        .subquery()
    )

    latest_salary_period_subq = (
        select(
            SalaryData.job_title,
            SalaryData.seniority_level,
            func.max(SalaryData.period).label("latest_period"),
        )
        .group_by(SalaryData.job_title, SalaryData.seniority_level)
        .subquery()
    )
    latest_salary_subq = (
        select(SalaryData.job_title, SalaryData.seniority_level, SalaryData.p50)
        .join(
            latest_salary_period_subq,
            (SalaryData.job_title == latest_salary_period_subq.c.job_title)
            & (
                SalaryData.seniority_level.is_not_distinct_from(
                    latest_salary_period_subq.c.seniority_level
                )
            )
            & (SalaryData.period == latest_salary_period_subq.c.latest_period),
        )
        .subquery()
    )

    result = await db.execute(
        select(distinct_pairs_subq.c.skill_id, func.avg(latest_salary_subq.c.p50).label("avg_p50"))
        .join(
            latest_salary_subq,
            (distinct_pairs_subq.c.category == latest_salary_subq.c.job_title)
            & (
                distinct_pairs_subq.c.seniority.is_not_distinct_from(
                    latest_salary_subq.c.seniority_level
                )
            ),
        )
        .group_by(distinct_pairs_subq.c.skill_id)
    )
    return {row.skill_id: float(row.avg_p50) for row in result.all()}


# --- C. Candidate dashboard -----------------------------------------------------------------------


async def get_candidate_dashboard(
    db: AsyncSession, *, user_id: uuid.UUID
) -> CandidateDashboardRead:
    return CandidateDashboardRead(
        resume=await _resume_summary(db, user_id=user_id),
        skill_gaps=await _skill_gap_summary(db, user_id=user_id),
        interviews=await _interview_summary(db, user_id=user_id),
        roadmap=await _roadmap_summary(db, user_id=user_id),
        applications=await _application_funnel(db, user_id=user_id),
    )


async def _resume_summary(db: AsyncSession, *, user_id: uuid.UUID) -> DashboardResumeSummary:
    result = await db.execute(
        select(Resume.status, Resume.overall_score)
        .where(Resume.user_id == user_id, Resume.deleted_at.is_(None))
        .order_by(Resume.created_at.desc())
        .limit(1)
    )
    row = result.first()
    if row is None:
        return DashboardResumeSummary(status=None, overall_score=None)
    return DashboardResumeSummary(
        status=row.status,
        overall_score=float(row.overall_score) if row.overall_score is not None else None,
    )


async def _skill_gap_summary(
    db: AsyncSession, *, user_id: uuid.UUID
) -> DashboardSkillGapSummary | None:
    """Read-only — never computes gaps that don't already exist (unlike `GET /skills/gaps`'s
    auto-compute-on-read). `CareerGoal.is_active` has no DB-level uniqueness (a user can have 2+
    "active" goals), so this picks the most recently created one rather than
    `scalar_one_or_none()`, which would crash — same precedent as `job_matching.py`'s own
    active-goal resolution."""
    goal_result = await db.execute(
        select(CareerGoal)
        .where(CareerGoal.user_id == user_id, CareerGoal.is_active.is_(True))
        .order_by(CareerGoal.created_at.desc())
    )
    goal = goal_result.scalars().first()
    if goal is None:
        return None

    try:
        career_path = await resolve_career_path(db, goal.target_role)
    except CareerPathNotFoundError:
        return None

    gaps = await get_stored_skill_gaps(db, user_id=user_id, career_path_slug=career_path.slug)
    if not gaps:
        return None

    counts = dict.fromkeys(GapLevel, 0)
    for gap in gaps:
        counts[gap.gap_level] += 1
    return DashboardSkillGapSummary(
        target_role=career_path.slug,
        missing=counts[GapLevel.MISSING],
        weak=counts[GapLevel.WEAK],
        adequate=counts[GapLevel.ADEQUATE],
        strong=counts[GapLevel.STRONG],
    )


async def _interview_summary(db: AsyncSession, *, user_id: uuid.UUID) -> DashboardInterviewSummary:
    data = await get_interview_analytics(db, user_id=user_id)
    return DashboardInterviewSummary(
        total_completed=data.total_completed, average_overall_score=data.average_overall_score
    )


async def _roadmap_summary(
    db: AsyncSession, *, user_id: uuid.UUID
) -> DashboardRoadmapSummary | None:
    """No existing "get a user's current roadmap" helper fits here — `learning_roadmap.py`'s
    `get_learning_path` requires an already-known `target_role`, and a user can have multiple
    roadmaps (one per role, per the partial-unique index). Shows the most-recently-*updated*
    roadmap — real recent activity — rather than trying to match whatever the user's active
    `CareerGoal` happens to be, which may not have a roadmap at all or may point to a stale one."""
    result = await db.execute(
        select(LearningPath)
        .where(LearningPath.user_id == user_id, LearningPath.deleted_at.is_(None))
        .order_by(LearningPath.updated_at.desc())
        .limit(1)
    )
    path = result.scalar_one_or_none()
    if path is None:
        return None

    items = await get_ordered_items(db, path.id)
    completed = sum(1 for item in items if item.completed)
    return DashboardRoadmapSummary(
        target_role=path.target_role, completed_items=completed, total_items=len(items)
    )


async def _application_funnel(
    db: AsyncSession, *, user_id: uuid.UUID
) -> DashboardApplicationFunnel:
    matches_result = await db.execute(
        select(func.count()).select_from(JobMatch).where(JobMatch.user_id == user_id)
    )
    total_matches = matches_result.scalar_one()

    status_result = await db.execute(
        select(Application.status, func.count())
        .where(Application.user_id == user_id, Application.deleted_at.is_(None))
        .group_by(Application.status)
    )
    counts: dict[ApplicationStatus, int] = dict(status_result.all())  # type: ignore[arg-type]
    return DashboardApplicationFunnel(
        total_matches=total_matches,
        saved=counts.get(ApplicationStatus.SAVED, 0),
        applied=counts.get(ApplicationStatus.APPLIED, 0),
        interviewing=counts.get(ApplicationStatus.INTERVIEWING, 0),
        offer=counts.get(ApplicationStatus.OFFER, 0),
        rejected=counts.get(ApplicationStatus.REJECTED, 0),
    )
