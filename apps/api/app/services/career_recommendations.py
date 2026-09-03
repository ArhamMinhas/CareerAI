import math

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career_path import CareerPath
from app.models.user import User
from app.services.career_paths import list_career_paths
from app.services.job_matching import _latest_resume_embedding

TOP_N = 5


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def get_career_recommendations(
    db: AsyncSession, *, user: User
) -> list[tuple[CareerPath, float]]:
    """Ranks published career paths for `user` by resume-to-career-path embedding cosine
    similarity — docs/ML_PIPELINE.md §3 model 2's own baseline, used here as the live ranking
    rather than the trained model: on the one real evaluation available, the model didn't clear
    this baseline (ml/models/career_recommendation/README.md) — "baseline first, model only if
    it earns its place" (ML_PIPELINE.md §1). Returns `[]` if the user has no resume embedding yet
    (same graceful-degradation precedent as `job_matching.py::_candidate_jobs`).
    """
    resume_embedding = await _latest_resume_embedding(db, user.id)
    if resume_embedding is None:
        return []

    career_paths = await list_career_paths(db)
    scored = [
        (cp, _cosine_similarity(resume_embedding, cp.embedding))
        for cp in career_paths
        if cp.embedding is not None
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:TOP_N]
