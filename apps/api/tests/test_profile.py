import uuid

from httpx import AsyncClient
from sqlalchemy import delete as sa_delete

from app.core.db import AsyncSessionLocal
from app.models.skill import Skill


async def test_get_profile_lazily_creates_it(authed_client: AsyncClient) -> None:
    response = await authed_client.get("/api/v1/profile")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["full_name"] is None
    assert data["id"]


async def test_patch_profile_updates_only_sent_fields(authed_client: AsyncClient) -> None:
    await authed_client.patch("/api/v1/profile", json={"full_name": "Ada Lovelace", "bio": "hi"})

    response = await authed_client.patch("/api/v1/profile", json={"headline": "AI Engineer"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["full_name"] == "Ada Lovelace"
    assert data["bio"] == "hi"
    assert data["headline"] == "AI Engineer"


async def test_profile_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/profile")
    assert response.status_code == 401


async def test_education_crud_lifecycle(authed_client: AsyncClient) -> None:
    create = await authed_client.post(
        "/api/v1/profile/education",
        json={
            "institution": "MIT",
            "degree": "BSc Computer Science",
            "start_date": "2018-09-01",
            "end_date": "2022-06-01",
        },
    )
    assert create.status_code == 201
    education_id = create.json()["data"]["id"]

    listing = await authed_client.get("/api/v1/profile/education")
    assert any(row["id"] == education_id for row in listing.json()["data"])

    update = await authed_client.patch(
        f"/api/v1/profile/education/{education_id}",
        json={"degree": "BSc Computer Science, Honours"},
    )
    assert update.status_code == 200
    assert update.json()["data"]["degree"] == "BSc Computer Science, Honours"

    delete = await authed_client.delete(f"/api/v1/profile/education/{education_id}")
    assert delete.status_code == 204

    listing_after = await authed_client.get("/api/v1/profile/education")
    assert all(row["id"] != education_id for row in listing_after.json()["data"])


async def test_education_rejects_end_date_before_start_date(authed_client: AsyncClient) -> None:
    response = await authed_client.post(
        "/api/v1/profile/education",
        json={"institution": "MIT", "start_date": "2022-01-01", "end_date": "2020-01-01"},
    )
    assert response.status_code == 422


async def test_education_not_found_for_other_users_row(authed_client: AsyncClient) -> None:
    response = await authed_client.patch(
        "/api/v1/profile/education/00000000-0000-0000-0000-000000000000", json={"degree": "x"}
    )
    assert response.status_code == 404


async def test_experience_crud_lifecycle(authed_client: AsyncClient) -> None:
    create = await authed_client.post(
        "/api/v1/profile/experience",
        json={"company": "Acme Corp", "title": "Software Engineer", "start_date": "2022-07-01"},
    )
    assert create.status_code == 201
    experience_id = create.json()["data"]["id"]
    assert create.json()["data"]["end_date"] is None

    update = await authed_client.patch(
        f"/api/v1/profile/experience/{experience_id}", json={"title": "Senior Software Engineer"}
    )
    assert update.json()["data"]["title"] == "Senior Software Engineer"

    delete = await authed_client.delete(f"/api/v1/profile/experience/{experience_id}")
    assert delete.status_code == 204


async def test_project_crud_lifecycle(authed_client: AsyncClient) -> None:
    create = await authed_client.post(
        "/api/v1/profile/projects",
        json={
            "title": "CareerAI",
            "url": "https://example.com",
            "repo_url": "https://github.com/x/y",
        },
    )
    assert create.status_code == 201
    project_id = create.json()["data"]["id"]

    update = await authed_client.patch(
        f"/api/v1/profile/projects/{project_id}", json={"description": "An AI career platform."}
    )
    assert update.json()["data"]["description"] == "An AI career platform."

    delete = await authed_client.delete(f"/api/v1/profile/projects/{project_id}")
    assert delete.status_code == 204


async def test_skill_crud_lifecycle_and_taxonomy_reuse(authed_client: AsyncClient) -> None:
    unique_skill = f"Test Skill {uuid.uuid4().hex[:8]}"

    create = await authed_client.post(
        "/api/v1/profile/skills", json={"skill_name": unique_skill, "proficiency": "advanced"}
    )
    assert create.status_code == 201
    body = create.json()["data"]
    assert body["name"] == unique_skill
    assert body["proficiency"] == "advanced"
    assert body["source"] == "manual"
    user_skill_id = body["id"]

    duplicate = await authed_client.post(
        "/api/v1/profile/skills", json={"skill_name": unique_skill, "proficiency": "beginner"}
    )
    assert duplicate.status_code == 409

    update = await authed_client.patch(
        f"/api/v1/profile/skills/{user_skill_id}", json={"proficiency": "expert"}
    )
    assert update.json()["data"]["proficiency"] == "expert"

    autocomplete = await authed_client.get("/api/v1/skills", params={"q": unique_skill[:15]})
    assert any(s["name"] == unique_skill for s in autocomplete.json()["data"])

    delete = await authed_client.delete(f"/api/v1/profile/skills/{user_skill_id}")
    assert delete.status_code == 204

    listing_after = await authed_client.get("/api/v1/profile/skills")
    assert all(row["id"] != user_skill_id for row in listing_after.json()["data"])

    # Deleting a user_skills row only removes this user's claim, never the shared taxonomy
    # entry `get_or_create_skill` created (correct — other users may reference it). This test
    # is the only writer of the "Test Skill <hex>" row it made, so it's safe to remove here —
    # without this, every run permanently leaks one row into the real skill taxonomy.
    async with AsyncSessionLocal() as db:
        await db.execute(sa_delete(Skill).where(Skill.name == unique_skill))
        await db.commit()
