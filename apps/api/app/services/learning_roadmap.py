import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career_path import CareerPath
from app.models.learning_path import (
    LearningPath,
    LearningPathItem,
    LearningPathStatus,
    RoadmapPhase,
)
from app.models.resource import Resource
from app.models.skill import Skill
from app.models.skill_gap import GapLevel, SkillGap
from app.models.skill_learning_resource import SkillLearningResource
from app.models.skill_prerequisite import SkillPrerequisite
from app.models.user import User
from app.services.skill_gap import compute_and_store_skill_gaps, get_stored_skill_gaps

logger = logging.getLogger(__name__)

_GAP_LEVELS_NEEDING_WORK = (GapLevel.MISSING, GapLevel.WEAK)


@dataclass(frozen=True)
class SequencedSkill:
    """One skill's position in a freshly-computed roadmap sequence — the deterministic output of
    `generate_learning_path`, before any LLM narrative is layered on top of it
    (app/ai/roadmap_overview.py consumes this list directly to build its bounded prompt)."""

    skill: Skill
    gap_level: GapLevel
    phase: RoadmapPhase
    order_index: int


async def _fetch_prerequisite_edges(
    db: AsyncSession, skill_ids: set[uuid.UUID]
) -> list[tuple[uuid.UUID, uuid.UUID]]:
    """Only edges where *both* endpoints are in `skill_ids` — a prerequisite the user already
    has isn't part of the sequence, so it can't constrain it."""
    result = await db.execute(
        select(SkillPrerequisite.skill_id, SkillPrerequisite.requires_skill_id).where(
            SkillPrerequisite.skill_id.in_(skill_ids),
            SkillPrerequisite.requires_skill_id.in_(skill_ids),
        )
    )
    return [(row.skill_id, row.requires_skill_id) for row in result.all()]


def _topological_sort(
    skill_ids: list[uuid.UUID],
    edges: list[tuple[uuid.UUID, uuid.UUID]],
    priority_by_skill: dict[uuid.UUID, int],
) -> list[uuid.UUID]:
    """Kahn's algorithm — `docs/AI_ARCHITECTURE.md §8`'s Learning Planner guardrail requires
    prerequisite ordering to be computed deterministically, never decided by an LLM. Ties (no
    prerequisite edge between two ready skills) are broken by the existing skill-gap `_priority`
    value, descending — reused, not recomputed, from `app/services/skill_gap.py`.

    Cycle-defensive: real curated data shouldn't have one (`skill_prerequisites` is small,
    hand-curated content), but a topological sort over bad data must never infinite-loop or
    crash a request. If some skills can't be resolved (a cycle among them), they're appended
    afterward in priority-only order, with a logged warning — the roadmap still generates."""
    dependents: dict[uuid.UUID, list[uuid.UUID]] = {sid: [] for sid in skill_ids}
    in_degree: dict[uuid.UUID, int] = dict.fromkeys(skill_ids, 0)
    for skill_id, requires_skill_id in edges:
        dependents[requires_skill_id].append(skill_id)
        in_degree[skill_id] += 1

    def _priority_key(sid: uuid.UUID) -> tuple[int, str]:
        # Negative priority sorts descending; `sid.hex` is a deterministic, always-unique
        # tiebreaker for two skills with identical priority — never ambiguous ordering.
        return (-priority_by_skill.get(sid, 0), sid.hex)

    ready = sorted((sid for sid in skill_ids if in_degree[sid] == 0), key=_priority_key)
    result: list[uuid.UUID] = []

    while ready:
        current = ready.pop(0)
        result.append(current)
        newly_ready = []
        for dependent in dependents[current]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                newly_ready.append(dependent)
        if newly_ready:
            ready = sorted(ready + newly_ready, key=_priority_key)

    if len(result) != len(skill_ids):
        unresolved = [sid for sid in skill_ids if sid not in result]
        logger.warning(
            "Cycle detected in skill_prerequisites affecting %d skill(s); falling back to "
            "priority-only ordering for them.",
            len(unresolved),
        )
        unresolved.sort(key=_priority_key)
        result.extend(unresolved)

    return result


def _bucket_into_phases(ordered_skill_ids: list[uuid.UUID]) -> dict[uuid.UUID, RoadmapPhase]:
    """Purely position-based, never content-aware or LLM-decided — up to 3 buckets over the
    already-sequenced list, degenerating gracefully for small N (e.g. N=1 puts everything in
    Foundations)."""
    total = len(ordered_skill_ids)
    if total == 0:
        return {}
    bucket_size = -(-total // 3)  # ceil division without importing math for one use
    phases: dict[uuid.UUID, RoadmapPhase] = {}
    for index, skill_id in enumerate(ordered_skill_ids):
        if index < bucket_size:
            phases[skill_id] = RoadmapPhase.FOUNDATIONS
        elif index < bucket_size * 2:
            phases[skill_id] = RoadmapPhase.CORE
        else:
            phases[skill_id] = RoadmapPhase.ADVANCED
    return phases


async def _get_or_create_learning_path(
    db: AsyncSession, *, user_id: uuid.UUID, target_role: str
) -> LearningPath:
    """Same SAVEPOINT get-or-create shape as `get_or_create_skill`
    (app/services/skill_taxonomy.py) — safe to call from inside a larger transaction, and safe
    under a concurrent double-click on "Generate"/"Regenerate". Explicitly filters
    `deleted_at IS NULL`: a soft-deleted row for this (user, target_role) must never be reused —
    `DELETE /learning-roadmap` followed by a fresh `POST /generate` must create a genuinely new
    row, not resurrect the old one."""
    result = await db.execute(
        select(LearningPath).where(
            LearningPath.user_id == user_id,
            LearningPath.target_role == target_role,
            LearningPath.deleted_at.is_(None),
        )
    )
    learning_path = result.scalar_one_or_none()
    if learning_path is not None:
        return learning_path

    try:
        async with db.begin_nested():
            learning_path = LearningPath(user_id=user_id, target_role=target_role)
            db.add(learning_path)
            await db.flush()
    except IntegrityError:
        result = await db.execute(
            select(LearningPath).where(
                LearningPath.user_id == user_id,
                LearningPath.target_role == target_role,
                LearningPath.deleted_at.is_(None),
            )
        )
        learning_path = result.scalar_one()
    return learning_path


async def _persist_sequence(
    db: AsyncSession, learning_path: LearningPath, sequenced: list[SequencedSkill]
) -> list[LearningPathItem]:
    """Full re-derivation on every call, not a partial patch: `phase`/`order_index` are
    recomputed for *every* item because the whole sequence can shift when the underlying gap set
    changes (a new gap appears, an old one closes) — only `completed`/`completed_at` survive,
    carried over by matching `skill_id` against the prior row. Capture-then-wipe-then-rewrite,
    the same idiom `app/services/skill_gap.py`/`app/ai/kb_ingest.py` already use for this exact
    "recompute derived rows for one owner, race-safely" shape — not a new ON CONFLICT pattern."""
    try:
        async with db.begin_nested():
            existing_result = await db.execute(
                select(LearningPathItem).where(
                    LearningPathItem.learning_path_id == learning_path.id
                )
            )
            prior_by_skill = {row.skill_id: row for row in existing_result.scalars().all()}

            await db.execute(
                delete(LearningPathItem).where(
                    LearningPathItem.learning_path_id == learning_path.id
                )
            )

            new_items = []
            for seq in sequenced:
                prior = prior_by_skill.get(seq.skill.id)
                new_items.append(
                    LearningPathItem(
                        learning_path_id=learning_path.id,
                        skill_id=seq.skill.id,
                        phase=seq.phase,
                        order_index=seq.order_index,
                        completed=prior.completed if prior is not None else False,
                        completed_at=prior.completed_at if prior is not None else None,
                    )
                )
            db.add_all(new_items)
            await db.flush()
    except IntegrityError:
        result = await db.execute(
            select(LearningPathItem)
            .where(LearningPathItem.learning_path_id == learning_path.id)
            .order_by(LearningPathItem.order_index)
        )
        return list(result.scalars().all())
    return new_items


async def _recompute_status(db: AsyncSession, learning_path: LearningPath) -> None:
    """Derived from item completion, not a separate trigger/cron: every item completed ->
    `COMPLETED`; a completed path with a later-unmarked item reverts to `ACTIVE`. A roadmap with
    zero items (the user has no gaps for this role) stays `ACTIVE`, not `COMPLETED` — `all([])`
    being vacuously `True` in Python is a real footgun this explicitly guards against."""
    result = await db.execute(
        select(LearningPathItem.completed).where(
            LearningPathItem.learning_path_id == learning_path.id
        )
    )
    completions = result.scalars().all()
    if completions and all(completions):
        learning_path.status = LearningPathStatus.COMPLETED
    elif learning_path.status == LearningPathStatus.COMPLETED:
        learning_path.status = LearningPathStatus.ACTIVE
    await db.flush()


async def generate_learning_path(
    db: AsyncSession, *, user: User, career_path: CareerPath
) -> tuple[LearningPath, list[SequencedSkill]]:
    """Deterministic roadmap generation — no LLM call in this function (that's
    `app/ai/roadmap_overview.py`, invoked separately by the route so a narrative-generation
    failure can never block or corrupt this, the actually-valuable part). Reuses
    `get_stored_skill_gaps`/`compute_and_store_skill_gaps` directly rather than duplicating gap
    logic — gap computation is free/deterministic, so auto-computing on first use here mirrors
    `GET /skills/gaps`'s own precedent. Does not commit — caller (the route) owns the
    transaction, same convention as every other service in this codebase."""
    gaps = await get_stored_skill_gaps(db, user_id=user.id, career_path_slug=career_path.slug)
    if not gaps:
        gaps = await compute_and_store_skill_gaps(db, user=user, career_path=career_path)

    needing_work: list[SkillGap] = [g for g in gaps if g.gap_level in _GAP_LEVELS_NEEDING_WORK]
    skill_ids = [g.skill_id for g in needing_work]
    gap_level_by_skill = {g.skill_id: g.gap_level for g in needing_work}
    # Reuses each gap's already-computed, already-stored `priority` (weight/core-ness, plus any
    # real `growth_rate` blend — see `skill_gap.py::_priority`) rather than recomputing it here —
    # one source of truth for "how urgent is this skill," consistent with what
    # `GET /skills/gaps` already shows the user for the same gap row.
    priority_by_skill: dict[uuid.UUID, int] = {g.skill_id: g.priority for g in needing_work}

    edges = await _fetch_prerequisite_edges(db, set(skill_ids))
    ordered_ids = _topological_sort(skill_ids, edges, priority_by_skill)
    phase_by_skill = _bucket_into_phases(ordered_ids)

    skill_by_id = {gap.skill.id: gap.skill for gap in needing_work}
    sequenced = [
        SequencedSkill(
            skill=skill_by_id[skill_id],
            gap_level=gap_level_by_skill[skill_id],
            phase=phase_by_skill[skill_id],
            order_index=index,
        )
        for index, skill_id in enumerate(ordered_ids)
    ]

    learning_path = await _get_or_create_learning_path(
        db, user_id=user.id, target_role=career_path.slug
    )
    await _persist_sequence(db, learning_path, sequenced)
    await _recompute_status(db, learning_path)
    learning_path.generated_at = datetime.now(UTC)
    await db.flush()

    return learning_path, sequenced


async def get_learning_path(
    db: AsyncSession, *, user_id: uuid.UUID, target_role: str
) -> LearningPath | None:
    result = await db.execute(
        select(LearningPath).where(
            LearningPath.user_id == user_id,
            LearningPath.target_role == target_role,
            LearningPath.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def delete_learning_path(db: AsyncSession, *, user_id: uuid.UUID, target_role: str) -> bool:
    """Soft-deletes the active roadmap for this (user, target_role), if one exists. Returns
    `False` (no-op) rather than raising when there's nothing to delete — the route translates
    that into a 404."""
    learning_path = await get_learning_path(db, user_id=user_id, target_role=target_role)
    if learning_path is None:
        return False
    learning_path.soft_delete()
    await db.flush()
    return True


async def get_owned_learning_path_item(
    db: AsyncSession, *, item_id: uuid.UUID, user_id: uuid.UUID
) -> LearningPathItem | None:
    """Ownership-checked lookup via the parent `learning_path.user_id` — a second user's item id
    must resolve to `None` (404), never leak another user's row."""
    result = await db.execute(
        select(LearningPathItem)
        .join(LearningPath, LearningPathItem.learning_path_id == LearningPath.id)
        .where(
            LearningPathItem.id == item_id,
            LearningPath.user_id == user_id,
            LearningPath.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def set_item_completed(
    db: AsyncSession, *, item: LearningPathItem, completed: bool
) -> LearningPath:
    item.completed = completed
    item.completed_at = datetime.now(UTC) if completed else None
    await db.flush()

    learning_path = await db.get(LearningPath, item.learning_path_id)
    if learning_path is None:
        raise ValueError(f"LearningPathItem {item.id} references a missing learning_path")
    await _recompute_status(db, learning_path)
    return learning_path


async def get_ordered_items(
    db: AsyncSession, learning_path_id: uuid.UUID
) -> list[LearningPathItem]:
    """Always a fresh query, never a cached relationship collection — see `LearningPath`'s
    docstring for why. Used by both `GET /learning-roadmap` and `POST /generate`'s response
    builder, so the two routes can never disagree about what "the current roadmap" looks like."""
    result = await db.execute(
        select(LearningPathItem)
        .where(LearningPathItem.learning_path_id == learning_path_id)
        .order_by(LearningPathItem.order_index)
    )
    return list(result.scalars().all())


async def get_learning_resources_by_skill(
    db: AsyncSession, skill_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[tuple[SkillLearningResource, str | None]]]:
    """Curated resources/project suggestions for a set of skills, grouped by `skill_id` and
    ordered — a read-only join against the shared reference table
    (app/models/skill_learning_resource.py), never duplicated per `LearningPath`. The paired
    `str | None` is the linked `Resource`'s slug (Phase 9) when this resource points at one, via
    an outer join so a resource with no `resource_id` still comes back (with `None`) rather than
    being silently dropped by an inner join."""
    if not skill_ids:
        return {}
    result = await db.execute(
        select(SkillLearningResource, Resource.slug)
        .outerjoin(Resource, SkillLearningResource.resource_id == Resource.id)
        .where(SkillLearningResource.skill_id.in_(skill_ids))
        .order_by(SkillLearningResource.skill_id, SkillLearningResource.order_index)
    )
    grouped: dict[uuid.UUID, list[tuple[SkillLearningResource, str | None]]] = defaultdict(list)
    for resource, slug in result.all():
        grouped[resource.skill_id].append((resource, slug))
    return grouped
