"""Exports labeled training data for docs/ML_PIPELINE.md §3 model 1 (job suitability
classifier, docs/ROADMAP.md Phase 8) as a CSV `ml/` reads directly.

Model 1's feature set IS the existing deterministic `job_match_score` breakdown
(app/services/job_matching.py) — reusing that real, already-correct async code here (rather than
re-deriving profile/education/experience/career-goal matching logic a second time in `ml/`'s
pandas/raw-SQL layer) keeps feature computation DRY. Everything else Phase 8 needs (raw jobs/
skills/embeddings tables) has no such canonical async implementation to reuse, so `ml/
training/data.py` pulls those directly via SQL instead — see that module's docstring.

Label = `job_match_score >= SUITABLE_THRESHOLD`. Only users with a live (non-deleted), completed
resume are included — as of writing that's 2 real users, not a large N; see the model card this
produces for how that shapes the evaluation methodology.

Run from apps/api with the venv active (or `docker exec careerai-api-1 python -m
app.scripts.export_ml_training_data`):

    python -m app.scripts.export_ml_training_data
"""

import asyncio
import csv
from pathlib import Path

from sqlalchemy import select

from app.core.db import AsyncSessionLocal, engine
from app.models.job import Job
from app.models.resume import Resume, ResumeStatus
from app.models.user import User
from app.services.job_matching import _compute_breakdown, _load_match_context, _overall_score

OUT_PATH = Path("/tmp/job_suitability_training.csv")
SUITABLE_THRESHOLD = 60.0


async def run() -> None:
    await engine.dispose()
    async with AsyncSessionLocal() as db:
        user_ids_result = await db.execute(
            select(Resume.user_id)
            .where(Resume.deleted_at.is_(None), Resume.status == ResumeStatus.COMPLETED)
            .distinct()
        )
        user_ids = list(user_ids_result.scalars().all())

        jobs_result = await db.execute(select(Job).where(Job.is_active.is_(True)))
        jobs = list(jobs_result.scalars().all())

        rows: list[dict] = []
        for user_id in user_ids:
            user = await db.get(User, user_id)
            if user is None:
                continue
            context = await _load_match_context(db, user)
            for job in jobs:
                breakdown = _compute_breakdown(
                    job=job,
                    profile=context.profile,
                    user_skill_ids=context.user_skill_ids,
                    experiences=context.experiences,
                    educations=context.educations,
                    career_goal=context.career_goal,
                    resume_embedding=context.resume_embedding,
                )
                score = _overall_score(breakdown)
                rows.append(
                    {
                        "user_id": str(user_id),
                        "job_id": str(job.id),
                        "semantic_similarity": breakdown.semantic_similarity.score,
                        "skill_overlap": breakdown.skill_overlap.score,
                        "experience_match": breakdown.experience_match.score,
                        "education_match": breakdown.education_match.score,
                        "preference_match": breakdown.preference_match.score,
                        "location_match": breakdown.location_match.score,
                        "job_match_score": score,
                        "suitable": int(score >= SUITABLE_THRESHOLD),
                    }
                )

        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with OUT_PATH.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
            writer.writeheader()
            writer.writerows(rows)

        print(f"wrote {len(rows)} rows ({len(user_ids)} users x {len(jobs)} jobs) -> {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(run())
