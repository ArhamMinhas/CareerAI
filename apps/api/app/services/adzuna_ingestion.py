import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.company import Company
from app.models.job import Job
from app.models.skill import slugify
from app.services.embeddings import embed_text

ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"
RESULTS_PER_PAGE = 50
_DESCRIPTION_MAX_CHARS = 4000  # embed_text's input budget, matching resume_tasks.py's precedent

# Adzuna's advertised country codes don't come back with a currency field on each job, so this
# is a small, honest heuristic rather than a real currency lookup — good enough for the
# countries actually used by app/scripts/ingest_adzuna_jobs.py today.
_COUNTRY_CURRENCY: dict[str, str] = {
    "us": "USD",
    "gb": "GBP",
    "ca": "CAD",
    "au": "AUD",
    "de": "EUR",
    "fr": "EUR",
    "in": "INR",
}


class AdzunaConfigError(Exception):
    """Raised when ADZUNA_APP_ID/ADZUNA_APP_KEY aren't configured."""


class AdzunaAPIError(Exception):
    """Raised on any non-2xx response from Adzuna."""


async def fetch_adzuna_page(*, what: str, where: str, country: str, page: int) -> list[dict]:
    if not settings.adzuna_app_id or not settings.adzuna_app_key:
        raise AdzunaConfigError(
            "ADZUNA_APP_ID / ADZUNA_APP_KEY aren't set — sign up for a free account at "
            "https://developer.adzuna.com and add them to .env."
        )
    params: dict[str, str | int] = {
        "app_id": settings.adzuna_app_id,
        "app_key": settings.adzuna_app_key,
        "results_per_page": RESULTS_PER_PAGE,
        "what": what,
        "where": where,
        "content-type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{ADZUNA_BASE_URL}/{country}/search/{page}", params=params)
    if response.status_code >= 400:
        raise AdzunaAPIError(f"Adzuna request failed ({response.status_code}): {response.text}")
    results = response.json().get("results", [])
    return results if isinstance(results, list) else []


async def _get_or_create_company(db: AsyncSession, name: str) -> Company:
    """Same get-or-create-by-slug shape as app/services/skill_taxonomy.py's `get_or_create_skill`
    — a SAVEPOINT so a concurrent ingestion run creating the same company doesn't crash the
    whole batch, just falls back to reading back whichever row won."""
    slug = slugify(name)
    result = await db.execute(select(Company).where(Company.slug == slug))
    company = result.scalar_one_or_none()
    if company is not None:
        return company

    try:
        async with db.begin_nested():
            company = Company(name=name, slug=slug)
            db.add(company)
            await db.flush()
    except IntegrityError:
        result = await db.execute(select(Company).where(Company.slug == slug))
        company = result.scalar_one()
    return company


def _map_employment_type(item: dict) -> str | None:
    contract_time = item.get("contract_time")
    if contract_time == "part_time":
        return "part-time"
    if contract_time == "full_time":
        return "full-time"
    return item.get("contract_type")


async def ingest_adzuna_jobs(
    db: AsyncSession, *, what: str, where: str, country: str = "us", max_pages: int = 1
) -> int:
    """Fetches real postings from Adzuna and upserts them as `Job` rows, keyed on
    `(source="adzuna", external_id)` — see `Job`'s docstring. Returns the number of jobs
    created or updated. Does not commit; callers own the transaction, matching every other
    ingestion/seed script here (see app/scripts/seed_jobs.py).
    """
    ingested = 0
    for page in range(1, max_pages + 1):
        results = await fetch_adzuna_page(what=what, where=where, country=country, page=page)
        if not results:
            break

        for item in results:
            external_id = str(item.get("id", ""))
            if not external_id:
                continue
            company_name = (item.get("company") or {}).get("display_name") or "Unknown Company"
            company = await _get_or_create_company(db, company_name)

            result = await db.execute(
                select(Job).where(Job.source == "adzuna", Job.external_id == external_id)
            )
            job = result.scalar_one_or_none()
            if job is None:
                job = Job(source="adzuna", external_id=external_id, company_id=company.id)
                db.add(job)

            title = (item.get("title") or "Untitled position").strip()[:255]
            description = (item.get("description") or "").strip()
            location = (item.get("location") or {}).get("display_name")

            job.company_id = company.id
            job.title = title
            job.description = description or "No description provided."
            job.employment_type = _map_employment_type(item)
            job.location = location
            job.remote = "remote" in (location or "").lower()
            job.salary_min = item.get("salary_min")
            job.salary_max = item.get("salary_max")
            job.currency = _COUNTRY_CURRENCY.get(country)
            job.apply_url = item.get("redirect_url")
            job.is_active = True
            job.embedding = await embed_text(
                f"{title} at {company.name}\n\n{description[:_DESCRIPTION_MAX_CHARS]}"
            )
            await db.flush()
            ingested += 1

    return ingested
