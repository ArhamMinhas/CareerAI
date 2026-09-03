"""Populates `skill_demand`/`salary_data` (docs/DATABASE.md §2.5, docs/ROADMAP.md Phase 8) from
real `jobs`/`job_skills` data — feeds model 4's baseline (median salary lookup) and model 6's
training data (docs/ML_PIPELINE.md §3).

Both tables bucket by ISO week (`date_trunc('week', posted_at)`), with no `region` dimension —
see `app/models/market_data.py`'s docstrings for why. `SalaryData.job_title` stores the
normalized `jobs.search_category` value, not the literal raw posting title: exact titles are
almost all distinct at this data volume (~550 jobs), so a percentile over a near-singleton group
is meaningless — `search_category` groups give up to ~50 postings per period, enough for a real
p25/p50/p75. Revisit once there's enough volume per exact title to make literal-title grouping
meaningful.

`SkillDemand.growth_rate` is left `NULL` (not computed as a noisy near-zero-N ratio) for any
skill whose *prior* period's `demand_count` is below `MIN_PERIOD_COUNT` — see
app/services/skill_gap.py's `_priority()`, which reads this same threshold before blending
`growth_rate` in.

Idempotent: replaces this run's period rows rather than accumulating duplicates.

Run from apps/api with the venv active (or `docker exec careerai-api-1 python -m
app.scripts.aggregate_market_data`):

    python -m app.scripts.aggregate_market_data
"""

import asyncio
import statistics
import uuid
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import AsyncSessionLocal, engine
from app.models.job import Job, JobSkill
from app.models.market_data import SalaryData, SkillDemand

MIN_PERIOD_COUNT = 3


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


async def _aggregate_salary_data(db: AsyncSession) -> int:
    result = await db.execute(
        select(
            Job.search_category,
            Job.seniority_level,
            Job.posted_at,
            Job.salary_min,
            Job.salary_max,
            Job.currency,
        ).where(
            Job.salary_min.is_not(None),
            Job.salary_max.is_not(None),
            Job.search_category.is_not(None),
        )
    )
    rows = result.all()

    groups: dict[tuple[str, str | None, date], list[float]] = defaultdict(list)
    currencies: dict[tuple[str, str | None, date], str | None] = {}
    for category, seniority, posted_at, salary_min, salary_max, currency in rows:
        period = _week_start(posted_at.date())
        key = (category, seniority, period)
        groups[key].append((float(salary_min) + float(salary_max)) / 2)
        currencies[key] = currency

    await db.execute(delete(SalaryData))
    count = 0
    for (category, seniority, period), midpoints in groups.items():
        midpoints.sort()
        db.add(
            SalaryData(
                job_title=category,
                seniority_level=seniority,
                p25=statistics.quantiles(midpoints, n=4)[0]
                if len(midpoints) >= 2
                else midpoints[0],
                p50=statistics.median(midpoints),
                p75=statistics.quantiles(midpoints, n=4)[2]
                if len(midpoints) >= 2
                else midpoints[0],
                currency=currencies[(category, seniority, period)],
                period=period,
            )
        )
        count += 1
    return count


async def _aggregate_skill_demand(db: AsyncSession) -> int:
    result = await db.execute(
        select(JobSkill.skill_id, Job.posted_at).join(Job, Job.id == JobSkill.job_id)
    )
    rows = result.all()

    counts: dict[tuple[uuid.UUID, date], int] = defaultdict(int)
    for skill_id, posted_at in rows:
        counts[(skill_id, _week_start(posted_at.date()))] += 1

    await db.execute(delete(SkillDemand))
    count = 0
    for (skill_id, period), demand_count in counts.items():
        prior_period = period - timedelta(days=7)
        prior_count = counts.get((skill_id, prior_period))
        growth_rate = None
        if prior_count is not None and prior_count >= MIN_PERIOD_COUNT:
            growth_rate = (demand_count - prior_count) / prior_count
        db.add(
            SkillDemand(
                skill_id=skill_id, demand_count=demand_count, growth_rate=growth_rate, period=period
            )
        )
        count += 1
    return count


async def run() -> None:
    await engine.dispose()
    async with AsyncSessionLocal() as db:
        salary_rows = await _aggregate_salary_data(db)
        demand_rows = await _aggregate_skill_demand(db)
        await db.commit()
        print(f"wrote {salary_rows} salary_data rows, {demand_rows} skill_demand rows")


if __name__ == "__main__":
    asyncio.run(run())
