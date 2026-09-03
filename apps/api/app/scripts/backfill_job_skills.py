"""Backfills `job_skills` (docs/ROADMAP.md Phase 8) from each job's title/description via
`app/services/job_skill_extraction.py`'s deterministic keyword/synonym matcher against the
shared skill taxonomy. Needed because `job_skills` stayed empty through Phase 7 — real Adzuna
postings were ingested with no skill extraction step at all.

Idempotent: replaces a job's existing `JobSkill` rows each run rather than accumulating
duplicates, so re-running after new jobs are ingested (or the skill taxonomy grows) is safe.

Run from apps/api with the venv active (or `docker exec careerai-api-1 python -m
app.scripts.backfill_job_skills`):

    python -m app.scripts.backfill_job_skills
"""

import asyncio

from sqlalchemy import delete, select

from app.core.db import AsyncSessionLocal, engine
from app.models.job import Job, JobSkill
from app.models.skill import Skill
from app.services.job_skill_extraction import extract_job_skills


async def run() -> None:
    await engine.dispose()
    async with AsyncSessionLocal() as db:
        skills = list((await db.execute(select(Skill))).scalars().all())
        jobs = list((await db.execute(select(Job))).scalars().all())

        total_links = 0
        jobs_with_matches = 0
        for job in jobs:
            matches = extract_job_skills(
                title=job.title, description=job.description, skills=skills
            )
            await db.execute(delete(JobSkill).where(JobSkill.job_id == job.id))
            for skill_id, weight in matches.items():
                db.add(JobSkill(job_id=job.id, skill_id=skill_id, is_required=True, weight=weight))
            if matches:
                jobs_with_matches += 1
                total_links += len(matches)
            await db.commit()

        print(
            f"done — {total_links} job_skills links across {jobs_with_matches}/{len(jobs)} jobs "
            f"({len(skills)} skills in taxonomy)"
        )


if __name__ == "__main__":
    asyncio.run(run())
