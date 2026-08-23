from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.envelope import Envelope, meta_from_request
from app.schemas.job_match import JobMatchRead
from app.services.job_matching import get_stored_job_matches

router = APIRouter(prefix="/matches", tags=["jobs"])


@router.get("", response_model=Envelope[list[JobMatchRead]])
async def get_matches(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Envelope[list[JobMatchRead]]:
    """docs/API.md §5's `GET /api/v1/matches` — reads this user's cached ranked matches (`POST
    /jobs/match` computes them). Empty until the first refresh, same "nothing computed yet"
    shape as `GET /skills/gaps` before its first read."""
    matches = await get_stored_job_matches(db, user_id=user.id)
    return Envelope(
        data=[JobMatchRead.model_validate(m) for m in matches], meta=meta_from_request(request)
    )
