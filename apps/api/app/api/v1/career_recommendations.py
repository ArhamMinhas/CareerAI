from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.career_path import CareerPathRead, CareerRecommendationRead
from app.schemas.envelope import Envelope, meta_from_request
from app.services.career_recommendations import get_career_recommendations

router = APIRouter(prefix="/career-recommendations", tags=["careers"])


@router.get("", response_model=Envelope[list[CareerRecommendationRead]])
async def get_recommendations(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Envelope[list[CareerRecommendationRead]]:
    """docs/ML_PIPELINE.md §3 model 2, Phase 8 — top career paths ranked by resume-to-career-
    path embedding similarity for the current user. Empty (not an error) if the user has no
    analyzed resume yet."""
    ranked = await get_career_recommendations(db, user=user)
    return Envelope(
        data=[
            CareerRecommendationRead(career_path=CareerPathRead.model_validate(cp), fit_score=score)
            for cp, score in ranked
        ],
        meta=meta_from_request(request),
    )
