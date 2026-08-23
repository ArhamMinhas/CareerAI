import uuid

import pytest
from sqlalchemy import delete, select

import app.services.adzuna_ingestion as adzuna_ingestion
from app.core.db import AsyncSessionLocal
from app.models.company import Company
from app.models.job import Job
from app.services.adzuna_ingestion import AdzunaConfigError, fetch_adzuna_page, ingest_adzuna_jobs


async def test_fetch_adzuna_page_fails_fast_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(adzuna_ingestion.settings, "adzuna_app_id", "")
    monkeypatch.setattr(adzuna_ingestion.settings, "adzuna_app_key", "")
    with pytest.raises(AdzunaConfigError):
        await fetch_adzuna_page(what="engineer", where="remote", country="us", page=1)


def _fake_result(*, job_id: str, title: str, company: str) -> dict:
    return {
        "id": job_id,
        "title": title,
        "description": "A great real job.",
        "redirect_url": f"https://example-job-board.com/jobs/{job_id}",
        "company": {"display_name": company},
        "location": {"display_name": "Remote"},
        "salary_min": 100000.0,
        "salary_max": 150000.0,
        "contract_time": "full_time",
    }


async def test_ingest_adzuna_jobs_creates_company_and_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unique = uuid.uuid4().hex[:8]
    job_id = f"test-{unique}"
    company_name = f"Test Adzuna Co {unique}"

    async def fake_fetch(*, what: str, where: str, country: str, page: int) -> list[dict]:
        if page > 1:
            return []
        return [_fake_result(job_id=job_id, title="Real Software Engineer", company=company_name)]

    monkeypatch.setattr(adzuna_ingestion, "fetch_adzuna_page", fake_fetch)
    monkeypatch.setattr(
        adzuna_ingestion,
        "embed_text",
        lambda text: _fake_embedding(),  # type: ignore[arg-type]
    )

    async with AsyncSessionLocal() as db:
        count = await ingest_adzuna_jobs(db, what="engineer", where="remote", max_pages=2)
        await db.commit()
        assert count == 1

        result = await db.execute(
            select(Job).where(Job.source == "adzuna", Job.external_id == job_id)
        )
        job = result.scalar_one()
        assert job.title == "Real Software Engineer"
        assert job.apply_url == f"https://example-job-board.com/jobs/{job_id}"
        assert job.employment_type == "full-time"
        assert job.remote is True

        company_result = await db.execute(select(Company).where(Company.id == job.company_id))
        company = company_result.scalar_one()
        assert company.name == company_name

        await db.execute(delete(Job).where(Job.id == job.id))
        await db.execute(delete(Company).where(Company.id == company.id))
        await db.commit()


async def test_ingest_adzuna_jobs_upserts_on_rerun(monkeypatch: pytest.MonkeyPatch) -> None:
    unique = uuid.uuid4().hex[:8]
    job_id = f"test-{unique}"
    company_name = f"Test Adzuna Co {unique}"

    async def fake_fetch_v1(*, what: str, where: str, country: str, page: int) -> list[dict]:
        if page > 1:
            return []
        return [_fake_result(job_id=job_id, title="Original Title", company=company_name)]

    async def fake_fetch_v2(*, what: str, where: str, country: str, page: int) -> list[dict]:
        if page > 1:
            return []
        return [_fake_result(job_id=job_id, title="Updated Title", company=company_name)]

    monkeypatch.setattr(
        adzuna_ingestion,
        "embed_text",
        lambda text: _fake_embedding(),  # type: ignore[arg-type]
    )

    async with AsyncSessionLocal() as db:
        monkeypatch.setattr(adzuna_ingestion, "fetch_adzuna_page", fake_fetch_v1)
        await ingest_adzuna_jobs(db, what="engineer", where="remote")
        await db.commit()

        monkeypatch.setattr(adzuna_ingestion, "fetch_adzuna_page", fake_fetch_v2)
        count = await ingest_adzuna_jobs(db, what="engineer", where="remote")
        await db.commit()
        assert count == 1

        result = await db.execute(
            select(Job).where(Job.source == "adzuna", Job.external_id == job_id)
        )
        jobs = result.scalars().all()
        assert len(jobs) == 1
        assert jobs[0].title == "Updated Title"

        company_result = await db.execute(select(Company).where(Company.slug.contains(unique)))
        company = company_result.scalar_one()
        await db.execute(delete(Job).where(Job.id == jobs[0].id))
        await db.execute(delete(Company).where(Company.id == company.id))
        await db.commit()


async def _fake_embedding() -> list[float]:
    return [0.1] * 1536
