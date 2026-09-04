import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import delete, select

from app.core.db import AsyncSessionLocal
from app.models.career_path import CareerPath, CareerPathSkill
from app.models.learning_path import LearningPath, LearningPathItem, LearningPathStatus
from app.models.skill import Skill
from app.models.skill_gap import GapLevel, SkillGap
from app.models.skill_prerequisite import SkillPrerequisite
from app.models.user import Role, User
from app.services.learning_roadmap import (
    delete_learning_path,
    generate_learning_path,
    get_learning_path,
    get_owned_learning_path_item,
    set_item_completed,
)
from app.services.skill_taxonomy import get_or_create_skill

# Fully self-contained fixtures — must not depend on app/scripts/seed_learning_resources.py
# having been run, and never make real embedding/LLM calls (the service under test here has
# none — that's app/ai/roadmap_overview.py, tested separately).


@pytest.fixture
async def roadmap_career_path() -> AsyncGenerator[tuple[CareerPath, Skill, Skill, Skill]]:
    """A career path requiring 3 skills; skill_b requires skill_a (a real prerequisite edge),
    skill_c has no edge at all — exercises both the constrained and priority-only-fallback
    parts of the sequencing algorithm in one fixture."""
    unique = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        skill_a = await get_or_create_skill(db, f"Roadmap Skill A {unique}")
        skill_b = await get_or_create_skill(db, f"Roadmap Skill B {unique}")
        skill_c = await get_or_create_skill(db, f"Roadmap Skill C {unique}")
        db.add(SkillPrerequisite(skill_id=skill_b.id, requires_skill_id=skill_a.id))
        await db.commit()

        path = CareerPath(
            slug=f"test-roadmap-path-{unique}",
            title=f"Test Roadmap Path {unique}",
            summary="A test career path for learning-roadmap unit tests.",
            description_md="Test description.",
            related_job_titles=[],
            published=True,
        )
        db.add(path)
        await db.flush()
        db.add(
            CareerPathSkill(career_path_id=path.id, skill_id=skill_a.id, weight=5, is_core=False)
        )
        db.add(CareerPathSkill(career_path_id=path.id, skill_id=skill_b.id, weight=8, is_core=True))
        db.add(
            CareerPathSkill(career_path_id=path.id, skill_id=skill_c.id, weight=3, is_core=False)
        )
        await db.commit()
        path_id, a_id, b_id, c_id = path.id, skill_a.id, skill_b.id, skill_c.id

    yield path, skill_a, skill_b, skill_c

    async with AsyncSessionLocal() as db:
        await db.execute(delete(SkillPrerequisite).where(SkillPrerequisite.skill_id == b_id))
        await db.execute(delete(SkillGap).where(SkillGap.skill_id.in_([a_id, b_id, c_id])))
        await db.execute(delete(CareerPath).where(CareerPath.id == path_id))
        await db.execute(delete(Skill).where(Skill.id.in_([a_id, b_id, c_id])))
        await db.commit()


@pytest.fixture
async def roadmap_user() -> AsyncGenerator[User]:
    user = User(id=uuid.uuid4(), email=f"roadmap-test-{uuid.uuid4()}@example.com", role=Role.USER)
    async with AsyncSessionLocal() as db:
        db.add(user)
        await db.commit()

    yield user

    async with AsyncSessionLocal() as db:
        await db.execute(delete(LearningPath).where(LearningPath.user_id == user.id))
        await db.execute(delete(User).where(User.id == user.id))
        await db.commit()


async def test_generate_learning_path_orders_by_prerequisite_and_creates_all_items(
    roadmap_user: User, roadmap_career_path: tuple[CareerPath, Skill, Skill, Skill]
) -> None:
    path, skill_a, skill_b, skill_c = roadmap_career_path

    async with AsyncSessionLocal() as db:
        user = await db.get(User, roadmap_user.id)
        career_path = await db.get(CareerPath, path.id)
        assert user is not None
        assert career_path is not None
        learning_path, sequenced = await generate_learning_path(
            db, user=user, career_path=career_path
        )
        await db.commit()
        learning_path_id = learning_path.id

    assert {seq.skill.id for seq in sequenced} == {skill_a.id, skill_b.id, skill_c.id}
    order_index_by_skill = {seq.skill.id: seq.order_index for seq in sequenced}
    assert order_index_by_skill[skill_a.id] < order_index_by_skill[skill_b.id]

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(LearningPathItem).where(LearningPathItem.learning_path_id == learning_path_id)
        )
        items = result.scalars().all()
        assert len(items) == 3
        assert {i.order_index for i in items} == {0, 1, 2}


async def test_regenerate_preserves_completed_state_for_still_relevant_skills(
    roadmap_user: User, roadmap_career_path: tuple[CareerPath, Skill, Skill, Skill]
) -> None:
    path, skill_a, _skill_b, _skill_c = roadmap_career_path

    async with AsyncSessionLocal() as db:
        user = await db.get(User, roadmap_user.id)
        career_path = await db.get(CareerPath, path.id)
        assert user is not None and career_path is not None
        learning_path, _ = await generate_learning_path(db, user=user, career_path=career_path)
        await db.commit()
        learning_path_id = learning_path.id

    # Mark skill_a's item complete.
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(LearningPathItem).where(
                LearningPathItem.learning_path_id == learning_path_id,
                LearningPathItem.skill_id == skill_a.id,
            )
        )
        item_a = result.scalar_one()
        await set_item_completed(db, item=item_a, completed=True)
        await db.commit()

    # Regenerate — full re-derivation, but skill_a's completion must survive.
    async with AsyncSessionLocal() as db:
        user = await db.get(User, roadmap_user.id)
        career_path = await db.get(CareerPath, path.id)
        assert user is not None and career_path is not None
        await generate_learning_path(db, user=user, career_path=career_path)
        await db.commit()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(LearningPathItem).where(
                LearningPathItem.learning_path_id == learning_path_id,
                LearningPathItem.skill_id == skill_a.id,
            )
        )
        item_a_after = result.scalar_one()
        assert item_a_after.completed is True
        assert item_a_after.completed_at is not None


async def test_regenerate_removes_items_for_skills_no_longer_gapped(
    roadmap_user: User, roadmap_career_path: tuple[CareerPath, Skill, Skill, Skill]
) -> None:
    path, skill_a, _skill_b, _skill_c = roadmap_career_path

    async with AsyncSessionLocal() as db:
        user = await db.get(User, roadmap_user.id)
        career_path = await db.get(CareerPath, path.id)
        assert user is not None and career_path is not None
        learning_path, sequenced = await generate_learning_path(
            db, user=user, career_path=career_path
        )
        await db.commit()
        learning_path_id = learning_path.id
    assert len(sequenced) == 3

    # Directly close skill_a's gap the same way skill_gap.py's own tests do — mark it STRONG so
    # the next regenerate no longer considers it a gap.
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SkillGap).where(
                SkillGap.user_id == roadmap_user.id, SkillGap.skill_id == skill_a.id
            )
        )
        gap = result.scalar_one()
        gap.gap_level = GapLevel.STRONG
        await db.commit()

    async with AsyncSessionLocal() as db:
        user = await db.get(User, roadmap_user.id)
        career_path = await db.get(CareerPath, path.id)
        assert user is not None and career_path is not None
        _, sequenced_after = await generate_learning_path(db, user=user, career_path=career_path)
        await db.commit()

    assert skill_a.id not in {seq.skill.id for seq in sequenced_after}
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(LearningPathItem).where(
                LearningPathItem.learning_path_id == learning_path_id,
                LearningPathItem.skill_id == skill_a.id,
            )
        )
        assert result.scalar_one_or_none() is None


async def test_generate_learning_path_survives_concurrent_calls(
    roadmap_user: User, roadmap_career_path: tuple[CareerPath, Skill, Skill, Skill]
) -> None:
    """Regression test mirroring `test_compute_and_store_skill_gaps_survives_concurrent_calls`
    and `test_ingest_resource_survives_concurrent_calls`: two concurrent `/generate` calls (a
    double-click on "Regenerate", or two tabs) must not crash on either the parent
    `learning_paths` row or the child `learning_path_items` upsert."""
    path, _skill_a, _skill_b, _skill_c = roadmap_career_path

    async def _generate() -> uuid.UUID:
        async with AsyncSessionLocal() as db:
            user = await db.get(User, roadmap_user.id)
            career_path = await db.get(CareerPath, path.id)
            assert user is not None and career_path is not None
            learning_path, _ = await generate_learning_path(db, user=user, career_path=career_path)
            await db.commit()
            return learning_path.id

    first_id, second_id = await asyncio.gather(_generate(), _generate())
    assert first_id == second_id  # both resolved to the same, single learning_path row

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(LearningPath).where(LearningPath.user_id == roadmap_user.id)
        )
        paths = result.scalars().all()
        assert len(paths) == 1  # no duplicate row from the losing attempt

        items_result = await db.execute(
            select(LearningPathItem).where(LearningPathItem.learning_path_id == first_id)
        )
        items = items_result.scalars().all()
        assert len(items) == 3  # no duplicate/leftover items either
        assert len({i.skill_id for i in items}) == 3  # all distinct skills


async def test_status_transitions_to_completed_and_back(
    roadmap_user: User, roadmap_career_path: tuple[CareerPath, Skill, Skill, Skill]
) -> None:
    path, skill_a, skill_b, skill_c = roadmap_career_path

    async with AsyncSessionLocal() as db:
        user = await db.get(User, roadmap_user.id)
        career_path = await db.get(CareerPath, path.id)
        assert user is not None and career_path is not None
        learning_path, _ = await generate_learning_path(db, user=user, career_path=career_path)
        await db.commit()
        learning_path_id = learning_path.id

    async def _item_for(skill_id: uuid.UUID) -> LearningPathItem:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(LearningPathItem).where(
                    LearningPathItem.learning_path_id == learning_path_id,
                    LearningPathItem.skill_id == skill_id,
                )
            )
            return result.scalar_one()

    for skill_id in (skill_a.id, skill_b.id, skill_c.id):
        async with AsyncSessionLocal() as db:
            item = await db.get(LearningPathItem, (await _item_for(skill_id)).id)
            assert item is not None
            await set_item_completed(db, item=item, completed=True)
            await db.commit()

    async with AsyncSessionLocal() as db:
        learning_path = await db.get(LearningPath, learning_path_id)
        assert learning_path is not None
        assert learning_path.status == LearningPathStatus.COMPLETED

    # Unmark one item — status must revert to ACTIVE.
    async with AsyncSessionLocal() as db:
        item = await db.get(LearningPathItem, (await _item_for(skill_a.id)).id)
        assert item is not None
        await set_item_completed(db, item=item, completed=False)
        await db.commit()

    async with AsyncSessionLocal() as db:
        learning_path = await db.get(LearningPath, learning_path_id)
        assert learning_path is not None
        assert learning_path.status == LearningPathStatus.ACTIVE


async def test_delete_then_regenerate_creates_a_fresh_row(
    roadmap_user: User, roadmap_career_path: tuple[CareerPath, Skill, Skill, Skill]
) -> None:
    path, _skill_a, _skill_b, _skill_c = roadmap_career_path

    async with AsyncSessionLocal() as db:
        user = await db.get(User, roadmap_user.id)
        career_path = await db.get(CareerPath, path.id)
        assert user is not None and career_path is not None
        learning_path, _ = await generate_learning_path(db, user=user, career_path=career_path)
        await db.commit()
        original_id = learning_path.id

    async with AsyncSessionLocal() as db:
        deleted = await delete_learning_path(db, user_id=roadmap_user.id, target_role=path.slug)
        await db.commit()
        assert deleted is True

    async with AsyncSessionLocal() as db:
        assert await get_learning_path(db, user_id=roadmap_user.id, target_role=path.slug) is None

    async with AsyncSessionLocal() as db:
        user = await db.get(User, roadmap_user.id)
        career_path = await db.get(CareerPath, path.id)
        assert user is not None and career_path is not None
        new_learning_path, _ = await generate_learning_path(db, user=user, career_path=career_path)
        await db.commit()
        assert new_learning_path.id != original_id


async def test_delete_learning_path_is_a_noop_when_nothing_to_delete(
    roadmap_user: User, roadmap_career_path: tuple[CareerPath, Skill, Skill, Skill]
) -> None:
    path, *_ = roadmap_career_path
    async with AsyncSessionLocal() as db:
        deleted = await delete_learning_path(db, user_id=roadmap_user.id, target_role=path.slug)
        assert deleted is False


async def test_get_owned_learning_path_item_enforces_ownership(
    roadmap_user: User, roadmap_career_path: tuple[CareerPath, Skill, Skill, Skill]
) -> None:
    path, skill_a, _skill_b, _skill_c = roadmap_career_path
    other_user = User(
        id=uuid.uuid4(), email=f"roadmap-other-{uuid.uuid4()}@example.com", role=Role.USER
    )

    async with AsyncSessionLocal() as db:
        db.add(other_user)
        await db.commit()

    try:
        async with AsyncSessionLocal() as db:
            user = await db.get(User, roadmap_user.id)
            career_path = await db.get(CareerPath, path.id)
            assert user is not None and career_path is not None
            learning_path, _ = await generate_learning_path(db, user=user, career_path=career_path)
            await db.commit()
            learning_path_id = learning_path.id

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(LearningPathItem).where(
                    LearningPathItem.learning_path_id == learning_path_id,
                    LearningPathItem.skill_id == skill_a.id,
                )
            )
            item = result.scalar_one()

            owned = await get_owned_learning_path_item(db, item_id=item.id, user_id=roadmap_user.id)
            assert owned is not None

            not_owned = await get_owned_learning_path_item(
                db, item_id=item.id, user_id=other_user.id
            )
            assert not_owned is None
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(LearningPath).where(LearningPath.user_id == other_user.id))
            await db.execute(delete(User).where(User.id == other_user.id))
            await db.commit()
