import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy import delete

from app.core.db import AsyncSessionLocal
from app.models.career_path import CareerPath, CareerPathSkill
from app.models.skill import Skill
from app.services.skill_taxonomy import get_or_create_skill


@pytest.fixture
async def seeded_skills() -> AsyncGenerator[tuple[Skill, Skill, CareerPath]]:
    unique = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        skill_a = await get_or_create_skill(db, f"Detail Test Skill A {unique}")
        skill_b = await get_or_create_skill(db, f"Detail Test Skill B {unique}")
        skill_a.seo_summary = "A real, curated description of skill A."
        skill_a.synonyms = ["Skill A Alias"]
        skill_a.embedding = [0.2] * 1536
        skill_b.embedding = [0.201] * 1536  # deliberately close to skill_a's vector
        await db.commit()

        career_path = CareerPath(
            slug=f"test-skill-page-path-{unique}",
            title=f"Test Skill Page Path {unique}",
            summary="s",
            description_md="d",
            related_job_titles=[],
            published=True,
        )
        db.add(career_path)
        await db.flush()
        db.add(
            CareerPathSkill(
                career_path_id=career_path.id, skill_id=skill_a.id, weight=5, is_core=False
            )
        )
        await db.commit()
        skill_a_id, skill_b_id, path_id = skill_a.id, skill_b.id, career_path.id

    yield skill_a, skill_b, career_path

    async with AsyncSessionLocal() as db:
        await db.execute(delete(CareerPath).where(CareerPath.id == path_id))
        await db.execute(delete(Skill).where(Skill.id.in_([skill_a_id, skill_b_id])))
        await db.commit()


async def test_get_skill_by_slug_is_public(
    client: AsyncClient, seeded_skills: tuple[Skill, Skill, CareerPath]
) -> None:
    skill_a, _, _ = seeded_skills
    response = await client.get(f"/api/v1/skills/{skill_a.slug}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == skill_a.name
    assert data["seo_summary"] == "A real, curated description of skill A."
    assert data["synonyms"] == ["Skill A Alias"]


async def test_get_skill_by_id_also_works(
    client: AsyncClient, seeded_skills: tuple[Skill, Skill, CareerPath]
) -> None:
    skill_a, _, _ = seeded_skills
    response = await client.get(f"/api/v1/skills/{skill_a.id}")
    assert response.status_code == 200
    assert response.json()["data"]["slug"] == skill_a.slug


async def test_get_skill_includes_related_skills_via_embedding(
    client: AsyncClient, seeded_skills: tuple[Skill, Skill, CareerPath]
) -> None:
    skill_a, skill_b, _ = seeded_skills
    response = await client.get(f"/api/v1/skills/{skill_a.slug}")
    related_names = {row["name"] for row in response.json()["data"]["related_skills"]}
    assert skill_b.name in related_names
    assert skill_a.name not in related_names


async def test_get_skill_404_for_unknown(client: AsyncClient) -> None:
    response = await client.get("/api/v1/skills/not-a-real-skill-slug")
    assert response.status_code == 404


async def test_get_skill_includes_career_paths_requiring_it(
    client: AsyncClient, seeded_skills: tuple[Skill, Skill, CareerPath]
) -> None:
    skill_a, skill_b, career_path = seeded_skills
    response = await client.get(f"/api/v1/skills/{skill_a.slug}")
    career_path_slugs = {row["slug"] for row in response.json()["data"]["career_paths"]}
    assert career_path.slug in career_path_slugs

    other_response = await client.get(f"/api/v1/skills/{skill_b.slug}")
    assert other_response.json()["data"]["career_paths"] == []


async def test_list_curated_skills_is_public_and_excludes_uncurated(
    client: AsyncClient, seeded_skills: tuple[Skill, Skill, CareerPath]
) -> None:
    skill_a, skill_b, _ = seeded_skills
    response = await client.get("/api/v1/skills/curated")
    assert response.status_code == 200
    names = {row["name"] for row in response.json()["data"]}
    assert skill_a.name in names  # has seo_summary
    assert skill_b.name not in names  # no seo_summary
