import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select

from app.core.db import AsyncSessionLocal
from app.models.career_path import CareerPath, CareerPathSkill
from app.models.skill import Skill
from app.models.skill_gap import GapLevel, SkillGap
from app.models.user import Role, User
from app.services.skill_gap import _priority, compute_and_store_skill_gaps
from app.services.skill_taxonomy import get_or_create_skill


def test_priority_without_growth_rate_is_unchanged() -> None:
    assert _priority(5, True, GapLevel.MISSING) == 20
    assert _priority(5, True, GapLevel.MISSING, growth_rate=None) == 20


def test_priority_blends_positive_growth_rate() -> None:
    base = _priority(5, True, GapLevel.MISSING)
    boosted = _priority(5, True, GapLevel.MISSING, growth_rate=1.0)
    assert boosted == base * 2


def test_priority_clamps_extreme_growth_rate() -> None:
    # 5.0 clamps to the 2.0 ceiling (docs: one noisy week shouldn't dominate weight/core-ness).
    base = _priority(5, True, GapLevel.MISSING)
    assert _priority(5, True, GapLevel.MISSING, growth_rate=5.0) == round(base * 3)
    # -0.9 clamps to the -0.5 floor.
    assert _priority(5, True, GapLevel.MISSING, growth_rate=-0.9) == round(base * 0.5)


def test_priority_ignores_growth_rate_for_covered_gap_levels() -> None:
    assert _priority(5, True, GapLevel.ADEQUATE, growth_rate=2.0) == 0
    assert _priority(5, True, GapLevel.STRONG, growth_rate=2.0) == 0


@pytest.fixture
async def gap_test_career_path() -> AsyncGenerator[tuple[CareerPath, Skill, Skill]]:
    """A career path requiring one core skill (weight 10) and one non-core skill (weight 4) —
    fully self-contained, no dependency on `app/scripts/seed_career_paths.py`."""
    unique = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        core_skill = await get_or_create_skill(db, f"Gap Core Skill {unique}")
        other_skill = await get_or_create_skill(db, f"Gap Other Skill {unique}")
        await db.commit()

        path = CareerPath(
            slug=f"test-gap-path-{unique}",
            title=f"Test Gap Path {unique}",
            summary="A test career path for skill-gap unit tests.",
            description_md="Test description.",
            related_job_titles=[],
            published=True,
        )
        db.add(path)
        await db.flush()
        db.add(
            CareerPathSkill(career_path_id=path.id, skill_id=core_skill.id, weight=10, is_core=True)
        )
        db.add(
            CareerPathSkill(
                career_path_id=path.id, skill_id=other_skill.id, weight=4, is_core=False
            )
        )
        await db.commit()
        path_id, core_id, other_id = path.id, core_skill.id, other_skill.id

    yield path, core_skill, other_skill

    async with AsyncSessionLocal() as db:
        await db.execute(delete(SkillGap).where(SkillGap.skill_id.in_([core_id, other_id])))
        await db.execute(delete(CareerPath).where(CareerPath.id == path_id))
        await db.execute(delete(Skill).where(Skill.id.in_([core_id, other_id])))
        await db.commit()


async def test_gaps_require_auth(
    client: AsyncClient, gap_test_career_path: tuple[CareerPath, Skill, Skill]
) -> None:
    path, _, _ = gap_test_career_path
    response = await client.get(f"/api/v1/skills/gaps?target_role={path.slug}")
    assert response.status_code == 401


async def test_get_gaps_404_for_unknown_target_role(authed_client: AsyncClient) -> None:
    response = await authed_client.get("/api/v1/skills/gaps?target_role=totally-unknown-role-xyz")
    assert response.status_code == 404


async def test_get_gaps_404_not_500_for_sql_wildcard_target_role(
    authed_client: AsyncClient,
) -> None:
    """Regression test: `target_role` is arbitrary caller input that used to be passed
    straight into an `ILIKE` pattern. A bare `%` matches every published career path, which
    made `resolve_career_path`'s `scalar_one_or_none()` raise `MultipleResultsFound` (a 500)
    instead of a clean 404 whenever more than one career path exists — as it does here, since
    other tests/the seed script populate real rows in this shared dev database."""
    response = await authed_client.get("/api/v1/skills/gaps?target_role=%25")
    assert response.status_code == 404


async def test_get_gaps_auto_computes_and_classifies_correctly(
    authed_client: AsyncClient, gap_test_career_path: tuple[CareerPath, Skill, Skill]
) -> None:
    path, core_skill, other_skill = gap_test_career_path

    add_response = await authed_client.post(
        "/api/v1/profile/skills",
        json={"skill_name": core_skill.name, "proficiency": "expert"},
    )
    assert add_response.status_code in (200, 201)

    response = await authed_client.get(f"/api/v1/skills/gaps?target_role={path.slug}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["target_role"] == path.title

    by_name = {row["skill"]["name"]: row for row in data["gaps"]}
    assert by_name[core_skill.name]["gap_level"] == "strong"
    assert by_name[core_skill.name]["priority"] == 0
    assert by_name[other_skill.name]["gap_level"] == "missing"
    # weight(4) * non-core(1) * missing-multiplier(2)
    assert by_name[other_skill.name]["priority"] == 8

    recommended_names = {row["skill"]["name"] for row in data["recommended_next"]}
    assert other_skill.name in recommended_names
    assert core_skill.name not in recommended_names
    assert data["summary"]["strong"] == 1
    assert data["summary"]["missing"] == 1


async def test_refresh_recomputes_after_skill_change(
    authed_client: AsyncClient, gap_test_career_path: tuple[CareerPath, Skill, Skill]
) -> None:
    path, _core_skill, other_skill = gap_test_career_path

    first = await authed_client.get(f"/api/v1/skills/gaps?target_role={path.slug}")
    assert all(row["gap_level"] == "missing" for row in first.json()["data"]["gaps"])

    await authed_client.post(
        "/api/v1/profile/skills",
        json={"skill_name": other_skill.name, "proficiency": "beginner"},
    )
    refreshed = await authed_client.post(f"/api/v1/skills/gaps/refresh?target_role={path.slug}")
    assert refreshed.status_code == 200
    by_name = {row["skill"]["name"]: row for row in refreshed.json()["data"]["gaps"]}
    assert by_name[other_skill.name]["gap_level"] == "weak"


async def test_compute_and_store_skill_gaps_survives_concurrent_calls(
    gap_test_career_path: tuple[CareerPath, Skill, Skill],
) -> None:
    """Regression test for a real race: two concurrent calls computing gaps for the same
    user+career-path (e.g. GET's auto-compute racing a POST /refresh from another tab) both
    used to see "no rows yet" and both try to insert the same `(user_id, skill_id,
    target_role)` rows — the loser crashed with a duplicate-key `IntegrityError` instead of
    just reading back the winner's equivalent, deterministic result."""
    path, core_skill, other_skill = gap_test_career_path
    user = User(
        id=uuid.uuid4(), email=f"concurrent-gaps-{uuid.uuid4()}@example.com", role=Role.USER
    )

    async with AsyncSessionLocal() as db:
        db.add(user)
        await db.commit()

    async def _compute() -> list[str]:
        async with AsyncSessionLocal() as db:
            fresh_path = await db.get(CareerPath, path.id)
            assert fresh_path is not None
            gaps = await compute_and_store_skill_gaps(db, user=user, career_path=fresh_path)
            await db.commit()
            return sorted(gap.gap_level.value for gap in gaps)

    try:
        first, second = await asyncio.gather(_compute(), _compute())
        assert first == second == ["missing", "missing"]

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(SkillGap).where(SkillGap.user_id == user.id))
            rows = result.scalars().all()
            assert len(rows) == 2  # no leftover duplicates from the losing attempt
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(SkillGap).where(SkillGap.user_id == user.id))
            await db.execute(delete(User).where(User.id == user.id))
            await db.commit()
