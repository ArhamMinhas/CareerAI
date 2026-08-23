import uuid

from httpx import AsyncClient
from sqlalchemy import delete

from app.core.db import AsyncSessionLocal
from app.models.company import Company
from app.models.job import Job


async def test_list_jobs_returns_seeded_job(client: AsyncClient, seeded_job: Job) -> None:
    response = await client.get("/api/v1/jobs")
    assert response.status_code == 200
    assert any(job["id"] == str(seeded_job.id) for job in response.json()["data"])


async def test_list_jobs_keyword_search_matches_title(client: AsyncClient, seeded_job: Job) -> None:
    response = await client.get("/api/v1/jobs", params={"q": seeded_job.title})
    assert response.status_code == 200
    data = response.json()["data"]
    assert any(job["id"] == str(seeded_job.id) for job in data)


async def test_list_jobs_keyword_search_excludes_non_matches(
    client: AsyncClient, seeded_job: Job
) -> None:
    # Self-contained: a second job whose title contains a unique keyword `seeded_job` doesn't
    # share, so a query for that keyword hits the keyword path (not the semantic fallback,
    # which always returns *some* nearest-neighbor ranking and would defeat this assertion)
    # and excludes the unrelated fixture job.
    unique = uuid.uuid4().hex[:8]
    keyword = f"Zorbatron{unique}"
    async with AsyncSessionLocal() as session:
        company = Company(name=f"Keyword Co {unique}", slug=f"keyword-co-{unique}")
        session.add(company)
        await session.flush()
        job = Job(
            company_id=company.id,
            title=f"{keyword} Engineer",
            description="A job with a distinctive, searchable title.",
            remote=True,
            is_active=True,
        )
        session.add(job)
        await session.commit()
        matching_job_id = job.id

    try:
        response = await client.get("/api/v1/jobs", params={"q": keyword})
        assert response.status_code == 200
        data = response.json()["data"]
        assert any(job["id"] == str(matching_job_id) for job in data)
        assert all(job["id"] != str(seeded_job.id) for job in data)
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(Job).where(Job.company_id == company.id))
            await session.execute(delete(Company).where(Company.id == company.id))
            await session.commit()


async def test_list_jobs_keyword_search_ranks_company_name_matches_first(
    client: AsyncClient,
) -> None:
    # Regression test: a query for a company name must not get buried behind unrelated jobs
    # that merely *mention* that name in their description (e.g. "familiar with Google Cloud"
    # ranking ahead of an actual job at Google) — see app/services/jobs.py's `_match_rank`.
    unique = uuid.uuid4().hex[:8]
    keyword = f"Zorbatron{unique}"
    async with AsyncSessionLocal() as session:
        real_company = Company(name=keyword, slug=f"real-{unique}")
        mentions_company = Company(name=f"Other Co {unique}", slug=f"other-{unique}")
        session.add_all([real_company, mentions_company])
        await session.flush()
        jobs = [
            # Posted later (would normally sort first by posted_at) but only *mentions* the
            # keyword in its description — must rank behind the real company-name match.
            Job(
                company_id=mentions_company.id,
                title="Cloud Engineer",
                description=f"Experience with {keyword} Cloud Platform preferred.",
                remote=True,
                is_active=True,
            ),
            Job(
                company_id=real_company.id,
                title="Software Engineer",
                description="A real job at the real company.",
                remote=True,
                is_active=True,
            ),
        ]
        session.add_all(jobs)
        await session.commit()
        mentions_job_id, real_job_id = jobs[0].id, jobs[1].id

    try:
        response = await client.get("/api/v1/jobs", params={"q": keyword, "limit": 1})
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 1
        assert data[0]["id"] == str(real_job_id), (
            "company-name match should rank ahead of a job that merely mentions the keyword"
        )
        assert data[0]["id"] != str(mentions_job_id)
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(Job).where(Job.company_id.in_([real_company.id, mentions_company.id]))
            )
            await session.execute(
                delete(Company).where(Company.id.in_([real_company.id, mentions_company.id]))
            )
            await session.commit()


async def test_get_job_by_id(client: AsyncClient, seeded_job: Job) -> None:
    response = await client.get(f"/api/v1/jobs/{seeded_job.id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["title"] == seeded_job.title
    assert "required_skills" in data


async def test_get_job_404_for_unknown_id(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/jobs/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_get_job_404_for_inactive_job(client: AsyncClient) -> None:
    unique = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as session:
        company = Company(name=f"Inactive Co {unique}", slug=f"inactive-co-{unique}")
        session.add(company)
        await session.flush()
        job = Job(
            company_id=company.id,
            title="Inactive Job",
            description="Not active.",
            remote=True,
            is_active=False,
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    try:
        response = await client.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 404
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(Job).where(Job.id == job_id))
            await session.execute(delete(Company).where(Company.id == company.id))
            await session.commit()


async def test_list_jobs_cursor_pagination_is_stable_and_exhaustive(client: AsyncClient) -> None:
    unique = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as session:
        company = Company(name=f"Pagination Co {unique}", slug=f"pagination-co-{unique}")
        session.add(company)
        await session.flush()
        jobs = [
            Job(
                company_id=company.id,
                title=f"Pagination Job {unique} {i}",
                description="Paginated test job.",
                remote=True,
                is_active=True,
            )
            for i in range(3)
        ]
        session.add_all(jobs)
        await session.commit()
        job_ids = {job.id for job in jobs}

    try:
        seen_ids: set[uuid.UUID] = set()
        cursor: str | None = None
        for _ in range(5):  # bounded loop guard against an infinite-pagination bug
            response = await client.get(
                "/api/v1/jobs", params={"limit": 1, "cursor": cursor} if cursor else {"limit": 1}
            )
            assert response.status_code == 200
            body = response.json()
            page_ids = {uuid.UUID(job["id"]) for job in body["data"]}
            assert not (page_ids & seen_ids), "cursor pagination returned a duplicate row"
            seen_ids |= page_ids
            cursor = body["meta"]["next_cursor"]
            if job_ids <= seen_ids:
                break

        assert job_ids <= seen_ids
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(Job).where(Job.company_id == company.id))
            await session.execute(delete(Company).where(Company.id == company.id))
            await session.commit()


async def test_list_jobs_rejects_invalid_cursor(client: AsyncClient) -> None:
    response = await client.get("/api/v1/jobs", params={"cursor": "not-a-real-cursor"})
    assert response.status_code == 400
