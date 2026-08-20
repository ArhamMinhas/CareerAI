from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.skill import Skill
from app.models.user import User
from app.schemas.envelope import Envelope, meta_from_request
from app.schemas.skill import SkillRead

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=Envelope[list[SkillRead]])
async def search_skills(
    request: Request,
    _user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    q: str | None = Query(default=None, max_length=255),
) -> Envelope[list[SkillRead]]:
    """Autocomplete for manual skill entry (Phase 3). The full taxonomy browse/gap-analysis
    catalog (docs/API.md §5) is Phase 6 — this only needs to answer "does a skill matching
    this text already exist" for the profile skills form."""
    stmt = select(Skill).order_by(Skill.name).limit(20)
    if q:
        stmt = select(Skill).where(Skill.name.ilike(f"%{q}%")).order_by(Skill.name).limit(20)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return Envelope(
        data=[SkillRead.model_validate(r) for r in rows], meta=meta_from_request(request)
    )
