"""Backfills `Job.predicted_category` (docs/ML_PIPELINE.md §3 model 5, docs/ROADMAP.md Phase 8)
for jobs ingested before the classifier existed. New ingestion runs set it directly
(app/services/adzuna_ingestion.py) — this script only needs to run once for the existing backlog.

Idempotent: re-running just re-predicts and overwrites.

Run from apps/api with the venv active (or `docker exec careerai-api-1 python -m
app.scripts.backfill_predicted_category`):

    python -m app.scripts.backfill_predicted_category
"""

import asyncio

from sqlalchemy import select

from app.core.db import AsyncSessionLocal, engine
from app.ml.inference import predict_job_category
from app.models.job import Job


async def run() -> None:
    await engine.dispose()
    async with AsyncSessionLocal() as db:
        jobs = list((await db.execute(select(Job))).scalars().all())
        updated = 0
        for job in jobs:
            predicted = predict_job_category(title=job.title, description=job.description)
            if predicted is not None:
                job.predicted_category = predicted
                updated += 1
        await db.commit()
        print(f"updated {updated}/{len(jobs)} jobs")


if __name__ == "__main__":
    asyncio.run(run())
