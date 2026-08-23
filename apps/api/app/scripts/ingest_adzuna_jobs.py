"""Ingests real job postings from the Adzuna API (docs/ROADMAP.md Phase 7) — the real
counterpart to app/scripts/seed_jobs.py's hand-written demo data. Requires a free developer
account at https://developer.adzuna.com; set ADZUNA_APP_ID/ADZUNA_APP_KEY in .env before running.

Run from apps/api with the venv active (or `docker exec careerai-api-1 python -m
app.scripts.ingest_adzuna_jobs`):

    python -m app.scripts.ingest_adzuna_jobs
"""

import asyncio

from app.core.config import settings
from app.core.db import AsyncSessionLocal, engine
from app.services.adzuna_ingestion import AdzunaAPIError, ingest_adzuna_jobs

# One (what, where) pair per career path this app already curates a required-skill profile
# for (see app/scripts/seed_career_paths.py) — real postings that plausibly line up with the
# roles the skill-gap and job-matching engines already know about, rather than an arbitrary
# keyword list.
QUERIES: list[tuple[str, str]] = [
    ("software engineer", "United States"),
    ("backend engineer", "United States"),
    ("frontend engineer", "United States"),
    ("full stack engineer", "United States"),
    ("machine learning engineer", "United States"),
    ("data scientist", "United States"),
    ("devops engineer", "United States"),
    ("product manager", "United States"),
]
MAX_PAGES_PER_QUERY = 1  # 50 results/page — keep this a quick, well-behaved run against the API


async def run() -> None:
    if not settings.adzuna_app_id or not settings.adzuna_app_key:
        raise SystemExit(
            "ADZUNA_APP_ID / ADZUNA_APP_KEY aren't set. Sign up for a free account at "
            "https://developer.adzuna.com, then add both to .env before running this script."
        )

    await engine.dispose()
    total = 0
    failed: list[str] = []
    async with AsyncSessionLocal() as db:
        for what, where in QUERIES:
            try:
                count = await ingest_adzuna_jobs(
                    db, what=what, where=where, max_pages=MAX_PAGES_PER_QUERY
                )
                await db.commit()
                total += count
                print(f"ingested {count} jobs for '{what}' in {where}")
            except AdzunaAPIError as exc:
                # A transient upstream failure (rate limit, momentary 5xx) on one query
                # shouldn't lose progress already committed for earlier queries or block the
                # remaining ones — roll back just this query's uncommitted work and move on.
                await db.rollback()
                failed.append(what)
                print(f"skipped '{what}' in {where} — Adzuna request failed: {exc}")
            await asyncio.sleep(1)  # a light pause between queries to stay well under rate limits

    print(f"done — {total} jobs ingested/updated total")
    if failed:
        print(f"failed queries (re-run to retry — already-ingested jobs are untouched): {failed}")


if __name__ == "__main__":
    asyncio.run(run())
