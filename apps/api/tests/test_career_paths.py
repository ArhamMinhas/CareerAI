import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy import delete

from app.core.db import AsyncSessionLocal
from app.models.career_path import CareerPath, CareerPathSkill
from app.models.skill import Skill
from app.services.skill_taxonomy import get_or_create_skill

# Fully self-contained fixtures — these tests must not depend on
# `app/scripts/seed_career_paths.py` having been run (CI's fresh Postgres never runs it, and
# it makes real OpenAI calls for embeddings which CI has no key for). Embeddings here are
# hand-written vectors, not real API calls, so the cosine-similarity query path is still
# exercised for real.


@pytest.fixture
async def seeded_career_paths() -> AsyncGenerator[tuple[CareerPath, CareerPath, Skill, Skill]]:
    unique = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        core_skill = await get_or_create_skill(db, f"Test Core Skill {unique}")
        extra_skill = await get_or_create_skill(db, f"Test Extra Skill {unique}")
        await db.commit()

        path_a = CareerPath(
            slug=f"test-career-a-{unique}",
            title=f"Test Career A {unique}",
            summary="Summary A",
            description_md="Description A with real content.",
            related_job_titles=["Role A"],
            embedding=[0.1] * 1536,
            published=True,
        )
        path_b = CareerPath(
            slug=f"test-career-b-{unique}",
            title=f"Test Career B {unique}",
            summary="Summary B",
            description_md="Description B.",
            related_job_titles=["Role B"],
            embedding=[0.101] * 1536,  # deliberately close to path_a's vector
            published=True,
        )
        db.add_all([path_a, path_b])
        await db.flush()

        db.add(
            CareerPathSkill(
                career_path_id=path_a.id, skill_id=core_skill.id, weight=10, is_core=True
            )
        )
        db.add(
            CareerPathSkill(
                career_path_id=path_a.id, skill_id=extra_skill.id, weight=4, is_core=False
            )
        )
        await db.commit()
        path_a_id, path_b_id, core_skill_id, extra_skill_id = (
            path_a.id,
            path_b.id,
            core_skill.id,
            extra_skill.id,
        )

    yield path_a, path_b, core_skill, extra_skill

    async with AsyncSessionLocal() as db:
        await db.execute(delete(CareerPath).where(CareerPath.id.in_([path_a_id, path_b_id])))
        await db.execute(delete(Skill).where(Skill.id.in_([core_skill_id, extra_skill_id])))
        await db.commit()


async def test_list_careers_is_public_and_includes_seeded_paths(
    client: AsyncClient,
    seeded_career_paths: tuple[CareerPath, CareerPath, Skill, Skill],
) -> None:
    path_a, path_b, _, _ = seeded_career_paths
    response = await client.get("/api/v1/careers")
    assert response.status_code == 200
    slugs = {item["slug"] for item in response.json()["data"]}
    assert path_a.slug in slugs
    assert path_b.slug in slugs


async def test_get_career_detail_includes_required_skills(
    client: AsyncClient,
    seeded_career_paths: tuple[CareerPath, CareerPath, Skill, Skill],
) -> None:
    path_a, _, core_skill, extra_skill = seeded_career_paths
    response = await client.get(f"/api/v1/careers/{path_a.slug}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["title"] == path_a.title
    skill_names = {row["skill"]["name"] for row in data["required_skills"]}
    assert core_skill.name in skill_names
    assert extra_skill.name in skill_names
    core_row = next(
        row for row in data["required_skills"] if row["skill"]["name"] == core_skill.name
    )
    assert core_row["is_core"] is True


async def test_get_career_detail_includes_related_career_paths(
    client: AsyncClient,
    seeded_career_paths: tuple[CareerPath, CareerPath, Skill, Skill],
) -> None:
    path_a, path_b, _, _ = seeded_career_paths
    response = await client.get(f"/api/v1/careers/{path_a.slug}")
    data = response.json()["data"]
    related_slugs = {rel["slug"] for rel in data["related_career_paths"]}
    assert path_b.slug in related_slugs
    assert path_a.slug not in related_slugs


async def test_get_career_detail_404_for_unknown_slug(client: AsyncClient) -> None:
    response = await client.get("/api/v1/careers/not-a-real-career-path")
    assert response.status_code == 404
