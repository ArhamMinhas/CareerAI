import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career_path import CareerPath
from app.models.market_data import SkillDemand
from app.models.profile import Profile
from app.models.skill import Proficiency, UserSkill
from app.models.skill_gap import GapLevel, SkillGap
from app.models.user import User

# A single week-over-week `growth_rate` swing can be noisy even above
# `aggregate_market_data.py`'s MIN_PERIOD_COUNT floor — this caps how much it can move priority
# in either direction, so one spiky week never dominates the weight/core-ness signal it's
# blended with.
_GROWTH_RATE_FLOOR = -0.5
_GROWTH_RATE_CEILING = 2.0

_PROFICIENCY_TO_GAP_LEVEL: dict[Proficiency, GapLevel] = {
    Proficiency.BEGINNER: GapLevel.WEAK,
    Proficiency.INTERMEDIATE: GapLevel.ADEQUATE,
    Proficiency.ADVANCED: GapLevel.STRONG,
    Proficiency.EXPERT: GapLevel.STRONG,
}


def _priority(
    weight: int, is_core: bool, gap_level: GapLevel, growth_rate: float | None = None
) -> int:
    """Higher = more urgent to learn (docs/ML_PIPELINE.md §2.3). Only MISSING/WEAK skills are
    ever surfaced as "recommended next" (app/schemas/skill_gap.py), but every required skill
    still gets a priority so the full gap list sorts consistently. `is_core` doubles the base
    weight — a core skill always outranks an equally-weighted non-core one — and MISSING always
    outranks WEAK at the same weight/core-ness, since having *none* of a required skill is
    always more urgent than having some of it.

    `growth_rate` (docs/ML_PIPELINE.md §2.3's Phase 8 follow-up, `SkillDemand.growth_rate`) scales
    the base priority once real demand data exists for this skill — `None` when there isn't
    (thin data; see `app/scripts/aggregate_market_data.py`'s `MIN_PERIOD_COUNT`), in which case
    this is a no-op, not a zero-growth assumption. Clamped to [-0.5, 2.0] so one noisy week-over-
    week swing can't dominate weight/core-ness, which stays a real signal even where demand data
    is thin."""
    if gap_level in (GapLevel.ADEQUATE, GapLevel.STRONG):
        return 0
    base = weight * (2 if is_core else 1)
    priority = base * 2 if gap_level == GapLevel.MISSING else base
    if growth_rate is not None:
        clamped = max(_GROWTH_RATE_FLOOR, min(_GROWTH_RATE_CEILING, growth_rate))
        priority = round(priority * (1 + clamped))
    return priority


async def compute_and_store_skill_gaps(
    db: AsyncSession, *, user: User, career_path: CareerPath
) -> list[SkillGap]:
    """Deterministic set comparison between the user's claimed skills and `career_path`'s
    required-skill profile — no LLM call (docs/AI_ARCHITECTURE.md §1). Takes an already-resolved
    `CareerPath` rather than a raw `target_role` string: every caller needs the resolved path
    for its own response anyway, so resolving twice (once at the call site, once in here) was
    just a wasted query. Replaces any previously-stored gaps for this user+career path with a
    fresh computation. Does not commit — callers own the transaction.

    The delete-then-insert runs inside a SAVEPOINT: two concurrent calls for the same
    user+career-path (e.g. a page firing this on load in two tabs, or GET's auto-compute racing
    a POST /refresh) would otherwise both see "no rows yet" and both try to insert the same
    `(user_id, skill_id, target_role)` rows, and the loser would crash with a duplicate-key
    `IntegrityError` — the same race already fixed for `get_current_user`
    (app/core/security.py). Since this computation is deterministic, the loser doesn't need to
    retry its own write — it just reads back whatever the winner already committed, which is
    guaranteed to be equivalent.
    """
    profile_result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    profile = profile_result.scalar_one_or_none()

    user_proficiency: dict[uuid.UUID, Proficiency] = {}
    if profile is not None:
        skills_result = await db.execute(
            select(UserSkill).where(UserSkill.profile_id == profile.id)
        )
        user_proficiency = {row.skill_id: row.proficiency for row in skills_result.scalars().all()}

    required_skill_ids = [required.skill_id for required in career_path.required_skills]
    growth_rates: dict[uuid.UUID, float] = {}
    if required_skill_ids:
        # Most recent period per skill only — a stale growth_rate from months ago shouldn't
        # still be nudging today's priority.
        latest_period_subq = (
            select(SkillDemand.skill_id, func.max(SkillDemand.period).label("latest_period"))
            .where(SkillDemand.skill_id.in_(required_skill_ids))
            .group_by(SkillDemand.skill_id)
            .subquery()
        )
        demand_result = await db.execute(
            select(SkillDemand.skill_id, SkillDemand.growth_rate).join(
                latest_period_subq,
                (SkillDemand.skill_id == latest_period_subq.c.skill_id)
                & (SkillDemand.period == latest_period_subq.c.latest_period),
            )
        )
        growth_rates = {
            row.skill_id: float(row.growth_rate)
            for row in demand_result.all()
            if row.growth_rate is not None
        }

    gaps: list[SkillGap] = []
    for required in career_path.required_skills:
        proficiency = user_proficiency.get(required.skill_id)
        gap_level = (
            _PROFICIENCY_TO_GAP_LEVEL[proficiency] if proficiency is not None else GapLevel.MISSING
        )
        gap = SkillGap(
            user_id=user.id,
            skill_id=required.skill_id,
            target_role=career_path.slug,
            gap_level=gap_level,
            priority=_priority(
                required.weight,
                required.is_core,
                gap_level,
                growth_rates.get(required.skill_id),
            ),
        )
        # `required.skill` is already loaded (CareerPathSkill.skill is `lazy="selectin"`) —
        # assigning it directly avoids an extra per-row query to populate `gap.skill` for
        # serialization, which a bare `flush()` on a freshly-constructed object wouldn't do
        # (selectin only fires for objects loaded via a SELECT, not fresh inserts).
        gap.skill = required.skill
        gaps.append(gap)

    try:
        async with db.begin_nested():
            await db.execute(
                delete(SkillGap).where(
                    SkillGap.user_id == user.id, SkillGap.target_role == career_path.slug
                )
            )
            db.add_all(gaps)
            await db.flush()
    except IntegrityError:
        return await get_stored_skill_gaps(db, user_id=user.id, career_path_slug=career_path.slug)
    return gaps


async def get_stored_skill_gaps(
    db: AsyncSession, *, user_id: uuid.UUID, career_path_slug: str
) -> list[SkillGap]:
    result = await db.execute(
        select(SkillGap)
        .where(SkillGap.user_id == user_id, SkillGap.target_role == career_path_slug)
        .order_by(SkillGap.priority.desc())
    )
    return list(result.scalars().all())
