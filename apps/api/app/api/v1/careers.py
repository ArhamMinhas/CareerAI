from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.ml.inference import predict_salary_range
from app.schemas.career_path import CareerPathDetailRead, CareerPathRead, PredictedSalaryRange
from app.schemas.envelope import Envelope, meta_from_request
from app.services.career_paths import (
    find_related_career_paths,
    get_career_path_by_slug,
    list_career_paths,
)

router = APIRouter(prefix="/careers", tags=["careers"])

# Real, independent `Job.search_category` values (app/scripts/ingest_adzuna_jobs.py's QUERIES)
# closest to each seeded career path (app/scripts/seed_career_paths.py) — most are exact matches;
# "ai-engineer" has no directly-matching query, so it uses "machine learning engineer" as the
# closest real proxy category rather than going unmapped. Feeds model 4's salary prediction
# (docs/ML_PIPELINE.md §3, Phase 8) for `/careers/[slug]`.
_CAREER_PATH_TO_SEARCH_CATEGORY: dict[str, str] = {
    "ai-engineer": "machine learning engineer",
    "machine-learning-engineer": "machine learning engineer",
    "data-scientist": "data scientist",
    "backend-engineer": "backend engineer",
    "frontend-engineer": "frontend engineer",
    "full-stack-engineer": "full stack engineer",
    "devops-engineer": "devops engineer",
    "product-manager": "product manager",
}


@router.get("", response_model=Envelope[list[CareerPathRead]])
async def get_careers(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Envelope[list[CareerPathRead]]:
    """Public, unauthenticated — backs the indexable `/careers` index page (docs/SEO.md §1).
    Not paginated: the curated catalog is small by design, not an unbounded feed."""
    career_paths = await list_career_paths(db)
    return Envelope(
        data=[CareerPathRead.model_validate(cp) for cp in career_paths],
        meta=meta_from_request(request),
    )


@router.get("/{slug}", response_model=Envelope[CareerPathDetailRead])
async def get_career(
    request: Request,
    slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Envelope[CareerPathDetailRead]:
    """Public, unauthenticated — backs the indexable `/careers/[slug]` page and is the same
    curated required-skill profile the Skill Gap Engine diffs against (docs/ROADMAP.md
    Phase 6)."""
    career_path = await get_career_path_by_slug(db, slug)
    if career_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Career path not found.")

    related = await find_related_career_paths(db, career_path)
    data = CareerPathDetailRead.model_validate(career_path)
    data.related_career_paths = [CareerPathRead.model_validate(r) for r in related]

    search_category = _CAREER_PATH_TO_SEARCH_CATEGORY.get(career_path.slug)
    if search_category is not None:
        salary_range = predict_salary_range(
            search_category=search_category,
            seniority_level="mid",
            remote=False,
            required_skill_count=len(career_path.required_skills),
        )
        if salary_range is not None:
            p25, p50, p75 = salary_range
            data.predicted_salary_range = PredictedSalaryRange(p25=p25, p50=p50, p75=p75)

    return Envelope(data=data, meta=meta_from_request(request))
