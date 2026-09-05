import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.core.db import AsyncSessionLocal
from app.core.security import get_current_user
from app.main import app
from app.models.company import Company
from app.models.job import Job
from app.models.skill import Skill
from app.models.user import Role, User

# Fully self-contained — no LLM calls anywhere in this feature, so nothing to monkeypatch (same
# reasoning as test_analytics_api.py). `admin_client` mirrors conftest.py's `authed_client`
# fixture exactly, but mints a Role.ADMIN user — `require_role`'s inner check depends on the same
# `get_current_user` callable conftest.py's fixture overrides, so the override applies here too.


@pytest.fixture
async def admin_client() -> AsyncGenerator[AsyncClient]:
    admin_user = User(id=uuid.uuid4(), email=f"admin-{uuid.uuid4()}@example.com", role=Role.ADMIN)
    async with AsyncSessionLocal() as session:
        session.add(admin_user)
        await session.commit()

    async def _override_user() -> User:
        return admin_user

    app.dependency_overrides[get_current_user] = _override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    del app.dependency_overrides[get_current_user]
    async with AsyncSessionLocal() as session:
        await session.execute(delete(User).where(User.id == admin_user.id))
        await session.commit()


async def test_admin_routes_require_auth(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/admin/users")).status_code == 401
    assert (await client.get("/api/v1/admin/jobs")).status_code == 401
    assert (await client.get("/api/v1/admin/skills")).status_code == 401
    assert (await client.get("/api/v1/admin/ai-usage")).status_code == 401
    assert (await client.get("/api/v1/admin/model-metrics")).status_code == 401
    assert (await client.get("/api/v1/admin/system-health")).status_code == 401


async def test_admin_routes_403_for_authenticated_non_admin(authed_client: AsyncClient) -> None:
    assert (await authed_client.get("/api/v1/admin/users")).status_code == 403
    assert (await authed_client.get("/api/v1/admin/system-health")).status_code == 403


async def test_list_admin_users_returns_real_users(admin_client: AsyncClient) -> None:
    response = await admin_client.get("/api/v1/admin/users?limit=5")
    assert response.status_code == 200
    assert isinstance(response.json()["data"], list)


async def test_update_admin_user_role_blocks_self_demotion(admin_client: AsyncClient) -> None:
    me_response = await admin_client.get("/api/v1/auth/me")
    my_id = me_response.json()["data"]["id"]

    response = await admin_client.patch(f"/api/v1/admin/users/{my_id}", json={"role": "USER"})
    assert response.status_code == 403


async def test_update_admin_user_role_changes_a_different_users_role(
    admin_client: AsyncClient,
) -> None:
    unique = uuid.uuid4().hex[:8]
    target = User(id=uuid.uuid4(), email=f"target-{unique}@example.com", role=Role.USER)
    async with AsyncSessionLocal() as db:
        db.add(target)
        await db.commit()

    try:
        response = await admin_client.patch(
            f"/api/v1/admin/users/{target.id}", json={"role": "RECRUITER"}
        )
        assert response.status_code == 200
        assert response.json()["data"]["role"] == "RECRUITER"
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(User).where(User.id == target.id))
            await db.commit()


async def test_update_admin_user_role_404_for_unknown_user(admin_client: AsyncClient) -> None:
    response = await admin_client.patch(
        f"/api/v1/admin/users/{uuid.uuid4()}", json={"role": "USER"}
    )
    assert response.status_code == 404


@pytest.fixture
async def admin_api_company() -> AsyncGenerator[Company]:
    unique = uuid.uuid4().hex[:8]
    company = Company(name=f"Admin API Co {unique}", slug=f"admin-api-co-{unique}")
    async with AsyncSessionLocal() as db:
        db.add(company)
        await db.commit()

    yield company

    async with AsyncSessionLocal() as db:
        await db.execute(delete(Job).where(Job.company_id == company.id))
        await db.execute(delete(Company).where(Company.id == company.id))
        await db.commit()


async def test_create_admin_job_succeeds_with_real_fields(
    admin_client: AsyncClient, admin_api_company: Company
) -> None:
    response = await admin_client.post(
        "/api/v1/admin/jobs",
        json={
            "company_id": str(admin_api_company.id),
            "title": "Admin-created Backend Engineer",
            "description": "A real description written through the admin API.",
            "remote": True,
        },
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["title"] == "Admin-created Backend Engineer"
    assert data["is_active"] is True
    assert data["company"]["id"] == str(admin_api_company.id)


async def test_create_admin_job_rejects_empty_description(
    admin_client: AsyncClient, admin_api_company: Company
) -> None:
    response = await admin_client.post(
        "/api/v1/admin/jobs",
        json={"company_id": str(admin_api_company.id), "title": "X", "description": ""},
    )
    assert response.status_code == 422


async def test_create_admin_job_404_for_unknown_company(admin_client: AsyncClient) -> None:
    response = await admin_client.post(
        "/api/v1/admin/jobs",
        json={"company_id": str(uuid.uuid4()), "title": "X", "description": "Y"},
    )
    assert response.status_code == 404


async def test_list_admin_jobs_includes_inactive_jobs(
    admin_client: AsyncClient, admin_api_company: Company
) -> None:
    async with AsyncSessionLocal() as db:
        job = Job(
            company_id=admin_api_company.id,
            title="Inactive Job",
            description="Test.",
            is_active=False,
        )
        db.add(job)
        await db.commit()
        job_id = job.id

    response = await admin_client.get("/api/v1/admin/jobs?limit=100")
    assert response.status_code == 200
    ids = {row["id"] for row in response.json()["data"]}
    assert str(job_id) in ids


async def test_create_admin_skill_then_409_on_duplicate(admin_client: AsyncClient) -> None:
    unique = uuid.uuid4().hex[:8]
    name = f"API Test Skill {unique}"
    try:
        first = await admin_client.post("/api/v1/admin/skills", json={"name": name})
        assert first.status_code == 201
        assert first.json()["data"]["has_curated_content"] is False

        second = await admin_client.post("/api/v1/admin/skills", json={"name": name})
        assert second.status_code == 409
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(Skill).where(Skill.name == name))
            await db.commit()


async def test_list_admin_skills_returns_envelope(admin_client: AsyncClient) -> None:
    response = await admin_client.get("/api/v1/admin/skills?limit=5")
    assert response.status_code == 200
    assert isinstance(response.json()["data"], list)


async def test_get_admin_ai_usage_returns_envelope(admin_client: AsyncClient) -> None:
    response = await admin_client.get("/api/v1/admin/ai-usage")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "by_feature" in data
    assert "by_model" in data


async def test_get_admin_model_metrics_returns_all_six_models(admin_client: AsyncClient) -> None:
    response = await admin_client.get("/api/v1/admin/model-metrics")
    assert response.status_code == 200
    models = response.json()["data"]["models"]
    assert len(models) == 6


async def test_get_admin_system_health_returns_envelope(admin_client: AsyncClient) -> None:
    response = await admin_client.get("/api/v1/admin/system-health")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["database_ok"] is True
    assert data["redis_ok"] is True
