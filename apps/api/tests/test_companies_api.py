from httpx import AsyncClient

from app.core.db import AsyncSessionLocal
from app.models.job import Job


async def test_get_company_by_slug(client: AsyncClient, seeded_job: Job) -> None:
    async with AsyncSessionLocal() as session:
        job = await session.get(Job, seeded_job.id)
        assert job is not None
        slug = job.company.slug

    response = await client.get(f"/api/v1/companies/{slug}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["slug"] == slug
    assert any(job["id"] == str(seeded_job.id) for job in data["jobs"])


async def test_get_company_404_for_unknown_slug(client: AsyncClient) -> None:
    response = await client.get("/api/v1/companies/no-such-company-slug")
    assert response.status_code == 404


async def test_get_company_jobs(client: AsyncClient, seeded_job: Job) -> None:
    async with AsyncSessionLocal() as session:
        job = await session.get(Job, seeded_job.id)
        assert job is not None
        slug = job.company.slug

    response = await client.get(f"/api/v1/companies/{slug}/jobs")
    assert response.status_code == 200
    assert any(job["id"] == str(seeded_job.id) for job in response.json()["data"])


async def test_get_company_jobs_404_for_unknown_slug(client: AsyncClient) -> None:
    response = await client.get("/api/v1/companies/no-such-company-slug/jobs")
    assert response.status_code == 404
